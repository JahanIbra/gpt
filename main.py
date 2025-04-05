# Импортируем модуль для фиксации проблемы с telegram
from telegram_module_fix import telegram, telegram_module, setup_graceful_exit, custom_polling

import os
import asyncio
import logging
import signal
import sys
from typing import Dict, Any, Optional, List, Callable
import threading
from datetime import datetime

from telegram import Update, BotCommand, Bot
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

from config import (
    TELEGRAM_TOKEN, 
    ADMIN_IDS, 
    APP_ENV, 
    DB_PATH,
    MISTRAL_MODEL_PATH,
    logger
)
from telegram_handlers import (
    start, 
    help_command, 
    about_command, 
    admin_panel,
    handle_message, 
    handle_admin_callback,
    start_teach,
    add_knowledge_question,
    add_knowledge_answer,
    cancel_conversation,
    start_add_pdf,
    process_pdf,
    AWAITING_KNOWLEDGE_QUESTION,
    AWAITING_KNOWLEDGE_ANSWER,
    AWAITING_PDF_FILE,
    register_handlers
)
from vector_search import create_faiss_index, update_faiss_index, load_faiss_index
from system_monitor import system_monitor, start_resource_monitoring, start_monitoring
from backup_manager import backup_manager
from database import init_database
from error_handler import ErrorHandler, setup_global_error_handling, setup_error_handlers
from enhanced_logging import LoggingContext, SensitiveDataFilter
from admin_notifications import AdminNotificationManager
from analytics import analytics
from admin_messaging import init_messaging_manager, handle_broadcast_button
from admin_utils import handle_admin_db_callback
from pdf_handler import init_pdf_index
from models import init_llm
from security import SecurityManager

# Глобальная переменная для хранения экземпляра приложения и event loop
application = None
main_loop = None
shutdown_event = None
is_running = False

def init_components():
    """Инициализирует все необходимые компоненты бота"""
    # Инициализация базы данных
    init_database()
    
    # Инициализация LLM модели
    init_llm(MISTRAL_MODEL_PATH)
    
    # Инициализация вектороного поиска
    load_faiss_index()
    
    # Инициализация индекса PDF
    init_pdf_index()
    
    # Инициализация аналитики
    analytics._init_analytics_tables()
    
    # Инициализация модуля безопасности
    security_manager = SecurityManager()
    logger.info("Модуль безопасности инициализирован")
    
    # Запуск мониторинга системных ресурсов
    start_monitoring()
    logger.info("Мониторинг системных ресурсов запущен")

async def setup_commands(application: Application) -> None:
    """
    Настраивает команды бота для меню команд
    
    Args:
        application: Экземпляр приложения Telegram
    """
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("help", "Показать справку"),
        BotCommand("about", "О боте")
    ]
    
    # Добавляем команды администратора
    admin_commands = [
        BotCommand("admin", "Панель администратора"),
        BotCommand("teach", "Добавить запись в базу знаний"),
        BotCommand("add_pdf", "Добавить PDF документ"),
        BotCommand("update_index", "Обновить индекс поиска")
    ]
    
    await application.bot.set_my_commands(commands)
    
    # Устанавливаем команды администратора только для администраторов
    for admin_id in ADMIN_IDS:
        await application.bot.set_my_commands(
            commands + admin_commands,
            scope=telegram.BotCommandScopeChat(chat_id=admin_id)
        )
    
    logger.info("Команды бота настроены")

async def notify_admin(admin_id: int, message: str) -> None:
    """
    Отправляет сообщение администратору
    
    Args:
        admin_id: ID администратора
        message: Текст сообщения
    """
    global application
    if application is None:
        logger.error("Приложение не инициализировано")
        return
        
    try:
        await application.bot.send_message(chat_id=admin_id, text=message)
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления администратору {admin_id}: {e}")

