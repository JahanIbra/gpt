from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext

async def show_admin_menu(update: Update, context: CallbackContext) -> None:
    """Показывает расширенное админ-меню с дополнительными опциями"""
    query = update.callback_query if update.callback_query else None
    
    # Формируем клавиатуру с полным набором команд
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📂 База данных", callback_data="admin_db")],
        [InlineKeyboardButton("🔄 Обновить индексы", callback_data="update_menu")],
        [InlineKeyboardButton("💾 Резервные копии", callback_data="backup_menu")],
        [InlineKeyboardButton("📣 Сообщение пользователям", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⬅️ Вернуться", callback_data="back_to_start")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = "👨‍💻 <b>Меню администратора</b>\n\n" \
                   "Выберите раздел для управления:"
    
    if query:
        await query.edit_message_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

async def show_update_menu(update: Update, context: CallbackContext) -> None:
    """Показывает меню обновления индексов"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить все индексы", callback_data="update_index:all")],
        [InlineKeyboardButton("📚 Обновить индекс базы знаний", callback_data="update_index:knowledge")],
        [InlineKeyboardButton("📄 Обновить индекс PDF", callback_data="update_index:pdf")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="🔄 <b>Обновление индексов</b>\n\n"
             "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def show_backup_menu(update: Update, context: CallbackContext) -> None:
    """Показывает меню управления резервными копиями"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📦 Создать новую копию", callback_data="backup:create")],
        [InlineKeyboardButton("📋 Список копий", callback_data="backup:list")],
        [InlineKeyboardButton("📥 Восстановить из копии", callback_data="backup:restore_list")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="💾 <b>Управление резервными копиями</b>\n\n"
             "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# Дополнительные обработчики для внедрения в общий список
additional_menu_handlers = {
    "admin_panel": show_admin_menu,
    "update_menu": show_update_menu,
    "backup_menu": show_backup_menu
}
