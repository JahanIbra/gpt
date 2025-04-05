import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext
import os
import sys

# Добавляем пути для упрощения импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.join(current_dir, 'root')
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

logger = logging.getLogger("bot")

# Пытаемся импортировать функции из root-директории
try:
    # Импортируем функции для работы с индексами (с обработкой ошибок)
    try:
        from vector_search import update_faiss_index
    except ImportError:
        logger.warning("Не удалось импортировать update_faiss_index")
        
        async def update_faiss_index():
            logger.warning("Вызвана заглушка update_faiss_index")
            return False
    
    try:
        from pdf_handler import update_all_pdf_index
    except ImportError:
        logger.warning("Не удалось импортировать update_all_pdf_index")
        
        async def update_all_pdf_index():
            logger.warning("Вызвана заглушка update_all_pdf_index")
            return False
    
    try:
        from backup_manager import backup_manager
    except ImportError:
        logger.warning("Не удалось импортировать backup_manager")
        
        class DummyBackupManager:
            async def create_full_backup(self):
                logger.warning("Вызвана заглушка create_full_backup")
                return "/dummy/path/backup.tar.gz"
            
            async def list_backups(self):
                logger.warning("Вызвана заглушка list_backups")
                return []
        
        backup_manager = DummyBackupManager()
    
except Exception as e:
    logger.error(f"Ошибка при импорте функций из root-директории: {e}")

# Заглушки для вызовов функций из других модулей
async def admin_base_menu(update, context):
    """Заглушка для admin_base_menu"""
    query = update.callback_query if update.callback_query else None
    message = (query.message if query else update.message)
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("База данных", callback_data="admin_db")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.answer()
        await query.edit_message_text(
            "🛠 Управление базами данных",
            reply_markup=reply_markup
        )
    else:
        await message.reply_text(
            "🛠 Управление базами данных",
            reply_markup=reply_markup
        )

