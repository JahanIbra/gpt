import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext

logger = logging.getLogger("bot")

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Тестовая команда для проверки работоспособности кнопок"""
    keyboard = [
        [InlineKeyboardButton("Тестовая команда", callback_data="test_admin")],
        [InlineKeyboardButton("Обновление индекса", callback_data="update_index:all")],
        [InlineKeyboardButton("Резервное копирование", callback_data="backup:create")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Нажмите кнопку для проверки обработчиков:",
        reply_markup=reply_markup
    )

# Функция для регистрации в основном файле
def register_test_command(application):
    from telegram.ext import CommandHandler
    application.add_handler(CommandHandler("test", test_command))
    logger.info("Зарегистрирована тестовая команда /test")
