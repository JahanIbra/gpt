import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import time

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError, Forbidden, BadRequest

from config import logger, ADMIN_IDS
from database import get_all_users, log_admin_message, update_admin_message_stats, add_user_if_not_exists

class AdminMessagingManager:
    """Класс для управления сообщениями администраторов пользователям"""
    
    def __init__(self, bot: Bot):
        """
        Инициализирует менеджер сообщений
        
        Args:
            bot: Экземпляр бота Telegram
        """
        self.bot = bot
        self.in_progress_broadcasts = {}
        self.canceled_broadcasts = set()
    
    async def broadcast_message(self, admin_id: int, message_text: str, 
                              parse_mode: Optional[str] = None) -> Tuple[int, int, int]:
        """
        Отправляет сообщение всем пользователям бота
        
        Args:
            admin_id: ID администратора
            message_text: Текст сообщения
            parse_mode: Режим форматирования текста
            
        Returns:
            Кортеж (всего_пользователей, успешно_отправлено, ошибок)
        """
        # Записываем сообщение в базу данных
        message_id = log_admin_message(admin_id, message_text)
        
        # Получаем список всех пользователей
        users = get_all_users()
        
        total_users = len(users)
        success_count = 0
        error_count = 0
        
        # Запоминаем, что запущена рассылка
        self.in_progress_broadcasts[message_id] = {
            "admin_id": admin_id,
            "started_at": datetime.now().isoformat(),
            "total": total_users,
            "completed": 0,
            "success": 0,
            "error": 0
        }
        
        # Отправляем сообщения с задержкой, чтобы избежать ограничений Telegram API
        batch_size = 20  # Отправляем по 20 сообщений
        delay = 1.0  # Секунд между batch_size сообщений
        
        try:
            # Проходим по списку пользователей
            for i, user in enumerate(users):
                # Проверяем, не отменена ли рассылка
                if message_id in self.canceled_broadcasts:
                    logger.info(f"Рассылка #{message_id} отменена администратором {admin_id}")
                    break
                
                user_id = user["user_id"]
                
                try:
                    # Пропускаем администраторов (по их желанию)
                    if user_id in ADMIN_IDS and user_id != admin_id:
                        continue
                    
                    # Отправляем сообщение пользователю
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=message_text,
                        parse_mode=parse_mode,
                        disable_notification=False,
                        disable_web_page_preview=True
                    )
                    
                    success_count += 1
                    self.in_progress_broadcasts[message_id]["success"] = success_count
                    
                except Forbidden:
                    # Пользователь заблокировал бота
                    error_count += 1
                    self.in_progress_broadcasts[message_id]["error"] = error_count
                    logger.warning(f"Пользователь {user_id} заблокировал бота")
                    
                except (TelegramError, BadRequest) as e:
                    # Другие ошибки отправки
                    error_count += 1
                    self.in_progress_broadcasts[message_id]["error"] = error_count
                    logger.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
                
                finally:
                    # Обновляем счетчик завершенных
                    self.in_progress_broadcasts[message_id]["completed"] += 1
                    
                    # Каждые batch_size сообщений делаем паузу
                    if (i + 1) % batch_size == 0:
                        # Обновляем статистику в базе данных
                        update_admin_message_stats(message_id, success_count)
                        # Делаем паузу
                        await asyncio.sleep(delay)
            
            # Обновляем финальную статистику в базе данных
            update_admin_message_stats(message_id, success_count)
            
            # Удаляем рассылку из списка активных
            if message_id in self.in_progress_broadcasts:
                del self.in_progress_broadcasts[message_id]
            
            if message_id in self.canceled_broadcasts:
                self.canceled_broadcasts.remove(message_id)
                
            return total_users, success_count, error_count
            
        except Exception as e:
            logger.error(f"Ошибка массовой рассылки: {e}")
            
            # Удаляем рассылку из списка активных
            if message_id in self.in_progress_broadcasts:
                del self.in_progress_broadcasts[message_id]
            
            if message_id in self.canceled_broadcasts:
                self.canceled_broadcasts.remove(message_id)
                
            return total_users, success_count, error_count
    
    def cancel_broadcast(self, message_id: int) -> bool:
        """
        Отменяет текущую рассылку
        
        Args:
            message_id: ID рассылки
            
        Returns:
            True если рассылка была найдена и отменена
        """
        if message_id in self.in_progress_broadcasts:
            self.canceled_broadcasts.add(message_id)
            return True
        return False
    
    def get_broadcast_status(self, message_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает статус текущей рассылки
        
        Args:
            message_id: ID рассылки
            
        Returns:
            Словарь с информацией о рассылке или None, если рассылка не найдена
        """
        return self.in_progress_broadcasts.get(message_id)
    
    def get_active_broadcasts(self) -> List[Dict[str, Any]]:
        """
        Получает список активных рассылок
        
        Returns:
            Список словарей с информацией о рассылках
        """
        return [
            {"message_id": msg_id, **info}
            for msg_id, info in self.in_progress_broadcasts.items()
        ]

# Глобальный экземпляр менеджера сообщений (будет инициализирован при запуске бота)
messaging_manager = None

async def init_messaging_manager(bot: Bot) -> AdminMessagingManager:
    """
    Инициализирует менеджер сообщений
    
    Args:
        bot: Экземпляр бота Telegram
        
    Returns:
        Экземпляр менеджера сообщений
    """
    global messaging_manager
    if messaging_manager is None:
        messaging_manager = AdminMessagingManager(bot)
    return messaging_manager

async def start_message_composition(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начинает процесс составления сообщения для пользователей"""
    # Проверяем, что пользователь администратор
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к этой функции.")
        return
    
    # Устанавливаем состояние ожидания текста сообщения
    context.user_data["awaiting_broadcast_text"] = True
    
    # Отправляем инструкцию
    await update.message.reply_text(
        "📣 <b>Сообщение для пользователей</b>\n\n"
        "Отправьте текст сообщения, которое будет разослано всем пользователям бота.\n\n"
        "Вы можете использовать разметку HTML. Например:\n"
        "<code>&lt;b&gt;жирный текст&lt;/b&gt;</code>\n"
        "<code>&lt;i&gt;курсив&lt;/i&gt;</code>\n"
        "<code>&lt;u&gt;подчеркнутый&lt;/u&gt;</code>\n"
        "<code>&lt;a href='...'&gt;ссылка&lt;/a&gt;</code>\n\n"
        "Для отмены отправьте /cancel",
        parse_mode=ParseMode.HTML
    )

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текст сообщения для рассылки"""
    # Проверяем, что пользователь администратор и ожидается текст сообщения
    if update.effective_user.id not in ADMIN_IDS or not context.user_data.get("awaiting_broadcast_text"):
        return
    
    # Получаем текст сообщения
    message_text = update.message.text.strip()
    
    # Убираем состояние ожидания
    del context.user_data["awaiting_broadcast_text"]
    
    # Отправляем предпросмотр и просим подтверждение
    preview_message = await update.message.reply_text(
        f"<b>Предпросмотр сообщения:</b>\n\n{message_text}",
        parse_mode=ParseMode.HTML
    )
    
    # Добавляем кнопки подтверждения/отмены
    keyboard = [
        [
            InlineKeyboardButton("✅ Отправить всем", callback_data=f"broadcast_confirm"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"broadcast_cancel")
        ]
    ]
    
    confirmation_message = await update.message.reply_text(
        f"Вы уверены, что хотите отправить это сообщение <b>всем пользователям</b> бота?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    
    # Сохраняем текст и ID сообщений в данных пользователя
    context.user_data["broadcast_text"] = message_text
    context.user_data["preview_message_id"] = preview_message.message_id
    context.user_data["confirmation_message_id"] = confirmation_message.message_id

async def handle_broadcast_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатие кнопок подтверждения/отмены рассылки"""
    query = update.callback_query
    await query.answer()
    
    admin_id = update.effective_user.id
    
    # Получаем действие из callback_data
    action = query.data
    
    if action == "broadcast_cancel":
        # Отмена рассылки
        await query.message.edit_text(
            "❌ Рассылка отменена.",
            reply_markup=None
        )
        
        # Очищаем данные
        if "broadcast_text" in context.user_data:
            del context.user_data["broadcast_text"]
        if "preview_message_id" in context.user_data:
            del context.user_data["preview_message_id"]
        if "confirmation_message_id" in context.user_data:
            del context.user_data["confirmation_message_id"]
            
    elif action == "broadcast_confirm":
        # Подтверждение рассылки
        message_text = context.user_data.get("broadcast_text", "")
        
        if not message_text:
            await query.message.edit_text(
                "❌ Ошибка: текст сообщения не найден.",
                reply_markup=None
            )
            return
        
        # Обновляем сообщение
        await query.message.edit_text(
            "⏳ Начинается рассылка сообщения всем пользователям...\n"
            "Это может занять некоторое время.",
            reply_markup=None
        )
        
        # Получаем экземпляр менеджера сообщений
        if not messaging_manager:
            await init_messaging_manager(context.bot)
        
        # Запускаем рассылку
        total, success, error = await messaging_manager.broadcast_message(
            admin_id, 
            message_text, 
            parse_mode=ParseMode.HTML
        )
        
        # Обновляем сообщение с результатами
        await query.message.edit_text(
            f"✅ <b>Рассылка завершена!</b>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"• Всего пользователей: {total}\n"
            f"• Успешно отправлено: {success}\n"
            f"• Ошибок доставки: {error}\n\n"
            f"<i>Некоторые пользователи могли заблокировать бота или удалить чат.</i>",
            parse_mode=ParseMode.HTML
        )
        
        # Очищаем данные
        if "broadcast_text" in context.user_data:
            del context.user_data["broadcast_text"]
        if "preview_message_id" in context.user_data:
            del context.user_data["preview_message_id"]
        if "confirmation_message_id" in context.user_data:
            del context.user_data["confirmation_message_id"]

async def check_user_exists(update: Update) -> None:
    """
    Проверяет наличие пользователя в базе данных и добавляет его, если нужно
    
    Args:
        update: Объект обновления Telegram
    """
    user = update.effective_user
    if user:
        add_user_if_not_exists(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
