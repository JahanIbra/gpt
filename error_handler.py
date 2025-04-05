import sys
import traceback
import logging
import functools
import asyncio
from datetime import datetime
from typing import Callable, Dict, Any, Optional, List, Union

from config import logger, ADMIN_IDS, APP_ENV

class ErrorHandler:
    """Класс для централизованной обработки ошибок в приложении"""
    
    _admin_notify_callback = None
    _error_log = []
    _max_log_size = 100  # Максимальное количество записей в журнале ошибок
    
    @classmethod
    def set_admin_notify_callback(cls, callback: Callable):
        """
        Устанавливает функцию обратного вызова для уведомления администраторов
        
        Args:
            callback: Функция для отправки уведомлений администраторам
        """
        cls._admin_notify_callback = callback
    
    @classmethod
    def log_error(cls, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Логирует ошибку и отправляет уведомление администраторам
        
        Args:
            error: Объект исключения
            context: Контекст, в котором произошла ошибка
            
        Returns:
            Словарь с информацией об ошибке
        """
        # Получаем трассировку стека
        tb = traceback.format_exc()
        
        # Формируем запись об ошибке
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "traceback": tb
        }
        
        # Логируем ошибку
        logger.error(f"Ошибка: {error_info['error_type']} - {error_info['error_message']}")
        logger.error(f"Контекст: {context}")
        logger.error(f"Трассировка:\n{tb}")
        
        # Добавляем в журнал ошибок
        cls._add_to_error_log(error_info)
        
        # Отправляем уведомление администраторам
        cls._notify_admins(error_info)
        
        return error_info
    
    @classmethod
    def _add_to_error_log(cls, error_info: Dict[str, Any]):
        """
        Добавляет запись в журнал ошибок
        
        Args:
            error_info: Информация об ошибке
        """
        cls._error_log.append(error_info)
        
        # Ограничиваем размер журнала
        if len(cls._error_log) > cls._max_log_size:
            cls._error_log = cls._error_log[-cls._max_log_size:]
    
    @classmethod
    def _notify_admins(cls, error_info: Dict[str, Any]):
        """
        Отправляет уведомление администраторам об ошибке
        
        Args:
            error_info: Информация об ошибке
        """
        if cls._admin_notify_callback is None:
            return
        
        # Формируем сообщение для администраторов
        message = (
            f"❌ <b>Ошибка в боте</b>\n\n"
            f"<b>Тип:</b> {error_info['error_type']}\n"
            f"<b>Сообщение:</b> {error_info['error_message']}\n"
            f"<b>Контекст:</b> {error_info['context']}\n\n"
            f"<b>Время:</b> {error_info['timestamp']}\n"
            f"<b>Среда:</b> {APP_ENV}"
        )
        
        # В режиме разработки добавляем трассировку
        if APP_ENV == "development":
            message += f"\n\n<b>Трассировка:</b>\n<code>{error_info['traceback'][:1000]}</code>"
        
        # Отправляем уведомление каждому администратору
        for admin_id in ADMIN_IDS:
            try:
                asyncio.create_task(cls._admin_notify_callback(admin_id, message))
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления администратору {admin_id}: {e}")
    
    @classmethod
    def get_error_log(cls) -> List[Dict[str, Any]]:
        """
        Возвращает журнал ошибок
        
        Returns:
            Список словарей с информацией об ошибках
        """
        return cls._error_log.copy()
        
    @classmethod
    def register_telegram_error_handlers(cls):
        """
        Регистрирует обработчики ошибок для Telegram бота
        
        Примечание: 
        Этот метод будет вызываться, когда экземпляр приложения Telegram уже создан,
        но может не иметь к нему доступа. Вместо этого он настраивает класс ErrorHandler
        для работы с ошибками, которые могут возникнуть в обработчиках Telegram.
        """
        logger.info("Настроены обработчики ошибок Telegram")
        
        # Так как у нас нет доступа к экземпляру приложения здесь,
        # мы просто подготавливаем класс к работе с ошибками Telegram.
        # Обработка ошибок фактически происходит через декораторы и
        # глобальные обработчики, которые уже настроены.
        return True

def catch_exceptions(log_message: str = "Ошибка в функции"):
    """
    Декоратор для перехвата и обработки исключений
    
    Args:
        log_message: Сообщение для логирования
        
    Returns:
        Декорированная функция
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                ErrorHandler.log_error(e, f"{log_message} {func.__name__}")
                # Возвращаем None или другое значение по умолчанию
                return None
                
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                ErrorHandler.log_error(e, f"{log_message} {func.__name__}")
                # Возвращаем None или другое значение по умолчанию
                return None
        
        # Определяем, какой враппер использовать
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
        
    return decorator

def async_error_handler(func):
    """
    Декоратор для обработки ошибок в асинхронных функциях
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            ErrorHandler.log_error(e, f"Ошибка в {func.__name__}")
            
            # Если это обработчик Telegram, возможно есть объект update
            if args and hasattr(args[0], 'effective_chat') and hasattr(args[1], 'bot'):
                update = args[0]
                context = args[1]
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
                    )
                except Exception:
                    pass
            
            # Логируем ошибку дополнительно
            logger.exception(f"Необработанное исключение в {func.__name__}")
            
    return wrapper

def handle_error(update, context):
    """
    Обработчик ошибок для Telegram бота
    
    Args:
        update: Объект обновления
        context: Контекст бота
    """
    # Получаем информацию об ошибке
    error = context.error
    
    # Логируем ошибку
    error_info = ErrorHandler.log_error(error, "Telegram dispatcher error")
    
    # Отправляем сообщение пользователю
    if update and update.effective_chat:
        try:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
            )
        except Exception:
            pass

def setup_global_error_handling():
    """
    Настраивает глобальную обработку ошибок
    """
    def global_exception_handler(exc_type, exc_value, exc_traceback):
        """
        Обработчик необработанных исключений
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # Пропускаем KeyboardInterrupt, чтобы можно было прервать программу
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Логируем ошибку
        ErrorHandler.log_error(exc_value, "Необработанное исключение")
    
    # Устанавливаем глобальный обработчик исключений
    sys.excepthook = global_exception_handler
    
    # Настраиваем обработку ошибок в асинхронных функциях
    loop = asyncio.get_event_loop()
    
    def handle_async_exception(loop, context):
        """
        Обработчик исключений для event loop
        """
        # Извлекаем исключение
        exception = context.get('exception', None)
        
        if exception:
            ErrorHandler.log_error(exception, "Необработанное асинхронное исключение")
        else:
            # Если исключение недоступно, логируем весь контекст
            logger.error(f"Ошибка в event loop: {context}")
    
    loop.set_exception_handler(handle_async_exception)
    
    logger.info("Настроена глобальная обработка ошибок")

def setup_error_handlers():
    """
    Настраивает обработчики ошибок для бота
    
    Returns:
        True, если настройка успешна
    """
    try:
        # Настраиваем глобальные обработчики исключений
        setup_global_error_handling()
        
        # Настраиваем обработчик для Telegram-ошибок 
        # (будет вызываться, если в callback_context есть ошибка)
        ErrorHandler.register_telegram_error_handlers()
        
        logger.info("Обработчики ошибок настроены")
        return True
    except Exception as e:
        logger.error(f"Ошибка настройки обработчиков ошибок: {e}")
        return False
