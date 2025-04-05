import os
import json
import csv
import sqlite3
import argparse
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime

from config import DB_PATH, logger
from database import init_database

def csv_to_knowledge(csv_file: str, delimiter: str = ',') -> List[Dict[str, Any]]:
    """
    Конвертирует CSV-файл в формат базы знаний
    
    Args:
        csv_file: Путь к CSV-файлу
        delimiter: Разделитель колонок
        
    Returns:
        Список словарей с данными для базы знаний
    """
    knowledge_data = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            
            for i, row in enumerate(reader, start=1):
                # Проверяем наличие обязательных колонок
                if 'question' not in row or 'answer' not in row:
                    logger.warning(f"Строка {i}: отсутствуют обязательные колонки 'question' или 'answer'")
                    continue
                
                # Формируем элемент базы знаний
                knowledge_item = {
                    "id": i,
                    "question": row["question"].strip(),
                    "answer": row["answer"].strip(),
                    "topic_path": row.get("topic_path", "root").strip(),
                    "is_category": int(row.get("is_category", "0").strip() == "1"),
                    "timestamp": datetime.now().isoformat()
                }
                
                knowledge_data.append(knowledge_item)
        
        logger.info(f"Преобразовано {len(knowledge_data)} записей из CSV")
        return knowledge_data
        
    except Exception as e:
        logger.error(f"Ошибка преобразования CSV в базу знаний: {e}")
        return []

def json_to_knowledge(json_file: str) -> List[Dict[str, Any]]:
    """
    Конвертирует JSON-файл в формат базы знаний
    
    Args:
        json_file: Путь к JSON-файлу
        
    Returns:
        Список словарей с данными для базы знаний
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проверяем формат данных
        if not isinstance(data, list):
            logger.error("Неверный формат JSON: ожидается список")
            return []
        
        # Преобразуем данные в нужный формат
        knowledge_data = []
        for i, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                logger.warning(f"Элемент {i}: не является словарем, пропускаем")
                continue
                
            if "question" not in item or "answer" not in item:
                logger.warning(f"Элемент {i}: отсутствуют обязательные поля 'question' или 'answer'")
                continue
            
            # Формируем элемент базы знаний
            knowledge_item = {
                "id": item.get("id", i),
                "question": item["question"],
                "answer": item["answer"],
                "topic_path": item.get("topic_path", "root"),
                "is_category": item.get("is_category", 0),
                "timestamp": item.get("timestamp", datetime.now().isoformat())
            }
            
            knowledge_data.append(knowledge_item)
        
        logger.info(f"Преобразовано {len(knowledge_data)} записей из JSON")
        return knowledge_data
        
    except Exception as e:
        logger.error(f"Ошибка преобразования JSON в базу знаний: {e}")
        return []

def knowledge_to_csv(knowledge_data: List[Dict[str, Any]], output_file: str, delimiter: str = ',') -> bool:
    """
    Сохраняет данные базы знаний в CSV-файл
    
    Args:
        knowledge_data: Список словарей с данными базы знаний
        output_file: Путь к выходному файлу
        delimiter: Разделитель колонок
        
    Returns:
        True, если сохранение прошло успешно
    """
    try:
        # Определяем поля для CSV
        fieldnames = ["id", "question", "answer", "topic_path", "is_category", "timestamp"]
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
            writer.writeheader()
            
            for item in knowledge_data:
                writer.writerow(item)
        
        logger.info(f"Сохранено {len(knowledge_data)} записей в CSV")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка сохранения базы знаний в CSV: {e}")
        return False

def knowledge_to_json(knowledge_data: List[Dict[str, Any]], output_file: str) -> bool:
    """
    Сохраняет данные базы знаний в JSON-файл
    
    Args:
        knowledge_data: Список словарей с данными базы знаний
        output_file: Путь к выходному файлу
        
    Returns:
        True, если сохранение прошло успешно
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(knowledge_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Сохранено {len(knowledge_data)} записей в JSON")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка сохранения базы знаний в JSON: {e}")
        return False

def load_knowledge_from_db() -> List[Dict[str, Any]]:
    """
    Загружает данные базы знаний из базы данных
    
    Returns:
        Список словарей с данными базы знаний
    """
    try:
        # Проверяем существование базы данных
        if not os.path.exists(DB_PATH):
            logger.error(f"База данных не найдена: {DB_PATH}")
            return []
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Проверяем существование таблицы
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge'")
        if not c.fetchone():
            logger.error("Таблица 'knowledge' не найдена в базе данных")
            conn.close()
            return []
        
        # Загружаем данные
        c.execute("SELECT * FROM knowledge")
        rows = c.fetchall()
        
        # Преобразуем в список словарей
        knowledge_data = []
        for row in rows:
            item = dict(row)
            knowledge_data.append(item)
        
        conn.close()
        
        logger.info(f"Загружено {len(knowledge_data)} записей из базы данных")
        return knowledge_data
        
    except Exception as e:
        logger.error(f"Ошибка загрузки базы знаний из базы данных: {e}")
        return []

