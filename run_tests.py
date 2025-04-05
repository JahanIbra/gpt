#!/usr/bin/env python3
"""
Скрипт для запуска тестов проекта
"""
import os
import sys
import pytest
import argparse
from datetime import datetime

def main():
    """Основная функция запуска тестов"""
    parser = argparse.ArgumentParser(description="Запуск тестов проекта")
    parser.add_argument("--unit", action="store_true", help="Запустить только модульные тесты")
    parser.add_argument("--integration", action="store_true", help="Запустить только интеграционные тесты")
    parser.add_argument("--all", action="store_true", help="Запустить все тесты")
    parser.add_argument("--database", action="store_true", help="Запустить тесты базы данных")
    parser.add_argument("--models", action="store_true", help="Запустить тесты моделей")
    parser.add_argument("--pdf", action="store_true", help="Запустить тесты PDF")
    parser.add_argument("--report", action="store_true", help="Создать отчет о тестировании")
    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")
    
    args = parser.parse_args()
    
    pytest_args = []
    
    # Обработка параметров запуска
    if args.unit:
        pytest_args.append("-m unit")
    elif args.integration:
        pytest_args.append("-m integration")
    elif args.database:
        pytest_args.append("-m database")
    elif args.models:
        pytest_args.append("-m models")
    elif args.pdf:
        pytest_args.append("-m pdf")
    # По умолчанию запускаем все тесты
    
    # Добавляем опцию подробного вывода
    if args.verbose:
        pytest_args.append("-v")
    
    # Добавляем опцию создания отчета
    if args.report:
        report_dir = "test_reports"
        os.makedirs(report_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(report_dir, f"report_{timestamp}.html")
        pytest_args.append(f"--html={report_path}")
        pytest_args.append("--self-contained-html")
    
    # Запускаем тесты
    print(f"Запуск тестов с параметрами: {' '.join(pytest_args)}")
    sys.exit(pytest.main(pytest_args))

if __name__ == "__main__":
    main()
