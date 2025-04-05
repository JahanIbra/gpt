import sys
import logging
from typing import Dict, Any, Callable

# Импортируем обработчики меню
from admin_menu import additional_menu_handlers

# Настройка логгера
logger = logging.getLogger("bot")

class AdminIntegration:
    """
    Класс для интеграции существующего админ-функционала с системой маршрутизации
    обратных вызовов Telegram бота.
    """
    
    def __init__(self):
        """Инициализация интеграции"""
        self.admin_handlers = {}
        self.admin_modules_loaded = False
    
    def load_admin_modules(self):
        """Загружает модули администрирования из директории проекта"""
        if self.admin_modules_loaded:
            return True
            
        try:
            # Добавляем пути к модулям
            sys.path.append('/home/codespace/hetzner/root')
            
            # Импортируем модули
            from admin_utils import (
                admin_base_menu,
                handle_admin_db_callback,
                handle_knowledge_menu,
                handle_cache_menu,
                handle_pdf_menu,
                handle_unanswered_menu,
                handle_export_db,
                handle_import_db,
                handle_clear_cache
            )
            
            from admin_messaging import (
                start_message_composition,
                handle_broadcast_button
            )
            
            # Регистрируем обработчики
            handlers = {
                "admin_db": admin_base_menu,
                "admin_db:knowledge": handle_knowledge_menu,
                "admin_db:cache": handle_cache_menu,
                "admin_db:pdf": handle_pdf_menu,
                "admin_db:unanswered": handle_unanswered_menu,
                "admin_db:export": handle_export_db,
                "admin_db:import": handle_import_db,
                "admin_db:clear_cache": handle_clear_cache,
                "admin_broadcast": start_message_composition,
                "broadcast_confirm": handle_broadcast_button,
                "broadcast_cancel": handle_broadcast_button
            }
            
            # Регистрируем дополнительные обработчики из admin_menu
            handlers.update(additional_menu_handlers)
            
            # Регистрируем обработчик для динамических команд
            # Эта функция будет обрабатывать все команды с префиксами
            handlers["admin_db:"] = handle_admin_db_callback
            
            # Обновляем словарь обработчиков
            self.admin_handlers.update(handlers)
            self.admin_modules_loaded = True
            
            logger.info("Модули администрирования успешно загружены")
            return True
            
        except ImportError as e:
            logger.error(f"Ошибка импорта модулей администрирования: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка загрузки модулей администрирования: {e}")
            return False
    
    def get_handlers(self) -> Dict[str, Callable]:
        """
        Возвращает словарь обработчиков для интеграции
        
        Returns:
            Словарь обработчиков callback-запросов
        """
        if not self.admin_modules_loaded:
            self.load_admin_modules()
        
        return self.admin_handlers

# Создаем глобальный экземпляр
admin_integration = AdminIntegration()
