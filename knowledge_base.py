import os
import json
import sqlite3
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import threading
import asyncio

from config import DB_PATH, logger
from database import load_knowledge as db_load_knowledge, save_knowledge as db_save_knowledge

# Блокировка для обеспечения потокобезопасности
_kb_lock = threading.Lock()

def get_topic_nodes() -> List[Dict[str, Any]]:
    """
    Получает список тематических узлов верхнего уровня
    
    Returns:
        Список словарей с информацией о узлах
    """
    try:
        with _kb_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Получаем узлы верхнего уровня
            c.execute("""
            SELECT * FROM knowledge 
            WHERE is_category=1 AND (topic_path='root' OR topic_path IS NULL OR topic_path='')
            ORDER BY id
            """)
            
            result = [dict(row) for row in c.fetchall()]
            conn.close()
            
            return result
            
    except Exception as e:
        logger.error(f"Ошибка получения тематических узлов: {e}")
        return []

def get_children(parent_id: int) -> List[Dict[str, Any]]:
    """
    Получает дочерние узлы для заданного родительского узла
    
    Args:
        parent_id: ID родительского узла
        
    Returns:
        Список словарей с информацией о дочерних узлах
    """
    try:
        with _kb_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Формируем путь родительского узла
            c.execute("SELECT topic_path FROM knowledge WHERE id=?", (parent_id,))
            parent_row = c.fetchone()
            
            if not parent_row:
                return []
            
            parent_path = parent_row["topic_path"]
            
            # Если путь пустой или root, используем только id
            if not parent_path or parent_path == "root":
                full_path = str(parent_id)
            else:
                full_path = f"{parent_path}/{parent_id}"
            
            # Получаем дочерние узлы
            c.execute("""
            SELECT * FROM knowledge 
            WHERE topic_path=?
            ORDER BY is_category DESC, id
            """, (full_path,))
            
            result = [dict(row) for row in c.fetchall()]
            conn.close()
            
            return result
            
    except Exception as e:
        logger.error(f"Ошибка получения дочерних узлов: {e}")
        return []

def add_knowledge_node(
    question: str, 
    answer: str, 
    parent_id: Optional[int] = None, 
    is_category: bool = False
) -> int:
    """
    Добавляет новый узел знаний в базу данных
    
    Args:
        question: Текст вопроса или название категории
        answer: Текст ответа или описание категории
        parent_id: ID родительского узла (опционально)
        is_category: Является ли узел категорией
        
    Returns:
        ID добавленного узла или 0 в случае ошибки
    """
    try:
        with _kb_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Определяем путь для нового узла
            topic_path = "root"
            
            if parent_id:
                # Получаем информацию о родительском узле
                c.execute("SELECT topic_path FROM knowledge WHERE id=?", (parent_id,))
                parent_row = c.fetchone()
                
                if parent_row:
                    parent_path = parent_row[0]
                    
                    # Если путь пустой или root, используем только id
                    if not parent_path or parent_path == "root":
                        topic_path = str(parent_id)
                    else:
                        topic_path = f"{parent_path}/{parent_id}"
            
            # Текущее время
            timestamp = datetime.now().isoformat()
            
            # Добавляем новый узел
            c.execute("""
            INSERT INTO knowledge (question, answer, topic_path, timestamp, is_category)
            VALUES (?, ?, ?, ?, ?)
            """, (question, answer, topic_path, timestamp, 1 if is_category else 0))
            
            # Получаем ID добавленного узла
            node_id = c.lastrowid
            
            conn.commit()
            conn.close()
            
            logger.info(f"Добавлен новый узел знаний: {node_id} (категория: {is_category})")
            return node_id
            
    except Exception as e:
        logger.error(f"Ошибка добавления узла знаний: {e}")
        return 0

def update_knowledge_node(
    node_id: int, 
    question: Optional[str] = None, 
    answer: Optional[str] = None,
    is_category: Optional[bool] = None
) -> bool:
    """
    Обновляет существующий узел знаний
    
    Args:
        node_id: ID узла
        question: Новый текст вопроса (опционально)
        answer: Новый текст ответа (опционально)
        is_category: Новый статус узла (опционально)
        
    Returns:
        True, если обновление успешно
    """
    try:
        with _kb_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Формируем запрос и параметры
            query_parts = []
            params = []
            
            if question is not None:
                query_parts.append("question=?")
                params.append(question)
            
            if answer is not None:
                query_parts.append("answer=?")
                params.append(answer)
            
            if is_category is not None:
                query_parts.append("is_category=?")
                params.append(1 if is_category else 0)
            
            # Если нет параметров для обновления, выходим
            if not query_parts:
                conn.close()
                return False
            
            # Обновляем время изменения
            query_parts.append("timestamp=?")
            params.append(datetime.now().isoformat())
            
            # Добавляем ID узла в параметры
            params.append(node_id)
            
            # Выполняем запрос
            query = f"UPDATE knowledge SET {', '.join(query_parts)} WHERE id=?"
            c.execute(query, params)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Обновлен узел знаний: {node_id}")
            return True
            
    except Exception as e:
        logger.error(f"Ошибка обновления узла знаний: {e}")
        return False

