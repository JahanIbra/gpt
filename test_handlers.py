import asyncio
import logging
from telegram import Update, CallbackQuery, Message, User, Chat
from telegram.ext import CallbackContext

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test")

async def test_direct_handler():
    """Непосредственно тестирует обработчик admin_panel"""
    logger.info("=== ТЕСТ ПРЯМОГО ВЫЗОВА ОБРАБОТЧИКА ===")
    
    try:
        # Импортируем обработчик
        from admin_handlers import admin_panel
        
        # Создаем мок-объекты
        user = User(id=12345, is_bot=False, first_name="Test", username="test_user")
        chat = Chat(id=12345, type="private")
        message = Message(message_id=1, date=None, chat=chat, from_user=user)
        update = Update(update_id=1, message=message)
        context = CallbackContext.from_update(None, update, None, None, None)
        
        # Вызываем обработчик напрямую
        logger.info("Вызов admin_panel...")
        await admin_panel(update, context)
        logger.info("admin_panel успешно выполнен!")
        
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при тестировании: {e}")
        return False

async def test_handlers_dict():
    """Тестирует словарь admin_handlers"""
    logger.info("=== ТЕСТ СЛОВАРЯ ОБРАБОТЧИКОВ ===")
    
    try:
        # Импортируем словарь обработчиков
        from admin_handlers import admin_handlers
        
        # Проверяем содержимое
        logger.info(f"Количество обработчиков: {len(admin_handlers)}")
        logger.info(f"Ключи: {list(admin_handlers.keys())[:5]}...")
        
        # Проверяем, что все элементы вызываемые
        all_callable = all(callable(handler) for handler in admin_handlers.values())
        logger.info(f"Все обработчики вызываемые: {all_callable}")
        
        # Выводим типы нескольких обработчиков
        sample_keys = list(admin_handlers.keys())[:3]
        for key in sample_keys:
            handler = admin_handlers[key]
            logger.info(f"Обработчик {key}: {type(handler).__name__}")
        
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при тестировании словаря: {e}")
        return False

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    
    # Запускаем тесты
    direct_test = loop.run_until_complete(test_direct_handler())
    dict_test = loop.run_until_complete(test_handlers_dict())
    
    logger.info(f"Результаты тестов:")
    logger.info(f"- Прямой вызов обработчика: {'Успех' if direct_test else 'Ошибка'}")
    logger.info(f"- Проверка словаря обработчиков: {'Успех' if dict_test else 'Ошибка'}")
