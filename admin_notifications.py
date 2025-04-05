from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime
from telegram import Bot
from telegram.error import Forbidden, TelegramError

from config import logger

class AdminNotificationManager:
    """Управление уведомлениями для администраторов"""
    
    def __init__(self, bot: Bot, admin_ids: List[int]):
        """
        Инициализирует менеджер уведомлений
        
        Args:
            bot: Экземпляр бота Telegram
            admin_ids: Список ID администраторов
        """
        self.bot = bot
        self.admin_ids = admin_ids
        self.blocked_admins = set()  # Администраторы, заблокировавшие бота
        self.last_notification = {}  # Время последнего уведомления для каждого админа
    
    async def notify_admins(self, message: str, parse_mode: Optional[str] = None) -> Dict[int, bool]:
        """
        Отправляет уведомление всем администраторам
        
        Args:
            message: Текст уведомления
            parse_mode: Режим форматирования текста
            
        Returns:
            Словарь {admin_id: status} с результатами отправки
        """
        results = {}
        
        for admin_id in self.admin_ids:
            # Пропускаем администраторов, которые заблокировали бота
            if admin_id in self.blocked_admins:
                logger.debug(f"Пропуск уведомления администратору {admin_id} (бот заблокирован)")
                results[admin_id] = False
                continue
            
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode=parse_mode
                )
                self.last_notification[admin_id] = datetime.now()
                results[admin_id] = True
                
            except Forbidden as e:
                # Администратор заблокировал бота
                logger.warning(f"Администратор {admin_id} заблокировал бота. Уведомления отключены.")
                self.blocked_admins.add(admin_id)
                results[admin_id] = False
                
            except TelegramError as e:
                logger.error(f"Ошибка отправки уведомления администратору {admin_id}: {e}")
                results[admin_id] = False
        
        return results
    
    async def notify_admin(self, admin_id: int, message: str, parse_mode: Optional[str] = None) -> bool:
        """
        Отправляет уведомление конкретному администратору
        
        Args:
            admin_id: ID администратора
            message: Текст уведомления
            parse_mode: Режим форматирования текста
            
        Returns:
            True если уведомление отправлено успешно
        """
        # Проверяем, не заблокирован ли бот этим администратором
        if admin_id in self.blocked_admins:
            logger.debug(f"Пропуск уведомления администратору {admin_id} (бот заблокирован)")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode=parse_mode
            )
            self.last_notification[admin_id] = datetime.now()
            return True
            
        except Forbidden as e:
            # Администратор заблокировал бота
            logger.warning(f"Администратор {admin_id} заблокировал бота. Уведомления отключены.")
            self.blocked_admins.add(admin_id)
            return False
            
        except TelegramError as e:
            logger.error(f"Ошибка отправки уведомления администратору {admin_id}: {e}")
            return False
    
    def reset_blocked_status(self, admin_id: int) -> None:
        """
        Сбрасывает статус блокировки для администратора
        
        Args:
            admin_id: ID администратора
        """
        if admin_id in self.blocked_admins:
            self.blocked_admins.remove(admin_id)
            logger.info(f"Сброшен статус блокировки для администратора {admin_id}")
    
    def get_available_admins(self) -> List[int]:
        """
        Возвращает список доступных администраторов
        
        Returns:
            Список ID администраторов, которые не блокировали бота
        """
        return [admin_id for admin_id in self.admin_ids if admin_id not in self.blocked_admins]
