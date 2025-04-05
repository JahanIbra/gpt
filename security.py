import os
import functools
import logging
import re
import json
import time
import threading
from typing import List, Set, Callable, Optional, Any, Dict, Tuple
from telegram import Update
from config import ADMIN_IDS, logger, RATE_LIMIT, RATE_LIMIT_TIME
from telegram.constants import ParseMode
from collections import defaultdict
from telegram.ext import ContextTypes
import asyncio
from datetime import datetime, timedelta
import hashlib

# Создаем класс безопасности для централизованного управления
class SecurityManager:
    """Менеджер безопасности для контроля доступа и защиты от злоупотреблений"""
    
    def __init__(self):
        """Инициализирует менеджер безопасности"""
        self.blocked_users = set()
        self.suspicious_users = {}  # user_id -> количество нарушений
        self.user_messages = {}     # user_id -> [timestamp1, timestamp2, ...]
        self.user_last_action = {}  # user_id -> timestamp
        self.lock = threading.Lock()
        self.rate_limit = RATE_LIMIT
        self.rate_time = RATE_LIMIT_TIME
        self.max_violations = 10    # Максимальное количество нарушений до блокировки
        self.violation_reset = 86400  # 24 часа - время сброса счетчика нарушений
        
        # Загружаем заблокированных пользователей из файла
        self._load_blocked_users()
    
    def _load_blocked_users(self):
        """Загружает список заблокированных пользователей из файла"""
        try:
            if os.path.exists('blocked_users.json'):
                with open('blocked_users.json', 'r') as f:
                    data = json.load(f)
                    self.blocked_users = set(data.get('blocked_users', []))
                    logger.info(f"Загружено {len(self.blocked_users)} заблокированных пользователей")
        except Exception as e:
            logger.error(f"Ошибка загрузки списка заблокированных пользователей: {e}")
    
    def _save_blocked_users(self):
        """Сохраняет список заблокированных пользователей в файл"""
        try:
            with open('blocked_users.json', 'w') as f:
                json.dump({'blocked_users': list(self.blocked_users)}, f)
        except Exception as e:
            logger.error(f"Ошибка сохранения списка заблокированных пользователей: {e}")
    
    def block_user(self, user_id: int, reason: str = ""):
        """
        Блокирует пользователя
        
        Args:
            user_id: ID пользователя
            reason: Причина блокировки
        """
        with self.lock:
            self.blocked_users.add(user_id)
            self._save_blocked_users()
            logger.warning(f"Пользователь {user_id} заблокирован. Причина: {reason}")
    
    def unblock_user(self, user_id: int):
        """
        Разблокирует пользователя
        
        Args:
            user_id: ID пользователя
        """
        with self.lock:
            if user_id in self.blocked_users:
                self.blocked_users.remove(user_id)
                self._save_blocked_users()
                logger.info(f"Пользователь {user_id} разблокирован")
    
    def is_blocked(self, user_id: int) -> bool:
        """
        Проверяет, заблокирован ли пользователь
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True, если пользователь заблокирован
        """
        return user_id in self.blocked_users
    
    def register_violation(self, user_id: int, violation_type: str):
        """
        Регистрирует нарушение пользователя
        
        Args:
            user_id: ID пользователя
            violation_type: Тип нарушения
        """
        if user_id in ADMIN_IDS:
            return  # Не регистрируем нарушения для администраторов
        
        with self.lock:
            current_time = time.time()
            
            # Сбрасываем счетчик нарушений, если прошло достаточно времени
            if user_id in self.suspicious_users:
                last_violation_time = self.suspicious_users[user_id].get('last_time', 0)
                if current_time - last_violation_time > self.violation_reset:
                    self.suspicious_users[user_id]['count'] = 0
            
            # Инициализируем или обновляем счетчик нарушений
            if user_id not in self.suspicious_users:
                self.suspicious_users[user_id] = {'count': 1, 'last_time': current_time, 'types': [violation_type]}
            else:
                self.suspicious_users[user_id]['count'] += 1
                self.suspicious_users[user_id]['last_time'] = current_time
                self.suspicious_users[user_id]['types'].append(violation_type)
            
            # Проверяем, не превышен ли лимит нарушений
            if self.suspicious_users[user_id]['count'] >= self.max_violations:
                types = self.suspicious_users[user_id]['types']
                reason = f"Превышен лимит нарушений: {', '.join(types[-5:])}"
                self.block_user(user_id, reason)
    
    def check_rate_limit(self, user_id: int) -> bool:
        """
        Проверяет, не превышен ли лимит запросов пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True, если лимит не превышен
        """
        if user_id in ADMIN_IDS:
            return True  # Для администраторов всегда разрешаем
        
        with self.lock:
            current_time = time.time()
            
            # Инициализируем список сообщений для нового пользователя
            if user_id not in self.user_messages:
                self.user_messages[user_id] = []
            
            # Удаляем устаревшие метки времени
            self.user_messages[user_id] = [t for t in self.user_messages[user_id] 
                                          if current_time - t < self.rate_time]
            
            # Проверяем количество сообщений
            if len(self.user_messages[user_id]) >= self.rate_limit:
                self.register_violation(user_id, "rate_limit")
                return False
            
            # Добавляем текущее время
            self.user_messages[user_id].append(current_time)
            return True
    
    def update_last_action(self, user_id: int):
        """
        Обновляет время последнего действия пользователя
        
        Args:
            user_id: ID пользователя
        """
        with self.lock:
            self.user_last_action[user_id] = time.time()
    
    def get_inactive_users(self, days: int = 30) -> List[int]:
        """
        Возвращает список неактивных пользователей
        
        Args:
            days: Количество дней неактивности
            
        Returns:
            Список ID неактивных пользователей
        """
        current_time = time.time()
        inactive_threshold = days * 86400  # days to seconds
        
        inactive_users = []
        for user_id, last_time in self.user_last_action.items():
            if current_time - last_time > inactive_threshold:
                inactive_users.append(user_id)
        
        return inactive_users
    
    def get_blocked_users(self) -> List[int]:
        """
        Возвращает список заблокированных пользователей
        
        Returns:
            Список ID заблокированных пользователей
        """
        return list(self.blocked_users)
    
    def get_suspicious_users(self) -> Dict[int, Dict[str, Any]]:
        """
        Возвращает список подозрительных пользователей с информацией о нарушениях
        
        Returns:
            Словарь {user_id: {count: int, last_time: float, types: List[str]}}
        """
        return self.suspicious_users.copy()
    
    def validate_user_input(self, text: str) -> Tuple[bool, str]:
        """
        Проверяет пользовательский ввод на потенциально опасные паттерны
        
        Args:
            text: Текст для проверки
            
        Returns:
            Кортеж (безопасно, сообщение об ошибке)
        """
        if not isinstance(text, str):
            text = str(text)  # ранее: if callable(text): text = text()
        # Ограничиваем длину сообщения
        if not text or len(text.strip()) == 0:
            return False, "Ввод не может быть пустым"
        
        if len(text) > 2000:
            return False, "Сообщение слишком длинное (максимум 2000 символов)"
        
        # Проверяем на наличие потенциально опасных паттернов
        dangerous_patterns = [
            r"(?:--|\{|\}|;|&&|\|\||\$\(|\`)",  # SQL/команды
            r"<script.*?>",  # XSS
            r"(?:/etc/passwd|/etc/shadow|/proc/self)",  # Пути к системным файлам
            r"(?:exec\s*\(|system\s*\(|eval\s*\()",  # Выполнение кода
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False, "В сообщении обнаружен подозрительный контент"
        
        return True, ""

    # Функция-алиас для совместимости
    def validate_input(self, text: str) -> Tuple[bool, str]:
        """
        Алиас для функции validate_user_input
        
        Args:
            text: Текст для проверки
            
        Returns:
            Кортеж (безопасно, сообщение об ошибке)
        """
        return self.validate_user_input(text)

# Добавление функции validate_user_input для проверки безопасности пользовательского ввода
def validate_user_input(text: str) -> tuple[bool, str]:
    """
    Проверяет пользовательский ввод на наличие потенциально опасного содержимого
    
    Args:
        text: Текст для проверки
        
    Returns:
        tuple: (is_valid, message)
            - is_valid: True если ввод безопасен, False в противном случае
            - message: Сообщение с результатом проверки или ошибкой
    """
    if not isinstance(text, str):
        text = str(text)  # ранее: if callable(text): text = text()
    if not text or len(text.strip()) == 0:
        return False, "Ввод не может быть пустым"
    
    # Проверка на превышение допустимой длины
    if len(text) > 4000:
        return False, "Ввод слишком длинный (максимум 4000 символов)"
    
    # Проверка на наличие потенциально опасных последовательностей
    dangerous_patterns = [
        "javascript:", 
        "<script>", 
        "eval(", 
        "exec(",
        "system(",
        "os.",
        "subprocess"
    ]
    
    for pattern in dangerous_patterns:
        if pattern.lower() in text.lower():
            return False, "Обнаружено потенциально опасное содержимое"
    
    return True, "Ввод прошел проверку безопасности"

# Создаем глобальный экземпляр менеджера безопасности
security_manager = SecurityManager()

# Декораторы для использования в обработчиках
def admin_required(func):
    """
    Декоратор для проверки, является ли пользователь администратором
    """
    @functools.wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text(
                "⛔ У вас нет доступа к этой функции."
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def rate_limit(limit: int = None):
    """
    Декоратор для ограничения частоты запросов
    
    Args:
        limit: Максимальное количество запросов в течение времени RATE_LIMIT_TIME
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            user_id = update.effective_user.id
            
            # Проверяем, заблокирован ли пользователь
            if security_manager.is_blocked(user_id):
                await update.message.reply_text(
                    "⛔ Ваш доступ к боту ограничен. Обратитесь к администратору."
                )
                return
            
            # Проверяем лимит запросов
            if not security_manager.check_rate_limit(user_id):
                await update.message.reply_text(
                    "⚠️ Слишком много запросов. Пожалуйста, подождите некоторое время."
                )
                return
            
            # Обновляем время последнего действия
            security_manager.update_last_action(user_id)
            
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

def validate_user_input_decorator(func):
    """
    Декоратор для проверки безопасности пользовательского ввода
    """
    @functools.wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Если сообщение содержит текст, проверяем его
        if update.message and update.message.text:
            text = update.message.text
            is_safe, error_message = security_manager.validate_user_input(text)
            if not is_safe:
                await update.message.reply_text(
                    f"⚠️ {error_message}\n\nВаше сообщение не было обработано из соображений безопасности."
                )
                return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

def prevent_bot_abuse():
    """
    Декоратор для предотвращения злоупотребления ботом
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            user_id = update.effective_user.id
            
            # Проверяем паттерны злоупотребления
            if check_bot_abuse(update):
                security_manager.register_violation(user_id, "bot_abuse")
                await update.message.reply_text(
                    "⚠️ Обнаружено подозрительное использование бота."
                )
                return
            
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

def check_bot_abuse(update) -> bool:
    """
    Проверяет сообщение на признаки злоупотребления ботом
    
    Args:
        update: Объект Update от Telegram
        
    Returns:
        True, если обнаружено злоупотребление
    """
    # Проверка на наличие команд других ботов
    if update.message and update.message.text:
        if update.message.text.startswith('/') and '@' in update.message.text:
            return True
    
    return False

# Добавляем __all__ для явного определения экспортируемых имен
__all__ = [
    'SecurityManager', 
    'security_manager', 
    'admin_required', 
    'rate_limit', 
    'validate_user_input', 
    'prevent_bot_abuse', 
    'check_bot_abuse'
]

# Выполняем дополнительную инициализацию при импорте модуля
logger.info("Модуль безопасности инициализирован")