def delete_knowledge_node(node_id: int, recursive: bool = False) -> bool:
    """
    Удаляет узел знаний
    
    Args:
        node_id: ID узла
        recursive: Удалять также дочерние узлы
        
    Returns:
        True, если удаление успешно
    """
    try:
        with _kb_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Получаем информацию о узле
            c.execute("SELECT topic_path FROM knowledge WHERE id=?", (node_id,))
            node_row = c.fetchone()
            
            if not node_row:
                conn.close()
                return False
            
            # Если требуется рекурсивное удаление
            if recursive:
                # Формируем шаблон для поиска дочерних узлов
                parent_path = node_row[0]
                
                # Если путь пустой или root, используем только id
                if not parent_path or parent_path == "root":
                    full_path = str(node_id)
                else:
                    full_path = f"{parent_path}/{node_id}"
                
                # Удаляем все дочерние узлы
                c.execute("DELETE FROM knowledge WHERE topic_path=?", (full_path,))
            
            # Удаляем сам узел
            c.execute("DELETE FROM knowledge WHERE id=?", (node_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Удален узел знаний: {node_id} (рекурсивно: {recursive})")
            return True
            
    except Exception as e:
        logger.error(f"Ошибка удаления узла знаний: {e}")
        return False

def move_knowledge_node(node_id: int, new_parent_id: Optional[int] = None) -> bool:
    """
    Перемещает узел знаний в другую категорию
    
    Args:
        node_id: ID узла
        new_parent_id: ID нового родительского узла (None для перемещения в корень)
        
    Returns:
        True, если перемещение успешно
    """
    try:
        with _kb_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Определяем новый путь
            new_path = "root"
            
            if new_parent_id:
                # Получаем информацию о новом родительском узле
                c.execute("SELECT topic_path, is_category FROM knowledge WHERE id=?", (new_parent_id,))
                parent_row = c.fetchone()
                
                # Проверяем, что родительский узел существует и является категорией
                if not parent_row:
                    conn.close()
                    return False
                
                if parent_row[1] != 1:  # is_category=0
                    conn.close()
                    return False
                
                parent_path = parent_row[0]
                
                # Если путь пустой или root, используем только id
                if not parent_path or parent_path == "root":
                    new_path = str(new_parent_id)
                else:
                    new_path = f"{parent_path}/{new_parent_id}"
            
            # Обновляем путь узла
            c.execute("""
            UPDATE knowledge 
            SET topic_path=?, timestamp=?
            WHERE id=?
            """, (new_path, datetime.now().isoformat(), node_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Перемещен узел знаний: {node_id} -> {new_path}")
            return True
            
    except Exception as e:
        logger.error(f"Ошибка перемещения узла знаний: {e}")
        return False

def search_knowledge(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Выполняет поиск по базе знаний
    
    Args:
        query: Поисковый запрос
        limit: Максимальное количество результатов
        
    Returns:
        Список словарей с результатами поиска
    """
    try:
        with _kb_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Выполняем поиск по вопросу и ответу
            c.execute("""
            SELECT * FROM knowledge 
            WHERE question LIKE ? OR answer LIKE ?
            ORDER BY is_category DESC, id
            LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit))
            
            result = [dict(row) for row in c.fetchall()]
            conn.close()
            
            return result
            
    except Exception as e:
        logger.error(f"Ошибка поиска в базе знаний: {e}")
        return []

def get_knowledge_tree() -> Dict[str, Any]:
    """
    Получает иерархическое дерево базы знаний
    
    Returns:
        Словарь с иерархическим представлением базы знаний
    """
    def build_tree(node_id, path):
        children = get_children(node_id)
        node_children = []
        
        for child in children:
            if child["is_category"]:
                # Если это категория, рекурсивно строим дерево
                child_tree = build_tree(child["id"], path + [child["question"]])
                node_children.append(child_tree)
            else:
                # Если это конечный узел, добавляем как есть
                node_children.append({
                    "id": child["id"],
                    "title": child["question"],
                    "type": "item",
                    "path": path + [child["question"]]
                })
        
        return {
            "id": node_id,
            "title": nodes_dict.get(node_id, {}).get("question", f"Категория {node_id}"),
            "type": "category",
            "path": path,
            "children": node_children
        }
    
    try:
        # Получаем все узлы
        all_nodes = []
        
        with _kb_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("SELECT * FROM knowledge")
            all_nodes = [dict(row) for row in c.fetchall()]
            conn.close()
        
        # Создаем словарь узлов для быстрого доступа
        nodes_dict = {node["id"]: node for node in all_nodes}
        
        # Получаем корневые категории
        root_categories = [node for node in all_nodes if node["is_category"] and (
            node["topic_path"] == "root" or not node["topic_path"])]
        
        # Строим дерево
        tree = {
            "title": "База знаний",
            "type": "root",
            "children": []
        }
        
        for category in root_categories:
            category_tree = build_tree(category["id"], [category["question"]])
            tree["children"].append(category_tree)
        
        return tree
        
    except Exception as e:
        logger.error(f"Ошибка построения дерева знаний: {e}")
        return {"title": "Ошибка", "type": "root", "children": []}

def import_knowledge_from_json(json_data: str) -> bool:
    """
    Импортирует базу знаний из JSON строки
    
    Args:
        json_data: Строка с данными в формате JSON
        
    Returns:
        True, если импорт успешен
    """
    try:
        # Парсим JSON
        data = json.loads(json_data)
        
        # Проверяем формат данных
        if not isinstance(data, list):
            logger.error("Неверный формат данных: ожидается список")
            return False
        
        # Проверяем содержимое
        for item in data:
            if not isinstance(item, dict) or "question" not in item or "answer" not in item:
                logger.error("Неверный формат элемента данных: отсутствуют обязательные поля")
                return False
        
        # Импортируем данные
        with _kb_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Очищаем существующую базу знаний
            c.execute("DELETE FROM knowledge")
            
            # Добавляем новые данные
            timestamp = datetime.now().isoformat()
            
            for item in data:
                c.execute("""
                INSERT INTO knowledge 
                (id, question, answer, topic_path, timestamp, is_category)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    item.get("id", None),
                    item["question"],
                    item["answer"],
                    item.get("topic_path", "root"),
                    item.get("timestamp", timestamp),
                    item.get("is_category", 0)
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Импортировано {len(data)} записей в базу знаний")
            return True
            
    except json.JSONDecodeError:
        logger.error("Ошибка разбора JSON")
        return False
    except Exception as e:
        logger.error(f"Ошибка импорта базы знаний: {e}")
        return False

def export_knowledge_to_json() -> str:
    """
    Экспортирует базу знаний в JSON строку
    
    Returns:
        Строка с данными в формате JSON
    """
    try:
        with _kb_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("SELECT * FROM knowledge")
            data = [dict(row) for row in c.fetchall()]
            conn.close()
            
            # Преобразуем в JSON
            json_data = json.dumps(data, ensure_ascii=False, indent=2)
            
            logger.info(f"Экспортировано {len(data)} записей из базы знаний")
            return json_data
            
    except Exception as e:
        logger.error(f"Ошибка экспорта базы знаний: {e}")
        return "[]"

def add_batch_knowledge(items: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Добавляет несколько записей в базу знаний
    
    Args:
        items: Список словарей с данными (каждый должен содержать question и answer)
        
    Returns:
        Кортеж (успешно добавлено, всего элементов)
    """
    success_count = 0
    
    try:
        with _kb_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Получаем максимальный ID
            c.execute("SELECT MAX(id) FROM knowledge")
            max_id = c.fetchone()[0] or 0
            
            # Добавляем записи по одной
            timestamp = datetime.now().isoformat()
            
            for i, item in enumerate(items):
                if "question" not in item or "answer" not in item:
                    continue
                
                try:
                    # Генерируем новый ID
                    new_id = max_id + i + 1
                    
                    c.execute("""
                    INSERT INTO knowledge 
                    (id, question, answer, topic_path, timestamp, is_category)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        new_id,
                        item["question"],
                        item["answer"],
                        item.get("topic_path", "root"),
                        item.get("timestamp", timestamp),
                        item.get("is_category", 0)
                    ))
                    
                    success_count += 1
                except Exception as item_error:
                    logger.error(f"Ошибка добавления элемента {i}: {item_error}")
            
            conn.commit()
            conn.close()
            
            logger.info(f"Добавлено {success_count} из {len(items)} записей в базу знаний")
            return success_count, len(items)
            
    except Exception as e:
        logger.error(f"Ошибка пакетного добавления в базу знаний: {e}")
        return success_count, len(items)

def save_knowledge(knowledge_data: List[Dict[str, Any]]) -> bool:
    """
    Сохраняет базу знаний в базу данных
    
    Args:
        knowledge_data: Список словарей с данными базы знаний
        
    Returns:
        True если сохранение прошло успешно
    """
    try:
        result = db_save_knowledge(knowledge_data)
        if result:
            logger.info(f"База знаний успешно сохранена: {len(knowledge_data)} записей")
            # Обновляем индекс FAISS после сохранения базы знаний
            asyncio.create_task(update_faiss_index())
        return result
    except Exception as e:
        logger.error(f"Ошибка сохранения базы знаний: {e}")
        return False
