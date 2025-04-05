import sqlite3
import os
import glob
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple

from config import DB_PATH, logger

class DatabaseMigration:
    """Класс для управления миграциями базы данных"""
    
    def __init__(self, db_path: str = DB_PATH):
        """
        Инициализирует систему миграций
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self.migrations_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migrations')
        self.version_table = 'schema_version'
        
        # Создаем директорию для миграций, если она не существует
        os.makedirs(self.migrations_dir, exist_ok=True)
    
    def _get_current_version(self) -> int:
        """
        Получает текущую версию схемы базы данных
        
        Returns:
            Номер текущей версии
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем, существует ли таблица версий
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self.version_table}'")
            if not cursor.fetchone():
                # Если таблица не существует, считаем версию 0
                conn.close()
                return 0
            
            # Получаем текущую версию
            cursor.execute(f"SELECT version FROM {self.version_table}")
            version = cursor.fetchone()[0]
            conn.close()
            return version
            
        except Exception as e:
            logger.error(f"Ошибка получения текущей версии БД: {e}")
            return 0
    
    def _update_version(self, version: int) -> bool:
        """
        Обновляет версию схемы в базе данных
        
        Args:
            version: Новая версия схемы
            
        Returns:
            True, если обновление успешно
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем, существует ли таблица версий
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self.version_table}'")
            if not cursor.fetchone():
                # Создаем таблицу версий, если она не существует
                cursor.execute(f"CREATE TABLE {self.version_table} (version INTEGER, applied_at TEXT)")
                cursor.execute(f"INSERT INTO {self.version_table} VALUES (0, datetime('now'))")
            
            # Обновляем версию
            cursor.execute(f"UPDATE {self.version_table} SET version = ?, applied_at = datetime('now')", (version,))
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления версии БД: {e}")
            return False
    
    def _get_available_migrations(self) -> List[Tuple[int, str]]:
        """
        Получает список доступных миграций
        
        Returns:
            Список кортежей (версия, путь к файлу)
        """
        migrations = []
        
        # Ищем файлы миграций
        migration_files = glob.glob(os.path.join(self.migrations_dir, "*.sql"))
        
        for file_path in migration_files:
            file_name = os.path.basename(file_path)
            # Имя файла должно быть в формате V{версия}__описание.sql
            if file_name.startswith('V') and '__' in file_name:
                try:
                    version_str = file_name.split('__')[0][1:]
                    version = int(version_str)
                    migrations.append((version, file_path))
                except ValueError:
                    logger.warning(f"Некорректное имя файла миграции: {file_name}")
        
        # Сортируем миграции по версии
        migrations.sort(key=lambda x: x[0])
        return migrations
    
    def _apply_migration(self, migration_path: str) -> bool:
        """
        Применяет миграцию из файла
        
        Args:
            migration_path: Путь к файлу миграции
            
        Returns:
            True, если миграция применена успешно
        """
        try:
            # Читаем SQL из файла
            with open(migration_path, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            # Выполняем SQL
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Разделяем SQL на отдельные команды
            statements = sql.split(';')
            
            for statement in statements:
                if statement.strip():
                    cursor.execute(statement)
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Ошибка применения миграции {migration_path}: {e}")
            return False
    
    def run_migrations(self) -> bool:
        """
        Запускает процесс миграции базы данных
        
        Returns:
            True, если все миграции применены успешно
        """
        try:
            # Получаем текущую версию
            current_version = self._get_current_version()
            logger.info(f"Текущая версия БД: {current_version}")
            
            # Получаем доступные миграции
            migrations = self._get_available_migrations()
            
            # Применяем миграции
            for version, migration_path in migrations:
                if version > current_version:
                    logger.info(f"Применение миграции V{version}: {os.path.basename(migration_path)}")
                    if self._apply_migration(migration_path):
                        # Обновляем версию
                        self._update_version(version)
                        logger.info(f"Миграция V{version} успешно применена")
                    else:
                        logger.error(f"Ошибка применения миграции V{version}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка выполнения миграций: {e}")
            return False
    
    def create_migration(self, description: str, sql: str) -> str:
        """
        Создает новый файл миграции
        
        Args:
            description: Описание миграции
            sql: SQL-запросы миграции
            
        Returns:
            Путь к созданному файлу миграции
        """
        try:
            # Получаем текущую версию
            current_version = self._get_current_version()
            new_version = current_version + 1
            
            # Формируем имя файла
            description = description.replace(' ', '_').lower()
            file_name = f"V{new_version}__{description}.sql"
            file_path = os.path.join(self.migrations_dir, file_name)
            
            # Создаем файл миграции
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"-- Migration: {description}\n")
                f.write(f"-- Version: {new_version}\n")
                f.write(f"-- Created: {datetime.now().isoformat()}\n\n")
                f.write(sql)
            
            logger.info(f"Создана миграция V{new_version}: {description}")
            return file_path
            
        except Exception as e:
            logger.error(f"Ошибка создания миграции: {e}")
            return ""

# Создаем базовые миграции
def create_initial_migrations(migrations_dir: str):
    """
    Создает начальные файлы миграций, если они не существуют
    
    Args:
        migrations_dir: Директория для файлов миграций
    """
    # Создаем директорию, если она не существует
    os.makedirs(migrations_dir, exist_ok=True)
    
    # Проверяем, существуют ли уже файлы миграций
    if glob.glob(os.path.join(migrations_dir, "*.sql")):
        return
    
    # Создаем первую миграцию - основные таблицы
    migration1_path = os.path.join(migrations_dir, "V1__initial_schema.sql")
    with open(migration1_path, 'w', encoding='utf-8') as f:
        f.write("""-- Migration: initial_schema
