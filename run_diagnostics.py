#!/usr/bin/env python3
"""
Скрипт для запуска диагностики бота
"""

import os
import sys
import asyncio
from bot_diagnostic import run_diagnostic

def main():
    """Основная функция"""
    try:
        asyncio.run(run_diagnostic())
    except KeyboardInterrupt:
        print("Диагностика прервана пользователем")
    except Exception as e:
        print(f"Ошибка при запуске диагностики: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Делаем скрипт исполняемым
    if os.name != 'nt':  # Не для Windows
        os.chmod(__file__, 0o755)
    
    main()
