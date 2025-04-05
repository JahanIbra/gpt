            chat_id=chat_id,
            text=f"❌ <b>Ошибка обновления индекса PDF</b>\n\n"
                 f"Произошла ошибка: {str(e)}",
            parse_mode=ParseMode.HTML
        )

async def run_diagnostic():
    """Запускает диагностику бота"""
    # Разбор аргументов командной строки
    parser = argparse.ArgumentParser(description="Диагностика бота для выявления проблем")
    parser.add_argument("--root-dir", help="Корневая директория проекта", default=DEFAULT_ROOT_DIR)
    parser.add_argument("--config", help="Путь к файлу конфигурации", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--log", help="Путь к файлу логов", default=DEFAULT_LOG_PATH)
    parser.add_argument("--detailed", action="store_true", help="Подробный вывод диагностики")
    parser.add_argument("--save", help="Сохранить результаты в JSON-файл", default=None)
    parser.add_argument("--check", choices=["all", "system", "config", "database", "model", "indices", "telegram", "logs"],
                      default="all", help="Указать, какие компоненты проверять")
    parser.add_argument("--fix", action="store_true", help="Попытаться автоматически исправить найденные проблемы")
    
    args = parser.parse_args()
    
    # Создаем диагностический инструмент
    diagnostic = BotDiagnostic(
        root_dir=args.root_dir, 
        config_path=args.config, 
        log_path=args.log,
        detailed=args.detailed
    )
    
    try:
        # Запускаем диагностику
        results = await diagnostic.run_full_diagnostic()
        
        # Выводим результаты
        diagnostic.print_results()
        
        # Сохраняем результаты в файл, если указан параметр --save
        if args.save:
            diagnostic.save_results_to_file(args.save)
        
        # Пытаемся исправить проблемы, если указан параметр --fix
        if args.fix and diagnostic.errors:
            print("\n" + "=" * 50)
            print("ИСПРАВЛЕНИЕ ПРОБЛЕМ")
            print("=" * 50)
            
            fixed = await fix_issues(diagnostic.results, args.root_dir)
            
            print(f"\nИсправлено проблем: {fixed}/{len(diagnostic.errors)}")
            
            # Запускаем диагностику повторно, чтобы проверить результаты исправления
            print("\nЗапуск повторной диагностики после исправлений...")
            await diagnostic.run_full_diagnostic()
            diagnostic.print_results()
            
    except KeyboardInterrupt:
        print("\nДиагностика прервана пользователем")
    except Exception as e:
        print(f"Ошибка при выполнении диагностики: {e}")
        traceback.print_exc()

async def fix_issues(results: Dict[str, Any], root_dir: str) -> int:
    """
    Пытается автоматически исправить найденные проблемы
    
    Args:
        results: Результаты диагностики
        root_dir: Корневая директория проекта
        
    Returns:
        Количество исправленных проблем
    """
    fixed_count = 0
    
    # Исправление проблем с базой данных
    database = results.get("database", {})
    if not database.get("exists", False):
        print("⚙️ Создание базы данных...")
        try:
            # Импортируем модуль базы данных
            sys.path.insert(0, root_dir)
            from database import init_database
            
            if init_database():
                print("✅ База данных успешно создана")
                fixed_count += 1
            else:
                print("❌ Не удалось создать базу данных")
        except Exception as e:
            print(f"❌ Ошибка создания базы данных: {e}")
    
    # Исправление проблем с индексами
    indices = results.get("indices", {})
    if not indices.get("faiss", {}).get("valid", False):
        print("⚙️ Создание FAISS индекса...")
        try:
            # Импортируем модуль векторного поиска
            from vector_search import create_faiss_index
            
            if await create_faiss_index():
                print("✅ FAISS индекс успешно создан")
                fixed_count += 1
            else:
                print("❌ Не удалось создать FAISS индекс")
        except Exception as e:
            print(f"❌ Ошибка создания FAISS индекса: {e}")
    
    # Исправление проблем с PDF индексами
    if not indices.get("pdf_index", {}).get("valid", False) and indices.get("pdf", {}).get("count", 0) > 0:
        print("⚙️ Обновление индексов PDF...")
        try:
            # Импортируем модуль PDF обработчика
            from pdf_handler import update_all_pdf_index
            
            if await update_all_pdf_index():
                print("✅ Индексы PDF успешно обновлены")
                fixed_count += 1
            else:
                print("❌ Не удалось обновить индексы PDF")
        except Exception as e:
            print(f"❌ Ошибка обновления индексов PDF: {e}")
    
    # Создание необходимых директорий
    required_dirs = [
        os.path.join(root_dir, "logs"),
        os.path.join(root_dir, "faiss_index"),
        os.path.join(root_dir, "pdf_docs"),
        os.path.join(root_dir, "pdf_index")
    ]
    
    for directory in required_dirs:
        if not os.path.exists(directory):
            print(f"⚙️ Создание директории {directory}...")
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"✅ Директория {directory} успешно создана")
                fixed_count += 1
            except Exception as e:
                print(f"❌ Ошибка создания директории {directory}: {e}")
    
    return fixed_count

def main():
    """Точка входа скрипта"""
    asyncio.run(run_diagnostic())

if __name__ == "__main__":
    main()
