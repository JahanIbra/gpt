import logging
import sys
from bot_setup import setup_bot

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout
)

logger = logging.getLogger("bot")

def test_bot():
    """Тестирует настройку бота"""
    # Используем тестовый токен
    token = "TEST_TOKEN"
    
    try:
        # Настраиваем бота
        application = setup_bot(token)
        logger.info("Бот успешно настроен для тестирования")
        
        # В реальном сценарии здесь бы запускался polling или webhook
        # application.run_polling()
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при настройке бота: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_bot()
    logger.info(f"Тест настройки бота {'успешен' if success else 'не пройден'}")
