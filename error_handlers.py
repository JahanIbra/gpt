import logging
import traceback
from telegram import Update
from telegram.ext import ContextTypes, Application

logger = logging.getLogger("bot")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает все ошибки в работе бота."""
    logger.error(f"При обработке возникло исключение:", exc_info=context.error)
    
    # Извлекаем трассировку стека
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    
    # Сокращаем сообщение, если оно слишком длинное
    error_message = str(context.error)[:100] + "..." if len(str(context.error)) > 100 else str(context.error)
    
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    
    # Журналируем подробности ошибки
    logger.error(
        f"update = {update_str}\n"
        f"error = {error_message}\n"
        f"traceback = {tb_string}"
    )
    
    # Отправляем уведомление пользователю, если это не системная ошибка
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка при обработке запроса. Администраторы уведомлены."
        )

def setup_error_handlers(application: Application) -> None:
    """Настраивает обработчики ошибок для приложения."""
    application.add_error_handler(error_handler)
    logger.info("Обработчики ошибок настроены")
