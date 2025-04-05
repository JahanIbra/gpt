import os
import logging
import sys
import time
import threading
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from contextlib import contextmanager

from config import LOG_LEVEL, logger as config_logger

# Создаем директорию для логов, если она не существует
os.makedirs('logs', exist_ok=True)

# Настройка файлового обработчика
file_handler = logging.FileHandler('logs/bot.log')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Получаем логгер из конфигурации и добавляем файловый обработчик
logger = config_logger
logger.addHandler(file_handler)

# Блокировка для потокобезопасного доступа
_log_lock = threading.Lock()

class SensitiveDataFilter(logging.Filter):
    """Фильтр для маскирования чувствительных данных в логах"""
    
    def __init__(self):
        super().__init__()
        # Паттерны для обнаружения токенов, API ключей и т.д.
        self.patterns = [
            # Токены Telegram в URL запросах api.telegram.org
            re.compile(r'(https?://api\.telegram\.org/bot)(\d+:[A-Za-z0-9\-_]+)(/\w+)'),
            # Токены Telegram в обычном тексте
            re.compile(r'bot(\d+):([A-Za-z0-9\-_]+)'),
            # Другие API ключи можно добавить по аналогии
        ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern in self.patterns:
                # Для URL используем специальную замену, сохраняющую структуру URL
                if 'api.telegram.org/bot' in record.msg:
                    record.msg = pattern.sub(r'\1\2:***СКРЫТО***\3', record.msg)
                else:
                    record.msg = pattern.sub(r'bot\1:***СКРЫТО***', record.msg)
        
        # Проверяем args если они есть
        if record.args:
            record.args = self._filter_args(record.args)
        
        return True
    
    def _filter_args(self, args: Any) -> Any:
        """Рекурсивно обрабатывает аргументы"""
        if isinstance(args, dict):
            return {k: self._filter_value(v) for k, v in args.items()}
        elif isinstance(args, (list, tuple)):
            return type(args)(self._filter_value(arg) for arg in args)
        return args
    
    def _filter_value(self, value: Any) -> Any:
        """Маскирует чувствительные данные в значении"""
        if isinstance(value, str):
            for pattern in self.patterns:
                value = pattern.sub(r'bot\1:***СКРЫТО***', value)
        return value

def setup_enhanced_logging(name: str, level: str = "INFO") -> logging.Logger:
    """
    Настраивает логгер с фильтрацией чувствительных данных
    
    Args:
        name: Имя логгера
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    
    # Устанавливаем уровень логирования
    level_num = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(level_num)
    
    # Если у логгера еще нет обработчиков, добавляем их
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level_num)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Добавляем фильтр для маскирования чувствительных данных
        handler.addFilter(SensitiveDataFilter())
        
        logger.addHandler(handler)
    
    return logger

class LoggingContext:
    """Контекстный менеджер для структурированного логирования"""
    
    def __init__(self, logger, operation: str = None, **context_data):
        """
        Инициализирует контекст логирования
        
        Args:
            logger: Объект логгера
            operation: Название операции (опционально)
            **context_data: Дополнительные данные для логирования
        """
        self.logger = logger
        self.operation = operation
        self.context_data = context_data
        self.start_time = None
    
    def __enter__(self):
        """Входит в контекст логирования"""
        self.start_time = time.time()
        
        if self.operation:
            context_str = ""
            if self.context_data:
                context_str = " " + json.dumps(self.context_data)
            
            self.logger.info(f"Started {self.operation}{context_str}")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выходит из контекста логирования"""
        duration = time.time() - self.start_time
        
        if exc_type is not None:
            # Если произошло исключение
            error_details = {
                "error_type": exc_type.__name__,
                "error_message": str(exc_val),
                "duration": f"{duration:.3f}s"
            }
            
            if self.context_data:
                error_details.update(self.context_data)
            
            self.logger.error(f"Failed {self.operation}: {json.dumps(error_details)}")
        else:
            # Если операция завершилась успешно
            if self.operation:
                success_details = {"duration": f"{duration:.3f}s"}
                
                if self.context_data:
                    success_details.update(self.context_data)
                
                self.logger.info(f"Completed {self.operation}: {json.dumps(success_details)}")

class StructuredLogger:
    """Класс для структурированного логирования в формате JSON"""
    
    def __init__(self, name: str, log_file: str, console: bool = True):
        """
        Инициализирует структурированный логгер
        
        Args:
            name: Имя логгера
            log_file: Путь к файлу логов
            console: Выводить логи в консоль
        """
        self.name = name
        self.log_file = log_file
        self.default_context = {}
        
        # Создаем базовый логгер
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Создаем обработчик файла
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Создаем обработчик консоли, если нужно
        if console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            self.logger.addHandler(console_handler)
        
        # Добавляем обработчик файла
        self.logger.addHandler(file_handler)
    
    def set_default_context(self, **context):
        """
        Устанавливает контекст по умолчанию для всех сообщений
        
        Args:
            **context: Данные контекста
        """
        self.default_context = context
    
    def log(self, level: int, message: str, **context):
        """
        Логирует сообщение с заданным уровнем и контекстом
        
        Args:
            level: Уровень логирования
            message: Сообщение
            **context: Данные контекста
        """
        # Объединяем контекст по умолчанию с переданным контекстом
        log_context = {**self.default_context, **context}
        
        # Формируем структурированное сообщение
        structured_data = {
            "timestamp": datetime.now().isoformat(),
            "level": logging.getLevelName(level),
            "logger": self.name,
            "message": message,
            "context": log_context
        }
        
        # Логируем структурированное сообщение
        with _log_lock:
            self.logger.log(level, json.dumps(structured_data))
    
    def info(self, message: str, **context):
        """Логирует сообщение с уровнем INFO"""
        self.log(logging.INFO, message, **context)
    
    def warning(self, message: str, **context):
        """Логирует сообщение с уровнем WARNING"""
        self.log(logging.WARNING, message, **context)
    
    def error(self, message: str, **context):
        """Логирует сообщение с уровнем ERROR"""
        self.log(logging.ERROR, message, **context)
    
    def critical(self, message: str, **context):
        """Логирует сообщение с уровнем CRITICAL"""
        self.log(logging.CRITICAL, message, **context)
    
    def exception(self, message: str, exc_info=True, **context):
        """Логирует исключение"""
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        if exc_type is not None:
            # Добавляем информацию об исключении в контекст
            context["exception"] = {
                "type": exc_type.__name__,
                "message": str(exc_value),
                "traceback": traceback.format_exc()
            }
        
        self.log(logging.ERROR, message, **context)

def log_critical_error(message: str, error: Exception = None, details: Dict[str, Any] = None):
    """
    Логирует критическую ошибку и отправляет уведомление администраторам
    
    Args:
        message: Сообщение об ошибке
        error: Объект исключения (опционально)
        details: Дополнительные детали (опционально)
    """
    error_data = {
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    
    if error:
        error_data["error_type"] = type(error).__name__
        error_data["error_message"] = str(error)
        error_data["traceback"] = traceback.format_exc()
    
    if details:
        error_data["details"] = details
    
    # Логируем ошибку
    error_json = json.dumps(error_data, indent=2)
    logger.critical(f"КРИТИЧЕСКАЯ ОШИБКА: {message}")
    logger.critical(error_json)
    
    # Сохраняем ошибку в отдельный файл
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error_file = os.path.join("logs", f"critical_error_{timestamp}.json")
        
        with open(error_file, "w", encoding="utf-8") as f:
            f.write(error_json)
        
        logger.info(f"Информация о критической ошибке сохранена в {error_file}")
    except Exception as e:
        logger.error(f"Не удалось сохранить информацию о критической ошибке: {e}")

@contextmanager
def log_execution_time(operation_name: str):
    """
    Контекстный менеджер для логирования времени выполнения операции
    
    Args:
        operation_name: Название операции
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"Операция '{operation_name}' выполнена за {duration:.3f} сек")

# Настраиваем структурированный логгер, если это нужно
structured_logger = StructuredLogger(
    name="structured",
    log_file="logs/structured.log",
    console=False
)

# Экспортируем основной логгер для использования в других модулях
__all__ = ['logger', 'LoggingContext', 'log_critical_error', 'log_execution_time', 'structured_logger', 'setup_enhanced_logging']
