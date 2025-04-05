import os
import sqlite3
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import threading
import hashlib

from config import DB_PATH, logger

# Блокировка для обеспечения потокобезопасного доступа к базе данных
_db_lock = threading.Lock()

def init_database() -> bool:
    """
    Инициализирует базу данных, создает необходимые таблицы
    
    Returns:
        True если инициализация прошла успешно
    """
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Таблица для хранения базы знаний
            c.execute('''
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                topic_path TEXT DEFAULT 'general',
                timestamp TEXT NOT NULL,
                is_category INTEGER DEFAULT 0
            )
            ''')
            
            # Таблица для кэша ответов
            c.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                question_hash TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                last_accessed TEXT NOT NULL
            )
            ''')
            
            # Таблица для PDF-файлов
            c.execute('''
            CREATE TABLE IF NOT EXISTS pdf_files (
                file_hash TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                page_count INTEGER,
                indexed INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL
            )
            ''')
            
            # Таблица для кэша результатов поиска в PDF
            c.execute('''
            CREATE TABLE IF NOT EXISTS pdf_cache (
                question_hash TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                context TEXT NOT NULL,
                source_info TEXT,
                timestamp TEXT NOT NULL
            )
            ''')
            
            # Таблица для неотвеченных вопросов
            c.execute('''
            CREATE TABLE IF NOT EXISTS unanswered_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                answered INTEGER DEFAULT 0
            )
            ''')
            
            # Создаем индексы для ускорения запросов
            c.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_topic ON knowledge(topic_path)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_cache_timestamp ON cache(timestamp)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_pdf_files_indexed ON pdf_files(indexed)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_unanswered_answered ON unanswered_questions(answered)')
            
            conn.commit()
            conn.close()
            
            logger.info("База данных успешно инициализирована")
            return True
            
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
        return False

def load_knowledge() -> List[Dict[str, Any]]:
    """
    Загружает базу знаний из базы данных
    
    Returns:
        Список словарей с данными базы знаний
    """
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("SELECT * FROM knowledge ORDER BY id")
            result = [dict(row) for row in c.fetchall()]
            
            conn.close()
            
            return result
            
    except sqlite3.OperationalError:
        # Если таблица не существует, инициализируем базу данных
        init_database()
        return []
        
    except Exception as e:
        logger.error(f"Ошибка загрузки базы знаний: {e}")
        return []

def save_knowledge(data: List[Dict[str, Any]]) -> bool:
    """
    Сохраняет базу знаний в базу данных
    
    Args:
        data: Список словарей с данными базы знаний
        
    Returns:
        True если сохранение прошло успешно
    """
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Очищаем таблицу
            c.execute("DELETE FROM knowledge")
            
            # Вставляем новые данные
            timestamp = datetime.now().isoformat()
            
            for item in data:
                c.execute("""
                INSERT INTO knowledge (id, question, answer, topic_path, timestamp, is_category)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    item.get("id", 0),
                    item.get("question", ""),
                    item.get("answer", ""),
                    item.get("topic_path", "general"),
                    item.get("timestamp", timestamp),
                    item.get("is_category", 0)
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"База знаний успешно сохранена: {len(data)} записей")
            return True
            
    except Exception as e:
        logger.error(f"Ошибка сохранения базы знаний: {e}")
        return False

def add_to_cache(question: str, answer: str) -> bool:
    """
    Добавляет пару вопрос-ответ в кэш
    
    Args:
        question: Вопрос
        answer: Ответ
        
    Returns:
        True если добавление прошло успешно
    """
    try:
        with _db_lock:
            # Вычисляем хеш вопроса
            question_hash = hashlib.md5(question.encode('utf-8')).hexdigest()
            
            # Текущее время
            timestamp = datetime.now().isoformat()
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            c.execute("""
            INSERT OR REPLACE INTO cache (question_hash, question, answer, timestamp, last_accessed)
            VALUES (?, ?, ?, ?, ?)
            """, (question_hash, question, answer, timestamp, timestamp))
            
            conn.commit()
            conn.close()
            
            return True
            
    except Exception as e:
        logger.error(f"Ошибка добавления в кэш: {e}")
        return False

def get_cached_answer(question_hash: str) -> Optional[Dict[str, Any]]:
    """
    Получает ответ из кэша по хешу вопроса
    
    Args:
        question_hash: Хеш вопроса
        
    Returns:
        Словарь с ответом или None, если ответ не найден
    """
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("SELECT * FROM cache WHERE question_hash=?", (question_hash,))
            result = c.fetchone()
            
            if result:
                # Обновляем время последнего доступа
                timestamp = datetime.now().isoformat()
                c.execute("UPDATE cache SET last_accessed=? WHERE question_hash=?", 
                         (timestamp, question_hash))
                conn.commit()
                
                cache_entry = dict(result)
                
                conn.close()
                return cache_entry
            
            conn.close()
            return None
            
    except Exception as e:
        logger.error(f"Ошибка получения кэша: {e}")
        return None

def load_cache() -> Dict[str, Dict[str, Any]]:
    """
    Загружает весь кэш из базы данных
    
    Returns:
        Словарь с данными кэша, где ключ - хеш вопроса
    """
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("SELECT * FROM cache")
            rows = c.fetchall()
            
            cache_data = {}
            for row in rows:
                data = dict(row)
                cache_data[data['question_hash']] = data
            
            conn.close()
            
            return cache_data
            
    except sqlite3.OperationalError:
        # Если таблица не существует, инициализируем базу данных
        init_database()
        return {}
        
    except Exception as e:
        logger.error(f"Ошибка загрузки кэша: {e}")
        return {}

def save_cache(cache_data: Dict[str, Dict[str, Any]]) -> bool:
    """
    Сохраняет кэш в базу данных
    
    Args:
        cache_data: Словарь с данными кэша
        
    Returns:
        True если сохранение прошло успешно
    """
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Очищаем таблицу
            c.execute("DELETE FROM cache")
            
            # Вставляем новые данные
            for question_hash, data in cache_data.items():
                c.execute("""
                INSERT INTO cache (question_hash, question, answer, timestamp, last_accessed)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    question_hash,
                    data.get('question', ''),
                    data.get('answer', ''),
                    data.get('timestamp', datetime.now().isoformat()),
                    data.get('last_accessed', datetime.now().isoformat())
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Кэш успешно сохранен: {len(cache_data)} записей")
            return True
            
    except Exception as e:
        logger.error(f"Ошибка сохранения кэша: {e}")
        return False

def add_to_pdf_cache(question: str, context: str, source_info: str = "") -> bool:
    """
    Добавляет результаты поиска по PDF в кэш
    
    Args:
        question: Вопрос
        context: Найденный контекст
        source_info: Информация об источнике
        
    Returns:
        True если добавление прошло успешно
    """
    try:
        with _db_lock:
            # Вычисляем хеш вопроса
            question_hash = hashlib.md5(question.encode('utf-8')).hexdigest()
            
            # Текущее время
            timestamp = datetime.now().isoformat()
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            c.execute("""
            INSERT OR REPLACE INTO pdf_cache (question_hash, question, context, source_info, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """, (question_hash, question, context, source_info, timestamp))
            
            conn.commit()
            conn.close()
            
            return True
            
    except Exception as e:
        logger.error(f"Ошибка добавления в PDF кэш: {e}")
        return False

def get_pdf_cached_context(question_hash: str) -> Optional[Dict[str, Any]]:
    """
    Получает контекст из PDF кэша по хешу вопроса
    
    Args:
        question_hash: Хеш вопроса
        
    Returns:
        Словарь с контекстом или None, если контекст не найден
    """
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("SELECT * FROM pdf_cache WHERE question_hash=?", (question_hash,))
            result = c.fetchone()
            
            conn.close()
            
            if result:
                return dict(result)
            
            return None
            
    except Exception as e:
        logger.error(f"Ошибка получения PDF кэша: {e}")
        return None

def add_unanswered_question(user_id: int, question: str) -> int:
    """
    Добавляет неотвеченный вопрос в базу данных
    
    Args:
        user_id: ID пользователя
        question: Текст вопроса
        
    Returns:
        ID добавленной записи или 0 в случае ошибки
    """
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Текущее время
            timestamp = datetime.now().isoformat()
            
            c.execute("""
            INSERT INTO unanswered_questions (user_id, question, timestamp, answered)
            VALUES (?, ?, ?, 0)
            """, (user_id, question, timestamp))
            
            # Получаем ID добавленной записи
            question_id = c.lastrowid
            
            conn.commit()
            conn.close()
            
            return question_id
            
    except Exception as e:
        logger.error(f"Ошибка добавления неотвеченного вопроса: {e}")
        return 0

def get_unanswered_questions() -> List[Dict[str, Any]]:
    """
    Получает список неотвеченных вопросов
    
    Returns:
        Список словарей с неотвеченными вопросами
    """
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("""
            SELECT * FROM unanswered_questions 
            WHERE answered=0 
            ORDER BY timestamp DESC
            """)
            
            result = [dict(row) for row in c.fetchall()]
            
            conn.close()
            
            return result
            
    except Exception as e:
        logger.error(f"Ошибка получения неотвеченных вопросов: {e}")
        return []

def mark_question_as_answered(question_id: int) -> bool:
    """
    Отмечает вопрос как отвеченный
    
    Args:
        question_id: ID вопроса
        
    Returns:
        True если обновление прошло успешно
    """
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            c.execute("""
            UPDATE unanswered_questions 
            SET answered=1 
            WHERE id=?
            """, (question_id,))
            
            conn.commit()
            conn.close()
            
            return True
            
    except Exception as e:
        logger.error(f"Ошибка отметки вопроса как отвеченного: {e}")
        return False

def clear_old_cache(days: int = 7) -> int:
    """
    Очищает старые записи из кэша
    
    Args:
        days: Возраст записей для удаления в днях
        
    Returns:
        Количество удаленных записей
    """
    try:
        with _db_lock:
            # Вычисляем дату для сравнения
            cutoff_date = (datetime.now() - datetime.timedelta(days=days)).isoformat()
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Удаляем старые записи из кэша ответов
            c.execute("DELETE FROM cache WHERE last_accessed < ?", (cutoff_date,))
            answer_cache_deleted = c.rowcount
            
            # Удаляем старые записи из PDF кэша
            c.execute("DELETE FROM pdf_cache WHERE timestamp < ?", (cutoff_date,))
            pdf_cache_deleted = c.rowcount
            
            conn.commit()
            conn.close()
            
            total_deleted = answer_cache_deleted + pdf_cache_deleted
            logger.info(f"Очистка кэша: удалено {total_deleted} записей (старше {days} дней)")
            
            return total_deleted
            
    except Exception as e:
        logger.error(f"Ошибка очистки старого кэша: {e}")
        return 0

def get_all_users() -> List[Dict[str, Any]]:
    """
    Получает список всех пользователей бота
    
    Returns:
        Список словарей с информацией о пользователях
    """
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Получаем уникальных пользователей из таблицы аналитики
            c.execute("""
            SELECT DISTINCT user_id FROM analytics_user_stats
            ORDER BY last_seen DESC
            """)
            
            users = []
            for row in c.fetchall():
                user_id = row['user_id']
                
                # Получаем дополнительную информацию о пользователе
                c.execute("""
                SELECT * FROM analytics_user_stats WHERE user_id=?
                """, (user_id,))
                user_data = dict(c.fetchone())
                
                users.append(user_data)
            
            conn.close()
            return users
            
    except Exception as e:
        logger.error(f"Ошибка получения списка пользователей: {e}")
        return []

def add_user_if_not_exists(user_id: int, username: str = None, first_name: str = None, 
                          last_name: str = None) -> bool:
    """
    Добавляет пользователя в базу данных, если его там нет
    
    Args:
        user_id: ID пользователя
        username: Имя пользователя (опционально)
        first_name: Имя (опционально)
        last_name: Фамилия (опционально)
        
    Returns:
        True если операция прошла успешно
    """
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Проверяем, существует ли пользователь
            c.execute("SELECT COUNT(*) FROM analytics_user_stats WHERE user_id=?", (user_id,))
            exists = c.fetchone()[0] > 0
            
            if not exists:
                # Текущая дата и время
                timestamp = datetime.now().isoformat()
                
                # Создаем данные пользователя
                user_data = {
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name
                }
                
                # Вставляем нового пользователя
                c.execute("""
                INSERT INTO analytics_user_stats 
                (user_id, first_seen, last_seen, total_messages, successful_queries, failed_queries, user_data)
                VALUES (?, ?, ?, 0, 0, 0, ?)
                """, (user_id, timestamp, timestamp, json.dumps(user_data, ensure_ascii=False)))
            else:
                # Если пользователь существует, обновляем его данные
                if any([username, first_name, last_name]):
                    # Получаем текущие данные
                    c.execute("SELECT user_data FROM analytics_user_stats WHERE user_id=?", (user_id,))
                    user_data_json = c.fetchone()[0]
                    
                    try:
                        user_data = json.loads(user_data_json) if user_data_json else {}
                    except:
                        user_data = {}
                    
                    # Обновляем данные
                    if username:
                        user_data["username"] = username
                    if first_name:
                        user_data["first_name"] = first_name
                    if last_name:
                        user_data["last_name"] = last_name
                    
                    # Сохраняем обновленные данные
                    c.execute("""
                    UPDATE analytics_user_stats 
                    SET user_data=? 
                    WHERE user_id=?
                    """, (json.dumps(user_data, ensure_ascii=False), user_id))
            
            conn.commit()
            conn.close()
            return True
            
    except Exception as e:
        logger.error(f"Ошибка добавления пользователя: {e}")
        return False

def log_admin_message(admin_id: int, message_text: str, sent_count: int = 0) -> int:
    """
    Записывает информацию о рассылке администратора
    
    Args:
        admin_id: ID администратора
        message_text: Текст сообщения
        sent_count: Количество отправленных сообщений
        
    Returns:
        ID сообщения или 0 в случае ошибки
    """
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Создаем таблицу для хранения сообщений администраторов, если её нет
            c.execute('''
            CREATE TABLE IF NOT EXISTS admin_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                sent_count INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL
            )
            ''')
            
            # Текущая дата и время
            timestamp = datetime.now().isoformat()
            
            # Вставляем запись о сообщении
            c.execute("""
            INSERT INTO admin_messages (admin_id, message_text, sent_count, timestamp)
            VALUES (?, ?, ?, ?)
            """, (admin_id, message_text, sent_count, timestamp))
            
            # Получаем ID добавленной записи
            message_id = c.lastrowid
            
            conn.commit()
            conn.close()
            
            return message_id
            
    except Exception as e:
        logger.error(f"Ошибка записи сообщения администратора: {e}")
        return 0

def update_admin_message_stats(message_id: int, sent_count: int) -> bool:
    """
    Обновляет статистику отправки сообщения администратора
    
    Args:
        message_id: ID сообщения
        sent_count: Количество отправленных сообщений
        
    Returns:
        True если обновление прошло успешно
    """
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Обновляем количество отправленных сообщений
            c.execute("""
            UPDATE admin_messages 
            SET sent_count=? 
            WHERE id=?
            """, (sent_count, message_id))
            
            conn.commit()
            conn.close()
            
            return True
            
    except Exception as e:
        logger.error(f"Ошибка обновления статистики сообщения: {e}")
        return False

# Инициализируем базу данных при импорте модуля
init_database()
