import os
import threading
import hashlib
import sqlite3
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from config import DB_PATH, logger, APP_ENV

class Analytics:
    """Класс для сбора и анализа статистики использования бота"""
    
    def __init__(self, db_path: str = DB_PATH):
        """
        Инициализирует модуль аналитики
        
        Args:
            db_path: Путь к базе данных
        """
        self.db_path = db_path
        self.stats_cache = {}
        self.lock = threading.Lock()
        
        # Инициализируем таблицы аналитики
        self._init_analytics_tables()
    
    def _init_analytics_tables(self) -> None:
        """Инициализирует таблицы для аналитики в базе данных"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                
                # Таблица для событий
                c.execute('''
                CREATE TABLE IF NOT EXISTS analytics_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data TEXT,
                    timestamp TEXT NOT NULL
                )
                ''')
                
                # Таблица для ежедневной статистики
                c.execute('''
                CREATE TABLE IF NOT EXISTS analytics_daily_stats (
                    date TEXT PRIMARY KEY,
                    total_messages INTEGER DEFAULT 0,
                    unique_users INTEGER DEFAULT 0,
                    new_users INTEGER DEFAULT 0,
                    successful_queries INTEGER DEFAULT 0,
                    failed_queries INTEGER DEFAULT 0,
                    stats_data TEXT
                )
                ''')
                
                # Таблица для пользовательской статистики
                c.execute('''
                CREATE TABLE IF NOT EXISTS analytics_user_stats (
                    user_id INTEGER PRIMARY KEY,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    total_messages INTEGER DEFAULT 0,
                    successful_queries INTEGER DEFAULT 0,
                    failed_queries INTEGER DEFAULT 0,
                    user_data TEXT
                )
                ''')
                
                # Таблица для статистики запросов
                c.execute('''
                CREATE TABLE IF NOT EXISTS analytics_query_stats (
                    query_hash TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    count INTEGER DEFAULT 0,
                    last_used TEXT NOT NULL
                )
                ''')
                
                # Индексы для более быстрого доступа
                c.execute('CREATE INDEX IF NOT EXISTS idx_events_user_id ON analytics_events(user_id)')
                c.execute('CREATE INDEX IF NOT EXISTS idx_events_event_type ON analytics_events(event_type)')
                c.execute('CREATE INDEX IF NOT EXISTS idx_events_timestamp ON analytics_events(timestamp)')
                
                conn.commit()
                conn.close()
                
                logger.info("Таблицы аналитики успешно инициализированы")
        except Exception as e:
            logger.error(f"Ошибка инициализации таблиц аналитики: {e}")
    
    def record_event(self, user_id: int, event_type: str, event_data: Dict[str, Any] = None) -> bool:
        """
        Записывает событие в базу данных
        
        Args:
            user_id: ID пользователя
            event_type: Тип события ('message', 'query', 'error', etc.)
            event_data: Дополнительные данные события (опционально)
            
        Returns:
            True, если запись успешна
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                
                # Преобразуем данные события в JSON
                event_data_json = json.dumps(event_data or {}, ensure_ascii=False)
                
                # Текущее время
                timestamp = datetime.now().isoformat()
                
                # Записываем событие
                c.execute('''
                INSERT INTO analytics_events (user_id, event_type, event_data, timestamp)
                VALUES (?, ?, ?, ?)
                ''', (user_id, event_type, event_data_json, timestamp))
                
                # Обновляем статистику пользователя
                self._update_user_stats(c, user_id, event_type, timestamp)
                
                # Обновляем статистику запросов, если это запрос
                if event_type == 'query' and event_data and 'query_text' in event_data:
                    self._update_query_stats(c, event_data['query_text'])
                
                conn.commit()
                conn.close()
                
                return True
                
        except Exception as e:
            logger.error(f"Ошибка записи события: {e}")
            return False
    
    def _update_user_stats(self, cursor, user_id: int, event_type: str, timestamp: str) -> None:
        """
        Обновляет статистику пользователя
        
        Args:
            cursor: Курсор базы данных
            user_id: ID пользователя
            event_type: Тип события
            timestamp: Временная метка
        """
        # Проверяем, существует ли запись о пользователе
        cursor.execute('''
        SELECT * FROM analytics_user_stats WHERE user_id=?
        ''', (user_id,))
        
        user_exists = cursor.fetchone()
        
        if user_exists:
            # Обновляем существующую запись
            updates = [
                "last_seen=?",
                "total_messages=total_messages+1"
            ]
            
            params = [timestamp]
            
            # Если это запрос, увеличиваем соответствующий счетчик
            if event_type == 'query':
                updates.append("successful_queries=successful_queries+1")
            elif event_type == 'error':
                updates.append("failed_queries=failed_queries+1")
            
            cursor.execute(f'''
            UPDATE analytics_user_stats 
            SET {", ".join(updates)}
            WHERE user_id=?
            ''', params + [user_id])
        else:
            # Создаем новую запись
            successful_queries = 1 if event_type == 'query' else 0
            failed_queries = 1 if event_type == 'error' else 0
            
            cursor.execute('''
            INSERT INTO analytics_user_stats 
            (user_id, first_seen, last_seen, total_messages, successful_queries, failed_queries, user_data)
            VALUES (?, ?, ?, 1, ?, ?, '{}')
            ''', (user_id, timestamp, timestamp, successful_queries, failed_queries))
    
    def _update_query_stats(self, cursor, query: str) -> None:
        """
        Обновляет статистику запросов
        
        Args:
            cursor: Курсор базы данных
            query: Текст запроса
        """
        # Создаем хеш запроса
        query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
        
        # Текущее время
        timestamp = datetime.now().isoformat()
        
        # Проверяем, существует ли запись о запросе
        cursor.execute('''
        SELECT * FROM analytics_query_stats WHERE query_hash=?
        ''', (query_hash,))
        
        query_exists = cursor.fetchone()
        
        if query_exists:
            # Обновляем существующую запись
            cursor.execute('''
            UPDATE analytics_query_stats 
            SET count=count+1, last_used=?
            WHERE query_hash=?
            ''', (timestamp, query_hash))
        else:
            # Создаем новую запись
            cursor.execute('''
            INSERT INTO analytics_query_stats 
            (query_hash, query, count, last_used)
            VALUES (?, ?, 1, ?)
            ''', (query_hash, query, timestamp))
    
    def update_daily_stats(self) -> bool:
        """
        Обновляет ежедневную статистику
        
        Returns:
            True, если обновление успешно
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                
                # Получаем текущую дату в формате YYYY-MM-DD
                today = datetime.now().strftime("%Y-%m-%d")
                
                # Получаем статистику за сегодня
                total_messages = self._get_total_messages_today(c)
                unique_users = self._get_unique_users_today(c)
                new_users = self._get_new_users_today(c)
                successful_queries = self._get_successful_queries_today(c)
                failed_queries = self._get_failed_queries_today(c)
                
                # Формируем дополнительные данные статистики
                stats_data = {
                    "query_distribution": self._get_query_type_distribution(c),
                    "top_queries": self._get_top_queries_today(c, 10),
                    "active_hours": self._get_active_hours_today(c)
                }
                
                stats_data_json = json.dumps(stats_data, ensure_ascii=False)
                
                # Проверяем, существует ли запись за сегодня
                c.execute('''
                SELECT * FROM analytics_daily_stats WHERE date=?
                ''', (today,))
                
                exists = c.fetchone()
                
                if exists:
                    # Обновляем существующую запись
                    c.execute('''
                    UPDATE analytics_daily_stats 
                    SET total_messages=?, unique_users=?, new_users=?, 
                        successful_queries=?, failed_queries=?, stats_data=?
                    WHERE date=?
                    ''', (total_messages, unique_users, new_users, 
                         successful_queries, failed_queries, stats_data_json, today))
                else:
                    # Создаем новую запись
                    c.execute('''
                    INSERT INTO analytics_daily_stats 
                    (date, total_messages, unique_users, new_users, 
                     successful_queries, failed_queries, stats_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (today, total_messages, unique_users, new_users, 
                         successful_queries, failed_queries, stats_data_json))
                
                conn.commit()
                conn.close()
                
                return True
                
        except Exception as e:
            logger.error(f"Ошибка обновления ежедневной статистики: {e}")
            return False
    
    def _get_total_messages_today(self, cursor) -> int:
        """
        Получает общее количество сообщений за сегодня
        
        Args:
            cursor: Курсор базы данных
            
        Returns:
            Количество сообщений
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        cursor.execute('''
        SELECT COUNT(*) FROM analytics_events 
        WHERE timestamp >= ?
        ''', (today_start,))
        
        return cursor.fetchone()[0]
    
    def _get_unique_users_today(self, cursor) -> int:
        """
        Получает количество уникальных пользователей за сегодня
        
        Args:
            cursor: Курсор базы данных
            
        Returns:
            Количество уникальных пользователей
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        cursor.execute('''
        SELECT COUNT(DISTINCT user_id) FROM analytics_events 
        WHERE timestamp >= ?
        ''', (today_start,))
        
        return cursor.fetchone()[0]
    
    def _get_new_users_today(self, cursor) -> int:
        """
        Получает количество новых пользователей за сегодня
        
        Args:
            cursor: Курсор базы данных
            
        Returns:
            Количество новых пользователей
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        cursor.execute('''
        SELECT COUNT(*) FROM analytics_user_stats 
        WHERE first_seen >= ?
        ''', (today_start,))
        
        return cursor.fetchone()[0]
    
    def _get_successful_queries_today(self, cursor) -> int:
        """
        Получает количество успешных запросов за сегодня
        
        Args:
            cursor: Курсор базы данных
            
        Returns:
            Количество успешных запросов
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        cursor.execute('''
        SELECT COUNT(*) FROM analytics_events 
        WHERE event_type='query' AND timestamp >= ?
        ''', (today_start,))
        
        return cursor.fetchone()[0]
    
    def _get_failed_queries_today(self, cursor) -> int:
        """
        Получает количество неудачных запросов за сегодня
        
        Args:
            cursor: Курсор базы данных
            
        Returns:
            Количество неудачных запросов
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        cursor.execute('''
        SELECT COUNT(*) FROM analytics_events 
        WHERE event_type='error' AND timestamp >= ?
        ''', (today_start,))
        
        return cursor.fetchone()[0]
    
    def _get_query_type_distribution(self, cursor) -> Dict[str, int]:
        """
        Получает распределение типов запросов за сегодня
        
        Args:
            cursor: Курсор базы данных
            
        Returns:
            Словарь {тип_запроса: количество}
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        cursor.execute('''
        SELECT event_data FROM analytics_events 
        WHERE event_type='query' AND timestamp >= ?
        ''', (today_start,))
        
        rows = cursor.fetchall()
        
        result = {}
        for row in rows:
            try:
                event_data = json.loads(row[0])
                query_type = event_data.get('query_type', 'unknown')
                
                if query_type not in result:
                    result[query_type] = 0
                
                result[query_type] += 1
            except:
                pass
        
        return result
    
    def _get_top_queries_today(self, cursor, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает наиболее популярные запросы за сегодня
        
        Args:
            cursor: Курсор базы данных
            limit: Максимальное количество результатов
            
        Returns:
            Список словарей с информацией о запросах
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        cursor.execute('''
        SELECT event_data, COUNT(*) as count 
        FROM analytics_events 
        WHERE event_type='query' AND timestamp >= ?
        GROUP BY event_data
        ORDER BY count DESC
        LIMIT ?
        ''', (today_start, limit))
        
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            try:
                event_data = json.loads(row[0])
                query_text = event_data.get('query_text', '')
                
                if query_text:
                    result.append({
                        'query_text': query_text,
                        'count': row[1]
                    })
            except:
                pass
        
        return result
    
    def _get_active_hours_today(self, cursor) -> Dict[int, int]:
        """
        Получает распределение активности по часам за сегодня
        
        Args:
            cursor: Курсор базы данных
            
        Returns:
            Словарь {час: количество_сообщений}
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        cursor.execute('''
        SELECT timestamp FROM analytics_events 
        WHERE timestamp >= ?
        ''', (today_start,))
        
        rows = cursor.fetchall()
        
        result = {i: 0 for i in range(24)}  # Инициализируем все часы
        
        for row in rows:
            try:
                dt = datetime.fromisoformat(row[0])
                hour = dt.hour
                result[hour] += 1
            except:
                pass
        
        return result
    
    def get_stats_for_period(self, days: int = 7) -> Dict[str, Any]:
        """
        Получает статистику за указанный период
        
        Args:
            days: Количество дней
            
        Returns:
            Словарь со статистикой
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                
                # Получаем данные по дням
                period_start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                
                c.execute('''
                SELECT * FROM analytics_daily_stats 
                WHERE date >= ?
                ORDER BY date
                ''', (period_start,))
                
                daily_stats = [dict(row) for row in c.fetchall()]
                
                # Получаем статистику пользователей
                c.execute('''
                SELECT COUNT(*) as user_count FROM analytics_user_stats
                ''')
                
                total_users = c.fetchone()["user_count"]
                
                # Получаем активных пользователей
                active_period_start = (datetime.now() - timedelta(days=days)).isoformat()
                
                c.execute('''
                SELECT COUNT(DISTINCT user_id) as active_users 
                FROM analytics_events 
                WHERE timestamp >= ?
                ''', (active_period_start,))
                
                active_users = c.fetchone()["active_users"]
                
                # Получаем статистику запросов
                c.execute('''
                SELECT COUNT(*) as query_count 
                FROM analytics_events 
                WHERE event_type='query' AND timestamp >= ?
                ''', (active_period_start,))
                
                query_count = c.fetchone()["query_count"]
                
                c.execute('''
                SELECT COUNT(*) as error_count 
                FROM analytics_events 
                WHERE event_type='error' AND timestamp >= ?
                ''', (active_period_start,))
                
                error_count = c.fetchone()["error_count"]
                
                conn.close()
                
                # Формируем результат
                result = {
                    "period_days": days,
                    "total_users": total_users,
                    "active_users": active_users,
                    "query_count": query_count,
                    "error_count": error_count,
                    "daily_stats": daily_stats
                }
                
                return result
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики за период: {e}")
            return {
                "error": str(e),
                "period_days": days,
                "total_users": 0,
                "active_users": 0,
                "query_count": 0,
                "error_count": 0,
                "daily_stats": []
            }
    
    def purge_old_data(self, days: int = 90) -> int:
        """
        Удаляет устаревшие данные из базы
        
        Args:
            days: Количество дней для хранения
            
        Returns:
            Количество удаленных записей
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                
                # Определяем пороговую дату
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                # Удаляем устаревшие события
                c.execute('''
                DELETE FROM analytics_events 
                WHERE timestamp < ?
                ''', (cutoff_date,))
                
                deleted_count = c.rowcount
                
                # Удаляем устаревшую ежедневную статистику
                cutoff_day = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                
                c.execute('''
                DELETE FROM analytics_daily_stats 
                WHERE date < ?
                ''', (cutoff_day,))
                
                deleted_count += c.rowcount
                
                conn.commit()
                conn.close()
                
                logger.info(f"Удалено {deleted_count} устаревших записей аналитики")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Ошибка удаления устаревших данных: {e}")
            return 0
    
    def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Получает общую статистику бота за указанный период
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            Словарь со статистикой
        """
        # Получаем статистику за период
        period_stats = self.get_stats_for_period(days)
        
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                
                # Получаем общее количество уникальных пользователей
                c.execute("SELECT COUNT(DISTINCT user_id) AS total_users FROM analytics_user_stats")
                total_users = c.fetchone()["total_users"]
                
                # Получаем общее количество сообщений
                c.execute("SELECT COUNT(*) AS total_messages FROM analytics_events")
                total_messages = c.fetchone()["total_messages"]
                
                # Получаем общее количество запросов
                c.execute("SELECT COUNT(*) AS total_queries FROM analytics_events WHERE event_type='query'")
                total_queries = c.fetchone()["total_queries"]
                
                # Получаем количество новых пользователей за последний день
                yesterday = (datetime.now() - timedelta(days=1)).isoformat()
                c.execute("SELECT COUNT(*) AS new_users FROM analytics_user_stats WHERE first_seen >= ?", (yesterday,))
                new_users_today = c.fetchone()["new_users"]
                
                # Получаем топ запросов
                c.execute("""
                SELECT query, count FROM analytics_query_stats 
                ORDER BY count DESC LIMIT 5
                """)
                top_queries = [dict(row) for row in c.fetchall()]
                
                conn.close()
                
                # Формируем результат
                result = {
                    "total_users": total_users,
                    "total_messages": total_messages,
                    "total_queries": total_queries,
                    "new_users_today": new_users_today,
                    "top_queries": top_queries,
                    "period_stats": period_stats
                }
                
                return result
                
        except Exception as e:
            logger.error(f"Ошибка получения общей статистики: {e}")
            return {
                "error": str(e),
                "total_users": 0,
                "total_messages": 0,
                "total_queries": 0,
                "new_users_today": 0,
                "top_queries": [],
                "period_stats": period_stats
            }

# Создаем глобальный экземпляр аналитики
analytics = Analytics()