async def init_application() -> None:
    """
    Инициализирует приложение
    """
    # Инициализируем базу данных
    if not init_database():
        logger.error("Ошибка инициализации базы данных")
        return
    
    # Создаем индекс FAISS, если он не существует
    if not os.path.exists(os.path.join("faiss_index", "index.faiss")):
        logger.info("Создание индекса FAISS...")
        await create_faiss_index()
    
    # Настраиваем обработчик ошибок
    ErrorHandler.set_admin_notify_callback(notify_admin)
    
    # Запускаем мониторинг системы
    system_monitor.set_admin_notify_callback(notify_admin)
    await system_monitor.start_monitoring()
    
    # Выполняем начальную диагностику
    diagnostics = await system_monitor.get_system_diagnostics()
    
    # Уведомляем администраторов о запуске бота
    startup_message = f"🚀 Бот запущен в режиме {APP_ENV}\n\n"
    startup_message += "Диагностика системы:\n"
    startup_message += f"- Память: {diagnostics['system']['ram']['percent']}%\n"
    startup_message += f"- Процессор: {diagnostics['system']['cpu']['percent']}%\n"
    startup_message += f"- Диск: {diagnostics['system']['disk']['percent']}%\n\n"
    
    for admin_id in ADMIN_IDS:
        await notify_admin(admin_id, startup_message)

async def shutdown() -> None:
    """
    Выполняет действия при завершении работы приложения
    """
    global application, shutdown_event, is_running
    
    # Предотвращаем повторный вызов
    if not is_running:
        return
        
    logger.info("Завершение работы приложения...")
    is_running = False
    
    # Останавливаем мониторинг системы
    if hasattr(system_monitor, 'stop_monitoring'):
        try:
            await system_monitor.stop_monitoring()
        except Exception as e:
            logger.error(f"Ошибка при остановке мониторинга: {e}")
    
    # Создаем резервную копию перед выключением
    try:
        if hasattr(backup_manager, 'create_full_backup'):
            await backup_manager.create_full_backup("shutdown")
            logger.info("Создана резервная копия перед завершением работы")
    except Exception as e:
        logger.error(f"Ошибка создания резервной копии перед завершением работы: {e}")
    
    # Уведомляем администраторов о завершении работы
    shutdown_message = "🛑 Бот остановлен"
    
    # Отправляем уведомления только если приложение еще активно
    if application:
        for admin_id in ADMIN_IDS:
            try:
                await notify_admin(admin_id, shutdown_message)
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления о завершении работы администратору {admin_id}: {e}")
    
    # Устанавливаем событие завершения
    if shutdown_event:
        shutdown_event.set()
    
    # Корректно останавливаем приложение
    if application:
        try:
            # Проверяем, запущено ли приложение
            if hasattr(application, 'running') and application.running:
                await application.stop()
                await application.shutdown()
                logger.info("Бот успешно остановлен")
            else:
                logger.info("Бот не был запущен, остановка не требуется")
        except Exception as e:
            logger.error(f"Ошибка при остановке бота: {e}")
    
    logger.info("Процедура завершения выполнена")

def signal_handler(signum, frame):
    """
    Обрабатывает сигналы SIGTERM/SIGINT
    Использует thread-safe механизм для запуска shutdown
    """
    logger.info(f"Получен сигнал {signum}, выполняется завершение работы...")
    
    global is_running, main_loop
    is_running = False
    
    # Использование разового вызова для безопасной остановки
    if main_loop and main_loop.is_running():
        main_loop.call_soon_threadsafe(lambda: asyncio.create_task(shutdown()))
        logger.info("Отправлен сигнал остановки основному циклу событий")

def init_app_database():
    """Инициализация базы данных приложения"""
    try:
        success = init_database()
        if success:
            logger.info("База данных успешно инициализирована")
        else:
            logger.error("Ошибка инициализации базы данных")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при инициализации базы данных: {e}")

def setup_logging():
    """Настройка логирования с фильтрацией чувствительных данных"""
    # Создаем экземпляр фильтра
    sensitive_filter = SensitiveDataFilter()
    
    # Применяем фильтр к основному логгеру
    for handler in logger.handlers:
        handler.addFilter(sensitive_filter)
    
    # Применяем фильтр к логгеру httpx
    httpx_logger = logging.getLogger("httpx")
    for handler in httpx_logger.handlers:
        handler.addFilter(sensitive_filter)
    
    # Если у httpx-логгера нет обработчиков, добавляем их и применяем фильтр
    if not httpx_logger.handlers:
        # Создаем обработчик с таким же форматом, как у основного логгера
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        handler.addFilter(sensitive_filter)
        httpx_logger.addHandler(handler)
    
    # Также добавляем фильтр к корневому логгеру для обработки других внешних библиотек
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(sensitive_filter)
    
    logger.debug("Настроена фильтрация чувствительных данных для всех логгеров")

