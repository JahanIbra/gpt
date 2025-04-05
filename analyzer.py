import os
import sqlite3
import json
from typing import Dict, List, Any
from datetime import datetime
import sys
import inspect

from config import DB_PATH, FAISS_INDEX_PATH, PDF_INDEX_PATH, PDF_DOCS_DIR, logger
from langchain_community.vectorstores import FAISS
from models import embeddings

class DataAnalyzer:
    """Класс для анализа данных и статистики бота"""
    
    def __init__(self, db_path: str = DB_PATH):
        """
        Инициализирует анализатор данных
        
        Args:
            db_path: Путь к базе данных
        """
        self.db_path = db_path
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику по пользователям
        
        Returns:
            Словарь со статистикой пользователей
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Получаем количество уникальных пользователей по таблице аналитики
            c.execute("""
            SELECT COUNT(DISTINCT user_id) as user_count 
            FROM analytics_events
            """)
            user_count = c.fetchone()["user_count"]
            
            # Получаем количество сообщений по дням
            c.execute("""
            SELECT 
                DATE(timestamp) as date, 
                COUNT(DISTINCT user_id) as unique_users 
            FROM analytics_events 
            GROUP BY DATE(timestamp) 
            ORDER BY date
            """)
            daily_users = [dict(row) for row in c.fetchall()]
            
            # Получаем активность пользователей
            c.execute("""
            SELECT 
                user_id, 
                COUNT(*) as message_count 
            FROM analytics_events 
            GROUP BY user_id 
            ORDER BY message_count DESC 
            LIMIT 10
            """)
            active_users = [dict(row) for row in c.fetchall()]
            
            # Получаем новых пользователей по дням
            c.execute("""
            SELECT 
                DATE(first_seen) as date, 
                COUNT(*) as new_users 
            FROM analytics_user_stats 
            GROUP BY DATE(first_seen) 
            ORDER BY date
            """)
            new_users = [dict(row) for row in c.fetchall()]
            
            conn.close()
            
            # Формируем результат
            result = {
                "total_users": user_count,
                "daily_users": daily_users,
                "active_users": active_users,
                "new_users": new_users
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики пользователей: {e}")
            return {
                "error": str(e),
                "total_users": 0,
                "daily_users": [],
                "active_users": [],
                "new_users": []
            }
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику по запросам пользователей
        
        Returns:
            Словарь со статистикой запросов
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Получаем общее количество запросов
            c.execute("""
            SELECT COUNT(*) as query_count 
            FROM analytics_events 
            WHERE event_type='query'
            """)
            query_count = c.fetchone()["query_count"]
            
            # Получаем популярные запросы
            c.execute("""
            SELECT 
                query, 
                count, 
                last_used 
            FROM analytics_query_stats 
            ORDER BY count DESC 
            LIMIT 10
            """)
            popular_queries = [dict(row) for row in c.fetchall()]
            
            # Получаем статистику запросов по дням
            c.execute("""
            SELECT 
                DATE(timestamp) as date, 
                COUNT(*) as query_count 
            FROM analytics_events 
            WHERE event_type='query' 
            GROUP BY DATE(timestamp) 
            ORDER BY date
            """)
            daily_queries = [dict(row) for row in c.fetchall()]
            
            # Получаем статистику обратной связи
            c.execute("""
            SELECT 
                event_data, 
                COUNT(*) as count 
            FROM analytics_events 
            WHERE event_type='feedback' 
            GROUP BY event_data
            """)
            feedback_stats = []
            for row in c.fetchall():
                try:
                    # Парсим JSON из event_data
                    event_data = json.loads(row["event_data"])
                    feedback_type = event_data.get("type", "unknown")
                    feedback_stats.append({
                        "type": feedback_type,
                        "count": row["count"]
                    })
                except:
                    pass
            
            conn.close()
            
            # Формируем результат
            result = {
                "total_queries": query_count,
                "popular_queries": popular_queries,
                "daily_queries": daily_queries,
                "feedback_stats": feedback_stats
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики запросов: {e}")
            return {
                "error": str(e),
                "total_queries": 0,
                "popular_queries": [],
                "daily_queries": [],
                "feedback_stats": []
            }
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику по кэшу
        
        Returns:
            Словарь со статистикой кэша
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Получаем общее количество записей в кэше
            c.execute("SELECT COUNT(*) FROM cache")
            cache_count = c.fetchone()[0]
            
            # Получаем общий размер кэша (приблизительно)
            c.execute("SELECT SUM(LENGTH(question) + LENGTH(answer)) FROM cache")
            cache_size = c.fetchone()[0] or 0
            
            # Получаем наиболее часто используемые записи кэша
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("""
            SELECT 
                question_hash, 
                question, 
                last_accessed 
            FROM cache 
            ORDER BY last_accessed DESC 
            LIMIT 10
            """)
            recent_cache = [dict(row) for row in c.fetchall()]
            
            conn.close()
            
            # Формируем результат
            result = {
                "cache_count": cache_count,
                "cache_size_bytes": cache_size,
                "cache_size_mb": cache_size / (1024 * 1024),
                "recent_cache": recent_cache
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики кэша: {e}")
            return {
                "error": str(e),
                "cache_count": 0,
                "cache_size_bytes": 0,
                "cache_size_mb": 0,
                "recent_cache": []
            }
    
    def get_knowledge_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику по базе знаний
        
        Returns:
            Словарь со статистикой базы знаний
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Получаем общее количество записей
            c.execute("SELECT COUNT(*) as knowledge_count FROM knowledge")
            knowledge_count = c.fetchone()["knowledge_count"]
            
            # Получаем количество категорий
            c.execute("SELECT COUNT(*) as category_count FROM knowledge WHERE is_category=1")
            category_count = c.fetchone()["category_count"]
            
            # Получаем статистику по путям
            c.execute("""
            SELECT 
                topic_path, 
                COUNT(*) as count 
            FROM knowledge 
            GROUP BY topic_path 
            ORDER BY count DESC
            """)
            topic_stats = [dict(row) for row in c.fetchall()]
            
            # Получаем средний размер вопросов и ответов
            c.execute("""
            SELECT 
                AVG(LENGTH(question)) as avg_question_length,
                AVG(LENGTH(answer)) as avg_answer_length,
                MAX(LENGTH(question)) as max_question_length,
                MAX(LENGTH(answer)) as max_answer_length
            FROM knowledge
            """)
            size_stats = dict(c.fetchone())
            
            conn.close()
            
            # Формируем результат
            result = {
                "knowledge_count": knowledge_count,
                "category_count": category_count,
                "topic_stats": topic_stats,
                "size_stats": size_stats
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики базы знаний: {e}")
            return {
                "error": str(e),
                "knowledge_count": 0,
                "category_count": 0,
                "topic_stats": [],
                "size_stats": {}
            }
    
    def get_pdf_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику по PDF-документам
        
        Returns:
            Словарь со статистикой PDF
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Получаем общее количество документов
            c.execute("SELECT COUNT(*) as pdf_count FROM pdf_files")
            pdf_count = c.fetchone()["pdf_count"]
            
            # Получаем количество проиндексированных документов
            c.execute("SELECT COUNT(*) as indexed_count FROM pdf_files WHERE indexed=1")
            indexed_count = c.fetchone()["indexed_count"]
            
            # Получаем список документов с информацией
            c.execute("""
            SELECT 
                file_hash, 
                filename, 
                page_count, 
                indexed, 
                timestamp 
            FROM pdf_files 
            ORDER BY timestamp DESC
            """)
            pdf_files = [dict(row) for row in c.fetchall()]
            
            # Получаем статистику по кэшу PDF
            c.execute("SELECT COUNT(*) as pdf_cache_count FROM pdf_cache")
            pdf_cache_count = c.fetchone()["pdf_cache_count"]
            
            conn.close()
            
            # Формируем результат
            result = {
                "pdf_count": pdf_count,
                "indexed_count": indexed_count,
                "pdf_files": pdf_files,
                "pdf_cache_count": pdf_cache_count
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики PDF: {e}")
            return {
                "error": str(e),
                "pdf_count": 0,
                "indexed_count": 0,
                "pdf_files": [],
                "pdf_cache_count": 0
            }
    
    def analyze_questions(self, limit: int = 1000) -> Dict[str, Any]:
        """
        Анализирует вопросы пользователей для выявления паттернов
        
        Args:
            limit: Максимальное количество вопросов для анализа
            
        Returns:
            Словарь с результатами анализа
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Получаем последние вопросы из аналитики
            c.execute("""
            SELECT 
                event_data 
            FROM analytics_events 
            WHERE event_type='query' 
            ORDER BY timestamp DESC 
            LIMIT ?
            """, (limit,))
            
            rows = c.fetchall()
            conn.close()
            
            # Извлекаем тексты вопросов
            questions = []
            for row in rows:
                try:
                    event_data = json.loads(row["event_data"])
                    if "query_text" in event_data:
                        questions.append(event_data["query_text"])
                except:
                    continue
            
            # Если нет вопросов, выходим
            if not questions:
                return {
                    "question_count": 0,
                    "word_stats": {},
                    "question_types": {},
                    "avg_length": 0
                }
            
            # Анализируем вопросы
            words = []
            question_types = Counter()
            question_lengths = []
            
            for question in questions:
                # Подсчет длины вопроса
                question_lengths.append(len(question))
                
                # Токенизация слов (простая реализация)
                words.extend(re.findall(r'\b\w+\b', question.lower()))
                
                # Определение типа вопроса
                if re.search(r'\bчто\b', question.lower()):
                    question_types["что"] += 1
                elif re.search(r'\bкак\b', question.lower()):
                    question_types["как"] += 1
                elif re.search(r'\bпочему\b', question.lower()):
                    question_types["почему"] += 1
                elif re.search(r'\bкогда\b', question.lower()):
                    question_types["когда"] += 1
                elif re.search(r'\bгде\b', question.lower()):
                    question_types["где"] += 1
                elif re.search(r'\bкто\b', question.lower()):
                    question_types["кто"] += 1
                elif re.search(r'\bможно\b|\bмогу\b|\bнужно\b', question.lower()):
                    question_types["разрешение"] += 1
                else:
                    question_types["другое"] += 1
            
            # Считаем статистику по словам
            word_stats = Counter(words).most_common(50)
            
            # Преобразуем в словарь
            word_stats_dict = {word: count for word, count in word_stats}
            
            # Преобразуем счетчик типов вопросов в словарь
            question_types_dict = dict(question_types)
            
            # Формируем результат
            result = {
                "question_count": len(questions),
                "word_stats": word_stats_dict,
                "question_types": question_types_dict,
                "avg_length": sum(question_lengths) / len(question_lengths) if question_lengths else 0
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка анализа вопросов: {e}")
            return {
                "error": str(e),
                "question_count": 0,
                "word_stats": {},
                "question_types": {},
                "avg_length": 0
            }
    
    def generate_statistics_report(self) -> Dict[str, Any]:
        """
        Генерирует полный отчет со статистикой
        
        Returns:
            Словарь с полным отчетом
        """
        # Собираем все статистики
        user_stats = self.get_user_statistics()
        query_stats = self.get_query_statistics()
        cache_stats = self.get_cache_statistics()
        knowledge_stats = self.get_knowledge_statistics()
        pdf_stats = self.get_pdf_statistics()
        question_analysis = self.analyze_questions()
        
        # Формируем время генерации отчета
        timestamp = datetime.now().isoformat()
        
        # Собираем полный отчет
        report = {
            "timestamp": timestamp,
            "user_statistics": user_stats,
            "query_statistics": query_stats,
            "cache_statistics": cache_stats,
            "knowledge_statistics": knowledge_stats,
            "pdf_statistics": pdf_stats,
            "question_analysis": question_analysis
        }
        
        return report
    
    def save_report_to_file(self, filename: str = None) -> str:
        """
        Сохраняет отчет в файл
        
        Args:
            filename: Имя файла для сохранения (опционально)
            
        Returns:
            Путь к сохраненному файлу
        """
        # Генерируем отчет
        report = self.generate_statistics_report()
        
        # Если имя файла не указано, используем метку времени
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"statistics_report_{timestamp}.json"
        
        # Сохраняем отчет в файл
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Отчет со статистикой сохранен в файл: {filename}")
        return filename

# Создаем глобальный экземпляр анализатора
data_analyzer = DataAnalyzer()

if __name__ == "__main__":
    # При запуске файла напрямую, генерируем и сохраняем отчет
    analyzer = DataAnalyzer()
    report_file = analyzer.save_report_to_file()
    print(f"Отчет со статистикой сохранен в файл: {report_file}")