-- Version: 1
-- Created: 2025-04-02

-- Таблица версий схемы
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- Таблица базы знаний
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    topic_path TEXT DEFAULT "",
    is_category INTEGER DEFAULT 0,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Таблица кэша ответов
CREATE TABLE IF NOT EXISTS cache (
    question_hash TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    last_accessed TEXT NOT NULL
);

-- Таблица PDF-файлов
CREATE TABLE IF NOT EXISTS pdf_files (
    file_hash TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    page_count INTEGER DEFAULT 0,
    indexed INTEGER DEFAULT 0,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Таблица кэша PDF
CREATE TABLE IF NOT EXISTS pdf_cache (
    query_hash TEXT PRIMARY KEY,
    context TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    last_accessed TEXT NOT NULL
);

-- Таблица неотвеченных вопросов
CREATE TABLE IF NOT EXISTS unanswered_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    answered INTEGER DEFAULT 0,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для улучшения производительности
CREATE INDEX IF NOT EXISTS idx_knowledge_question ON knowledge(question);
CREATE INDEX IF NOT EXISTS idx_cache_timestamp ON cache(timestamp);
CREATE INDEX IF NOT EXISTS idx_pdf_files_indexed ON pdf_files(indexed);
CREATE INDEX IF NOT EXISTS idx_unanswered_answered ON unanswered_questions(answered);
""")
    
    # Создаем вторую миграцию - таблицы аналитики
    migration2_path = os.path.join(migrations_dir, "V2__analytics_tables.sql")
    with open(migration2_path, 'w', encoding='utf-8') as f:
        f.write("""-- Migration: analytics_tables
-- Version: 2
-- Created: 2025-04-02

-- Таблица событий аналитики
CREATE TABLE IF NOT EXISTS analytics_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    event_data TEXT,
    timestamp TEXT NOT NULL
);

-- Таблица ежедневной статистики
CREATE TABLE IF NOT EXISTS analytics_daily_stats (
    date TEXT PRIMARY KEY,
    total_messages INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    successful_queries INTEGER DEFAULT 0,
    failed_queries INTEGER DEFAULT 0,
    stats_data TEXT
);

-- Таблица статистики пользователей
CREATE TABLE IF NOT EXISTS analytics_user_stats (
    user_id INTEGER PRIMARY KEY,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    total_messages INTEGER DEFAULT 0,
    successful_queries INTEGER DEFAULT 0,
    failed_queries INTEGER DEFAULT 0,
    user_data TEXT
);

-- Таблица статистики запросов
CREATE TABLE IF NOT EXISTS analytics_query_stats (
    query_hash TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    count INTEGER DEFAULT 0,
    last_used TEXT NOT NULL
);

-- Индексы для аналитики
CREATE INDEX IF NOT EXISTS idx_events_user_id ON analytics_events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON analytics_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON analytics_daily_stats(date);
CREATE INDEX IF NOT EXISTS idx_user_stats_last_seen ON analytics_user_stats(last_seen);
""")

# Функция для запуска миграций
def run_migrations() -> bool:
    """
    Запускает процесс миграции базы данных
    
    Returns:
        True, если миграции выполнены успешно
    """
    try:
        migration_manager = DatabaseMigration()
        
        # Создаем начальные миграции, если нужно
        create_initial_migrations(migration_manager.migrations_dir)
        
        # Запускаем миграции
        success = migration_manager.run_migrations()
        if success:
            logger.info("Миграции выполнены успешно")
        else:
            logger.error("Ошибка выполнения миграций")
        
        return success
        
    except Exception as e:
        logger.error(f"Неожиданная ошибка при выполнении миграций: {e}")
        return False

if __name__ == "__main__":
    # При запуске файла напрямую запускаем миграции
    run_migrations()
