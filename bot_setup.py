import logging
import sys
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

logger = logging.getLogger("bot")

def setup_bot(token: str) -> Application:
    """Настраивает и возвращает экземпляр приложения бота"""
    # Создаем экземпляр приложения
    application = Application.builder().token(token).build()
    
    # Импортируем необходимые модули
    from error_handlers import setup_error_handlers
    
    # Настраиваем обработчики ошибок
    setup_error_handlers(application)
    
    # Регистрируем обработчики команд
    from admin_handlers import admin_panel
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Добавляем тестовую команду
    from admin_test import test_command, register_test_command
    register_test_command(application)
    
    # Создаем прямой обработчик для всех callback-запросов
    async def direct_callback_handler(update: Update, context):
        """Централизованный обработчик всех callback-запросов"""
        query = update.callback_query
        callback_data = query.data
        
        logger.info(f"Получен callback: {callback_data}")
        
        # Импортируем admin_handlers напрямую здесь
        from admin_handlers import admin_handlers
        
        # Прямая проверка наличия обработчика
        if callback_data in admin_handlers:
            logger.info(f"Найден обработчик для {callback_data}")
            handler = admin_handlers[callback_data]
            try:
                await handler(update, context)
                return
            except Exception as e:
                logger.error(f"Ошибка при выполнении обработчика для {callback_data}: {e}")
                await query.answer(f"Ошибка: {str(e)[:50]}")
                return
        
        # Проверяем префиксы
        for prefix, handler in admin_handlers.items():
            if ":" in prefix and callback_data.startswith(prefix.split(":")[0] + ":"):
                logger.info(f"Найден префиксный обработчик {prefix} для {callback_data}")
                try:
                    await handler(update, context)
                    return
                except Exception as e:
                    logger.error(f"Ошибка при выполнении префиксного обработчика: {e}")
                    await query.answer(f"Ошибка: {str(e)[:50]}")
                    return
        
        # Если обработчик не найден
        logger.warning(f"Обработчик не найден для: {callback_data}")
        await query.answer(f"Команда не найдена: {callback_data}")
    
    # Регистрируем прямой обработчик для всех callback-запросов
    application.add_handler(CallbackQueryHandler(direct_callback_handler))
    
    logger.info("Бот настроен с использованием прямых обработчиков")
    return application
