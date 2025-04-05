import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger("bot")

class CallbackRouter:
    """Маршрутизатор callback-запросов от инлайн-кнопок"""
    
    def __init__(self):
        self.handlers = {}
    
    def register_handlers(self, handlers_dict):
        """Регистрирует обработчики callback-запросов"""
        # Добавляем логирование для лучшей диагностики
        logger.info(f"Регистрация {len(handlers_dict)} обработчиков: {', '.join(list(handlers_dict.keys())[:5])}...")
        self.handlers.update(handlers_dict)
    
    async def route_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Маршрутизирует callback-запросы к соответствующим обработчикам"""
        query = update.callback_query
        callback_data = query.data
        
        logger.info(f"Получен callback: {callback_data}")
        logger.info(f"Доступные обработчики: {len(self.handlers)}")
        
        # 1. Проверяем точное совпадение
        if callback_data in self.handlers:
            logger.info(f"Найден точный обработчик для {callback_data}")
            handler = self.handlers[callback_data]
            if callable(handler):
                await handler(update, context)
                return
            else:
                logger.error(f"Обработчик для {callback_data} не вызываемый: {type(handler)}")
                await query.answer("Внутренняя ошибка: неверный тип обработчика")
                return
        
        # 2. Проверяем динамические обработчики с префиксами
        handled = False
        for prefix, handler in self.handlers.items():
            # Проверка на префикс
            if ":" in prefix and callback_data.startswith(prefix.split(":")[0] + ":"):
                logger.info(f"Найден префиксный обработчик: {prefix} для {callback_data}")
                if callable(handler):
                    await handler(update, context)
                    handled = True
                    break
                else:
                    logger.error(f"Обработчик для префикса {prefix} не вызываемый: {type(handler)}")
                    await query.answer("Внутренняя ошибка: неверный тип обработчика")
                    handled = True
                    break
        
        # 3. Если ничего не найдено, проверяем точный префикс (для backup:restore:filename)
        if not handled:
            for prefix, handler in self.handlers.items():
                if prefix.endswith(":") and callback_data.startswith(prefix):
                    logger.info(f"Найден точный префиксный обработчик: {prefix} для {callback_data}")
                    if callable(handler):
                        await handler(update, context)
                        handled = True
                        break
                    else:
                        logger.error(f"Обработчик для префикса {prefix} не вызываемый: {type(handler)}")
                        await query.answer("Внутренняя ошибка: неверный тип обработчика")
                        handled = True
                        break
        
        # 4. Если всё ещё не найдено, логируем ошибку
        if not handled:
            available_handlers = ", ".join(list(self.handlers.keys())[:10])
            logger.warning(f"Неизвестная команда: {callback_data}. Доступные обработчики: {available_handlers}...")
            await query.answer(f"Неизвестная команда: {callback_data}")
