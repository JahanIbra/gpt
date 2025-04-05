"""
Модуль для обеспечения корректной работы с telegram в других модулях проекта.
Этот файл должен быть импортирован перед любыми другими импортами telegram.
"""

import telegram as telegram_module
# Экспортируем telegram как модуль для использования в импортах
telegram = telegram_module

# Экспортируем все основные компоненты, которые могут быть использованы
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, Application, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.constants import ParseMode

import asyncio
import signal
import sys
import threading
from typing import Dict, List, Any, Optional, Callable
import time
from config import logger

class GracefulExitHandler:
    """Класс для корректной обработки сигналов завершения работы"""
    
    def __init__(self, application: Application):
        """
        Инициализирует обработчик завершения работы
        
        Args:
            application: Экземпляр приложения Telegram
        """
        self.application = application
        self.shutdown_event = asyncio.Event()
        self.cleanup_tasks = []
        self.shutdown_in_progress = False
        
        # Сохраняем оригинальный обработчик для корректного завершения
        self.original_handler = signal.getsignal(signal.SIGINT)
        
    def add_cleanup_task(self, task: Callable) -> None:
        """
        Добавляет задачу для выполнения перед завершением
        
        Args:
            task: Функция для выполнения при завершении
        """
        self.cleanup_tasks.append(task)
        
    def register_signals(self) -> None:
        """Регистрирует обработчики сигналов для корректного завершения"""
        signal.signal(signal.SIGINT, self._handle_sigint)
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        
    def _handle_sigint(self, sig, frame) -> None:
        """Обрабатывает сигнал SIGINT (Ctrl+C)"""
        if self.shutdown_in_progress:
            # Если получен повторный сигнал, завершаем немедленно
            logger.warning("Получен повторный сигнал SIGINT, принудительное завершение")
            sys.exit(1)
            
        self.shutdown_in_progress = True
        logger.info("Получен сигнал 2, выполняется завершение работы...")
        
        # Запускаем асинхронное завершение в новом потоке
        threading.Thread(target=self._run_async_shutdown).start()
        
    def _handle_sigterm(self, sig, frame) -> None:
        """Обрабатывает сигнал SIGTERM"""
        if self.shutdown_in_progress:
            return
            
        self.shutdown_in_progress = True
        logger.info("Получен сигнал SIGTERM, выполняется завершение работы...")
        
        # Запускаем асинхронное завершение в новом потоке
        threading.Thread(target=self._run_async_shutdown).start()
        
    def _run_async_shutdown(self) -> None:
        """Запускает асинхронное завершение работы в отдельном потоке"""
        # Создаем новый цикл событий для текущего потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Запускаем асинхронное завершение
            loop.run_until_complete(self._shutdown())
        finally:
            # Закрываем цикл событий
            loop.close()
            
            # Принудительно завершаем процесс после таймаута
            # Это гарантирует, что процесс точно завершится
            time.sleep(2)  # Даем время на завершение логирования
            logger.info("Процесс завершен")
            sys.exit(0)
            
    async def _shutdown(self) -> None:
        """Выполняет корректное завершение работы приложения"""
        logger.info("Отправлен сигнал остановки основному циклу событий")
        
        # Выполняем все задачи очистки
        for task in self.cleanup_tasks:
            try:
                if asyncio.iscoroutinefunction(task):
                    await task()
                else:
                    task()
            except Exception as e:
                logger.error(f"Ошибка при выполнении задачи очистки: {e}")
        
        # Останавливаем приложение Telegram
        await self.application.stop()
        
        # Устанавливаем событие завершения
        self.shutdown_event.set()

def setup_graceful_exit(application: Application) -> GracefulExitHandler:
    """
    Настраивает корректное завершение приложения
    
    Args:
        application: Экземпляр приложения Telegram
        
    Returns:
        Обработчик корректного завершения
    """
    handler = GracefulExitHandler(application)
    handler.register_signals()
    return handler

async def custom_polling(application: Application, exit_handler: Optional[GracefulExitHandler] = None) -> None:
    """
    Запускает кастомный polling с корректной обработкой завершения
    
    Args:
        application: Экземпляр приложения Telegram
        exit_handler: Обработчик корректного завершения (опционально)
    """
    # Запускаем приложение
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Запущен кастомный polling для бота")
    
    try:
        # Ожидаем сигнала завершения, если есть обработчик
        if exit_handler:
            await exit_handler.shutdown_event.wait()
        else:
            # Иначе ожидаем бесконечно
            while True:
                await asyncio.sleep(1)
    except asyncio.CancelledError:
        # Если задача была отменена, завершаем корректно
        pass
    finally:
        # Останавливаем updater и приложение
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Кастомный polling остановлен")

# Экспортируем все для доступности через этот модуль
__all__ = [
    'telegram', 'telegram_module', 'Update', 'InlineKeyboardMarkup', 
    'InlineKeyboardButton', 'ContextTypes', 'Application', 
    'CommandHandler', 'MessageHandler', 'CallbackQueryHandler', 'ParseMode',
    'GracefulExitHandler', 'setup_graceful_exit', 'custom_polling'
]