def save_knowledge_to_db(knowledge_data: List[Dict[str, Any]]) -> bool:
    """
    Сохраняет данные базы знаний в базу данных
    
    Args:
        knowledge_data: Список словарей с данными базы знаний
        
    Returns:
        True, если сохранение прошло успешно
    """
    try:
        # Инициализируем базу данных, если она не существует
        if not os.path.exists(os.path.dirname(DB_PATH)):
            os.makedirs(os.path.dirname(DB_PATH))
        
        init_database()
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Очищаем таблицу
        c.execute("DELETE FROM knowledge")
        
        # Вставляем новые данные
        for item in knowledge_data:
            c.execute("""
            INSERT INTO knowledge (id, question, answer, topic_path, timestamp, is_category)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                item.get("id"),
                item.get("question"),
                item.get("answer"),
                item.get("topic_path", "root"),
                item.get("timestamp", datetime.now().isoformat()),
                item.get("is_category", 0)
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Сохранено {len(knowledge_data)} записей в базу данных")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка сохранения базы знаний в базу данных: {e}")
        return False

def excel_to_knowledge(excel_file: str, sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Конвертирует Excel-файл в формат базы знаний
    
    Args:
        excel_file: Путь к Excel-файлу
        sheet_name: Имя листа (опционально)
        
    Returns:
        Список словарей с данными для базы знаний
    """
    try:
        # Загружаем Excel-файл
        if sheet_name:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
        else:
            df = pd.read_excel(excel_file)
        
        # Проверяем наличие обязательных колонок
        if 'question' not in df.columns or 'answer' not in df.columns:
            logger.error("В Excel-файле отсутствуют обязательные колонки 'question' или 'answer'")
            return []
        
        # Преобразуем в список словарей
        knowledge_data = []
        for i, row in df.iterrows():
            # Преобразуем строку DataFrame в словарь
            item = row.to_dict()
            
            # Добавляем идентификатор, если его нет
            if 'id' not in item:
                item['id'] = i + 1
                
            # Преобразуем NaN в None
            for key, value in item.items():
                if pd.isna(value):
                    item[key] = None
            
            # Устанавливаем значения по умолчанию для необязательных полей
            if 'topic_path' not in item or item['topic_path'] is None:
                item['topic_path'] = 'root'
                
            if 'is_category' not in item or item['is_category'] is None:
                item['is_category'] = 0
                
            if 'timestamp' not in item or item['timestamp'] is None:
                item['timestamp'] = datetime.now().isoformat()
            
            knowledge_data.append(item)
        
        logger.info(f"Преобразовано {len(knowledge_data)} записей из Excel")
        return knowledge_data
        
    except Exception as e:
        logger.error(f"Ошибка преобразования Excel в базу знаний: {e}")
        return []

def knowledge_to_excel(knowledge_data: List[Dict[str, Any]], output_file: str) -> bool:
    """
    Сохраняет данные базы знаний в Excel-файл
    
    Args:
        knowledge_data: Список словарей с данными базы знаний
        output_file: Путь к выходному файлу
        
    Returns:
        True, если сохранение прошло успешно
    """
    try:
        # Создаем DataFrame из списка словарей
        df = pd.DataFrame(knowledge_data)
        
        # Сохраняем в Excel
        df.to_excel(output_file, index=False)
        
        logger.info(f"Сохранено {len(knowledge_data)} записей в Excel")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка сохранения базы знаний в Excel: {e}")
        return False

def main():
    """Основная функция для работы с утилитой из командной строки"""
    parser = argparse.ArgumentParser(description="Утилита для конвертации данных базы знаний")
    
    # Параметры для ввода и вывода
    parser.add_argument('--input', '-i', help='Путь к входному файлу')
    parser.add_argument('--output', '-o', help='Путь к выходному файлу')
    parser.add_argument('--format', '-f', choices=['csv', 'json', 'excel', 'db'], 
                        help='Формат входного файла (по умолчанию определяется по расширению)')
    parser.add_argument('--out-format', choices=['csv', 'json', 'excel', 'db'], 
                        help='Формат выходного файла (по умолчанию определяется по расширению)')
    parser.add_argument('--delimiter', '-d', default=',', help='Разделитель для CSV (по умолчанию ",")')
    parser.add_argument('--sheet', help='Имя листа для Excel')
    
    args = parser.parse_args()
    
    # Определяем формат входного файла
    input_format = args.format
    if not input_format and args.input:
        if args.input.endswith('.csv'):
            input_format = 'csv'
        elif args.input.endswith('.json'):
            input_format = 'json'
        elif args.input.endswith('.xlsx') or args.input.endswith('.xls'):
            input_format = 'excel'
    
    # Определяем формат выходного файла
    output_format = args.out_format
    if not output_format and args.output:
        if args.output.endswith('.csv'):
            output_format = 'csv'
        elif args.output.endswith('.json'):
            output_format = 'json'
        elif args.output.endswith('.xlsx') or args.output.endswith('.xls'):
            output_format = 'excel'
        elif args.output.endswith('.db'):
            output_format = 'db'
    
    # Загружаем данные
    knowledge_data = []
    
    if args.input:
        if input_format == 'csv':
            knowledge_data = csv_to_knowledge(args.input, args.delimiter)
        elif input_format == 'json':
            knowledge_data = json_to_knowledge(args.input)
        elif input_format == 'excel':
            knowledge_data = excel_to_knowledge(args.input, args.sheet)
        else:
            logger.error("Не удалось определить формат входного файла")
            return
    else:
        # Если входной файл не указан, загружаем из базы данных
        knowledge_data = load_knowledge_from_db()
    
    # Проверяем, что данные загружены
    if not knowledge_data:
        logger.error("Не удалось загрузить данные")
        return
    
    # Сохраняем данные
    if args.output:
        if output_format == 'csv':
            knowledge_to_csv(knowledge_data, args.output, args.delimiter)
        elif output_format == 'json':
            knowledge_to_json(knowledge_data, args.output)
        elif output_format == 'excel':
            knowledge_to_excel(knowledge_data, args.output)
        elif output_format == 'db':
            save_knowledge_to_db(knowledge_data)
        else:
            logger.error("Не удалось определить формат выходного файла")
    else:
        # Если выходной файл не указан, выводим в консоль количество записей
        print(f"Загружено {len(knowledge_data)} записей")

if __name__ == "__main__":
    main()
