import os
import sys
import logging
import inspect

# Настройка логирования для вывода в консоль
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("diagnostic")

def check_structure():
    """Проверяет структуру проекта и доступность файлов"""
    logger.info("=== ДИАГНОСТИКА СТРУКТУРЫ ПРОЕКТА ===")
    
    # Текущая директория и путь Python
    logger.info(f"Текущая директория: {os.getcwd()}")
    logger.info(f"sys.path: {sys.path}")
    
    # Проверка наличия директорий
    paths_to_check = [
        '/home/codespace/hetzner',
        '/home/codespace/hetzner/root',
        '/root'
    ]
    
    for path in paths_to_check:
        exists = os.path.exists(path)
        logger.info(f"Директория {path}: {'Существует' if exists else 'Не существует'}")
        
        if exists:
            logger.info(f"  Содержимое {path}:")
            try:
                files = os.listdir(path)
                for f in files[:10]:  # Показываем только первые 10 файлов
                    full_path = os.path.join(path, f)
                    type_str = "директория" if os.path.isdir(full_path) else "файл"
                    logger.info(f"    - {f} ({type_str})")
                if len(files) > 10:
                    logger.info(f"    ... и еще {len(files) - 10} файлов")
            except PermissionError:
                logger.info(f"  Нет прав для чтения директории {path}")

def check_imports():
    """Проверяет возможность импорта критических модулей"""
    logger.info("\n=== ДИАГНОСТИКА ИМПОРТОВ ===")
    
    modules_to_check = [
        'callback_router',
        'admin_handlers',
        'error_handlers',
        'admin_integration'
    ]
    
    for module_name in modules_to_check:
        try:
            module = __import__(module_name)
            logger.info(f"Модуль {module_name} успешно импортирован")
            
            # Проверяем ключевые компоненты модуля
            if module_name == 'callback_router':
                if hasattr(module, 'CallbackRouter'):
                    logger.info(f"  CallbackRouter найден в {module_name}")
                else:
                    logger.info(f"  CallbackRouter НЕ найден в {module_name}")
            
            elif module_name == 'admin_handlers':
                if hasattr(module, 'admin_handlers'):
                    logger.info(f"  admin_handlers найден в {module_name}")
                    handlers = getattr(module, 'admin_handlers')
                    logger.info(f"  Количество обработчиков: {len(handlers)}")
                    logger.info(f"  Ключи: {list(handlers.keys())[:5]}...")
                else:
                    logger.info(f"  admin_handlers НЕ найден в {module_name}")
        
        except ImportError as e:
            logger.error(f"Не удалось импортировать {module_name}: {e}")
        except Exception as e:
            logger.error(f"Ошибка при проверке {module_name}: {e}")

def check_callback_router():
    """Проверяет работу CallbackRouter с тестовыми данными"""
    logger.info("\n=== ТЕСТИРОВАНИЕ CALLBACK_ROUTER ===")
    
    try:
        from callback_router import CallbackRouter
        
        # Создаем тестовый роутер
        router = CallbackRouter()
        
        # Тестовые обработчики
        async def test_handler(update, context):
            return "Test handler executed"
        
        # Регистрируем тестовые обработчики
        test_handlers = {
            "test_callback": test_handler,
            "test_prefix:action": test_handler
        }
        
        router.register_handlers(test_handlers)
        
        # Проверяем зарегистрированные обработчики
        logger.info(f"Зарегистрировано обработчиков: {len(router.handlers)}")
        logger.info(f"Ключи обработчиков: {list(router.handlers.keys())}")
        
        # Проверяем, что обработчики действительно вызываемые объекты
        for key, handler in router.handlers.items():
            logger.info(f"Обработчик {key}: {type(handler).__name__}, вызываемый: {callable(handler)}")
        
    except ImportError as e:
        logger.error(f"Не удалось импортировать CallbackRouter: {e}")
    except Exception as e:
        logger.error(f"Ошибка при тестировании CallbackRouter: {e}")

if __name__ == "__main__":
    check_structure()
    check_imports()
    check_callback_router()
    logger.info("Диагностика завершена")