async def setup_bot_commands(bot: Bot):
    """Настраивает команды бота в меню Telegram"""
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("help", "Показать справку"),
        BotCommand("about", "О боте")
    ]
    
    admin_commands = [
        BotCommand("admin", "Панель администратора"),
        BotCommand("teach", "Добавить запись в базу знаний"),
        BotCommand("add_pdf", "Добавить PDF документ"),
        BotCommand("update_index", "Обновить индекс поиска")
    ]
    
    await bot.set_my_commands(commands)
    
    for admin_id in ADMIN_IDS:
        await bot.set_my_commands(
            commands + admin_commands,
            scope=telegram.BotCommandScopeChat(chat_id=admin_id)
        )
    
    logger.info("Команды бота настроены")

async def main() -> None:
    """
    Основная функция приложения
    """
    global application, main_loop, shutdown_event, is_running
    
    # Настраиваем логирование и маскирование чувствительных данных
    setup_logging()
    
    # Инициализируем базу данных
    init_app_database()
    
    # Инициализируем аналитику
    analytics.update_daily_stats()
    logger.info("Таблицы аналитики успешно инициализированы")
    
    # Настраиваем глобальную обработку ошибок
    setup_error_handlers()
    logger.info("Настроена глобальная обработка ошибок")
    
    # Инициализируем базу данных еще раз для уверенности
    init_app_database()
    
    # Запускаем мониторинг системных ресурсов - ИСПРАВЛЕНО: добавлен await
    await start_resource_monitoring()
    logger.info("Запущен мониторинг системных ресурсов")
    
    # Инициализируем событие завершения
    shutdown_event = asyncio.Event()
    
    # Сохраняем ссылку на основной event loop
    main_loop = asyncio.get_event_loop()
    
    # Создаем экземпляр приложения
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Создаем менеджер уведомлений администраторов
    admin_manager = AdminNotificationManager(application.bot, ADMIN_IDS)
    
    # Сохраняем менеджер в контексте приложения для доступа из других обработчиков
    application.bot_data["admin_manager"] = admin_manager
    
    # Отправляем уведомление о запуске бота
    startup_message = (
        f"🟢 Бот запущен\n"
        f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Среда: {APP_ENV}\n"
        f"База данных: {DB_PATH}\n"
        f"Модель: {MISTRAL_MODEL_PATH}"
    )
    
    await admin_manager.notify_admins(startup_message)
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Обработчик диалога обучения (добавления вопроса и ответа)
    teach_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("teach", start_teach)],
        states={
            AWAITING_KNOWLEDGE_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_knowledge_question)],
            AWAITING_KNOWLEDGE_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_knowledge_answer)]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)]
    )
    application.add_handler(teach_conv_handler)
    
    # Обработчик загрузки PDF
    pdf_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add_pdf", start_add_pdf)],
        states={
            AWAITING_PDF_FILE: [MessageHandler(filters.Document.PDF, process_pdf)]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)]
    )
    application.add_handler(pdf_conv_handler)
    
    # Обработка нажатия на кнопки
    application.add_handler(CallbackQueryHandler(handle_admin_callback))
    
    # Обработка обычных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Настраиваем команды бота
    await setup_bot_commands(application.bot)
    
    # Регистрируем все обработчики
    register_handlers(application)
    
    # Инициализируем менеджер сообщений для рассылки
    await init_messaging_manager(application.bot)
    
    # Регистрация обработчика для базы данных
    application.add_handler(CallbackQueryHandler(handle_admin_db_callback, pattern=r"^admin_db"))
    
    # Регистрируем обработчики сигналов для безопасного завершения
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Настраиваем корректное завершение работы
    exit_handler = setup_graceful_exit(application)
    exit_handler.add_cleanup_task(lambda: logger.info("Завершение работы бота..."))
    
    logger.info("Запуск бота...")
    
    # Запускаем кастомный polling
    await custom_polling(application, exit_handler)

if __name__ == "__main__":
    try:
        # Создаем и запускаем новый event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Запускаем основную функцию
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Завершение работы по Ctrl+C")
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}")
        import traceback
        logger.critical(traceback.format_exc())
        sys.exit(1)
    finally:
        # Закрываем event loop
        if 'loop' in locals() and loop.is_running():
            loop.stop()
        if 'loop' in locals() and not loop.is_closed():
            loop.close()