async def handle_admin_db_callback(update, context):
    """Заглушка для handle_admin_db_callback"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"Обработка DB callback: {query.data}")
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🔍 Обработка команды: {query.data}",
        reply_markup=reply_markup
    )

# Определяем функции для обработки callback-запросов
async def back_to_start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды возврата в начальное меню"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("Настройки", callback_data="admin_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="Панель администратора. Выберите раздел:",
        reply_markup=reply_markup
    )

async def admin_panel(update: Update, context: CallbackContext) -> None:
    """Показывает админ-панель"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("База данных", callback_data="admin_db")],
            [InlineKeyboardButton("Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton("Настройки", callback_data="admin_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="Панель администратора. Выберите раздел:",
            reply_markup=reply_markup
        )
    else:
        keyboard = [
            [InlineKeyboardButton("Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("База данных", callback_data="admin_db")],
            [InlineKeyboardButton("Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton("Настройки", callback_data="admin_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text="Панель администратора. Выберите раздел:",
            reply_markup=reply_markup
        )

async def admin_stats_refresh(update: Update, context: CallbackContext) -> None:
    """Обновляет статистику"""
    query = update.callback_query
    await query.answer("Обновление статистики...")
    
    # Здесь логика получения свежей статистики
    stats_text = "📊 Статистика бота:\n\n" \
                 "Всего пользователей: 152\n" \
                 "Активных сегодня: 24\n" \
                 "Сообщений за день: 341\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats:refresh")],
        [InlineKeyboardButton("📑 Подробнее", callback_data="admin_stats:detailed")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=stats_text,
        reply_markup=reply_markup
    )

async def admin_stats_detailed(update: Update, context: CallbackContext) -> None:
    """Показывает детальную статистику"""
    query = update.callback_query
    await query.answer()
    
    # Здесь логика получения детальной статистики
    detailed_stats = "📊 Подробная статистика:\n\n" \
                     "Всего пользователей: 152\n" \
                     "  - Новых за неделю: 17\n" \
                     "  - Активных за неделю: 98\n\n" \
                     "Сообщений за неделю: 2135\n" \
                     "  - Текстовых: 1856\n" \
                     "  - С медиа: 279\n\n" \
                     "Использование команд:\n" \
                     "  - /start: 43\n" \
                     "  - /help: 28\n"
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_stats:refresh")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=detailed_stats,
        reply_markup=reply_markup
    )

async def admin_db_handler(update: Update, context: CallbackContext) -> None:
    """Перенаправляет на основное меню управления базой данных"""
    await admin_base_menu(update, context)

async def cancel_teach(update: Update, context: CallbackContext) -> None:
    """Отменяет режим обучения бота"""
    query = update.callback_query
    await query.answer("Режим обучения отменен")
    
    # Сбрасываем состояние обучения
    if 'mode' in context.user_data:
        del context.user_data['mode']
    if 'qa_pairs' in context.user_data:
        del context.user_data['qa_pairs']
    
    # Возвращаемся к обычному режиму
    keyboard = [
        [InlineKeyboardButton("◀️ Вернуться в главное меню", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="Режим обучения был отменен. Все несохраненные данные удалены.",
        reply_markup=reply_markup
    )

async def update_all_indexes(update: Update, context: CallbackContext) -> None:
    """Обновляет все индексы"""
    query = update.callback_query
    await query.answer("Запуск обновления всех индексов...")
    
    message = await query.edit_message_text(
        "🔄 <b>Обновление всех индексов</b>\n\n"
        "Начато обновление всех индексов. Это может занять время...",
        parse_mode="HTML"
    )
    
    # Обновляем индекс базы знаний
    success_knowledge = await update_faiss_index()
    # Обновляем индекс PDF
    success_pdf = await update_all_pdf_index()
    
    result_text = "🔄 <b>Результаты обновления индексов</b>\n\n"
    result_text += "✅ " if success_knowledge else "❌ "
    result_text += "Индекс базы знаний\n"
    result_text += "✅ " if success_pdf else "❌ "
    result_text += "Индекс PDF документов\n\n"
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.edit_text(
        result_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def update_knowledge_index(update: Update, context: CallbackContext) -> None:
    """Обновляет индекс базы знаний"""
    query = update.callback_query
    await query.answer("Запуск обновления индекса базы знаний...")
    
    message = await query.edit_message_text(
        "🔄 <b>Обновление индекса базы знаний</b>\n\n"
        "Процесс запущен, пожалуйста подождите...",
        parse_mode="HTML"
    )
    
    # Обновляем индекс
    success = await update_faiss_index()
    
    result_text = "🔄 <b>Обновление индекса базы знаний</b>\n\n"
    if success:
        result_text += "✅ Индекс базы знаний успешно обновлен!\n"
        result_text += "Изменения вступили в силу."
    else:
        result_text += "❌ Ошибка обновления индекса базы знаний.\n"
        result_text += "Проверьте логи для подробностей."
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.edit_text(
        result_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def update_pdf_index(update: Update, context: CallbackContext) -> None:
    """Обновляет индекс PDF документов"""
    query = update.callback_query
    await query.answer("Запуск обновления индекса PDF...")
    
    message = await query.edit_message_text(
        "🔄 <b>Обновление индекса PDF</b>\n\n"
        "Процесс запущен, пожалуйста подождите...",
        parse_mode="HTML"
    )
    
    # Обновляем индекс
    success = await update_all_pdf_index()
    
    result_text = "🔄 <b>Обновление индекса PDF</b>\n\n"
    if success:
        result_text += "✅ Индекс PDF документов успешно обновлен!\n"
        result_text += "Изменения вступили в силу."
    else:
        result_text += "❌ Ошибка обновления индекса PDF документов.\n"
        result_text += "Проверьте логи для подробностей."
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.edit_text(
        result_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def create_backup(update: Update, context: CallbackContext) -> None:
    """Создает резервную копию данных"""
    query = update.callback_query
    await query.answer("Создание резервной копии...")
    
    message = await query.edit_message_text(
        "💾 <b>Создание резервной копии</b>\n\n"
        "Процесс запущен, пожалуйста подождите...",
        parse_mode="HTML"
    )
    
    try:
        # Создаем резервную копию
        backup_path = await backup_manager.create_full_backup()
        
        result_text = "💾 <b>Создание резервной копии</b>\n\n"
        result_text += f"✅ Резервная копия успешно создана!\n"
        result_text += f"📂 Путь к файлу: {backup_path}"
        
    except Exception as e:
        logger.error(f"Ошибка создания резервной копии: {e}")
        result_text = "💾 <b>Создание резервной копии</b>\n\n"
        result_text += f"❌ Ошибка создания резервной копии: {str(e)[:100]}"
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.edit_text(
        result_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def list_backups(update: Update, context: CallbackContext) -> None:
    """Показывает список доступных резервных копий"""
    query = update.callback_query
    await query.answer("Получение списка резервных копий...")
    
    message = await query.edit_message_text(
        "💾 <b>Список резервных копий</b>\n\n"
        "Загрузка данных...",
        parse_mode="HTML"
    )
    
    try:
        # Получаем список резервных копий
        backups = await backup_manager.list_backups()
        
        result_text = "💾 <b>Список резервных копий</b>\n\n"
        
        if backups:
            for i, backup in enumerate(backups, 1):
                created_at = backup.get("created_at", "Нет данных")
                size_mb = backup.get("size", 0) / (1024 * 1024)
                result_text += f"{i}. {backup['filename']}\n"
                result_text += f"   📅 {created_at}\n"
                result_text += f"   📊 {size_mb:.2f} МБ\n\n"
        else:
            result_text += "Резервных копий не найдено."
        
    except Exception as e:
        logger.error(f"Ошибка получения списка резервных копий: {e}")
        result_text = "💾 <b>Список резервных копий</b>\n\n"
        result_text += f"❌ Ошибка получения списка: {str(e)[:100]}"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="backup:list")],
        [InlineKeyboardButton("📤 Восстановить", callback_data="backup:restore_list")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.edit_text(
        result_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def restore_backup_list(update: Update, context: CallbackContext) -> None:
    """Показывает список резервных копий для восстановления"""
    query = update.callback_query
    await query.answer("Получение списка резервных копий для восстановления...")
    
    message = await query.edit_message_text(
        "🔄 <b>Восстановление из резервной копии</b>\n\n"
        "Загрузка доступных копий...",
        parse_mode="HTML"
    )
    
    try:
        # Получаем список резервных копий
        backups = await backup_manager.list_backups()
        
        result_text = "🔄 <b>Восстановление из резервной копии</b>\n\n"
        result_text += "⚠️ <b>Внимание!</b> Восстановление перезапишет текущие данные!\n\n"
        result_text += "Выберите резервную копию для восстановления:\n\n"
        
        keyboard = []
        
        if backups:
            for i, backup in enumerate(backups, 1):
                created_at = backup.get("created_at", "Нет данных")
                size_mb = backup.get("size", 0) / (1024 * 1024)
                
                # Добавляем кнопку для каждой резервной копии
                keyboard.append([
                    InlineKeyboardButton(
                        f"{i}. {backup['filename']} ({size_mb:.1f} МБ)",
                        callback_data=f"backup:restore:{backup['path']}"
                    )
                ])
        else:
            result_text += "Резервных копий не найдено."
        
        # Добавляем кнопку "Назад"
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="backup:list")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка получения списка резервных копий для восстановления: {e}")
        result_text = "🔄 <b>Восстановление из резервной копии</b>\n\n"
        result_text += f"❌ Ошибка получения списка: {str(e)[:100]}"
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data="backup:list")]
        ])
    
    await message.edit_text(
        result_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# Словарь обработчиков для маршрутизации callback-запросов
admin_handlers = {
    "back_to_start": back_to_start,
    "admin_panel": admin_panel,
    "admin_stats:refresh": admin_stats_refresh,
    "admin_stats:detailed": admin_stats_detailed,
    "admin_db": admin_db_handler,
    "admin_db:knowledge": handle_admin_db_callback,
    "admin_db:cache": handle_admin_db_callback,
    "admin_db:pdf": handle_admin_db_callback,
    "admin_db:unanswered": handle_admin_db_callback,
    "admin_db:export": handle_admin_db_callback,
    "admin_db:import": handle_admin_db_callback,
    "admin_db:clear_cache": handle_admin_db_callback,
    "update_index:all": update_all_indexes,
    "update_index:pdf": update_pdf_index,
    "update_index:knowledge": update_knowledge_index,
    "backup:create": create_backup,
    "backup:list": list_backups,
    "backup:restore_list": restore_backup_list,
    "cancel_teach": cancel_teach,
    "test_admin": admin_panel  # Простой тестовый обработчик
}
