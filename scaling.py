import os
import time
import json
import asyncio
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timedelta

from config import logger, APP_ENV

# Флаг использования Redis для кэширования
USE_REDIS = os.getenv("USE_REDIS", "false").lower() in ("true", "1", "t")

# Флаг использования PostgreSQL вместо SQLite
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() in ("true", "1", "t")

# Настройки Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Настройки PostgreSQL
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "bot_db")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "postgres_password")

# Настройки распределенного кэша
CACHE_TTL = int(os.getenv("CACHE_TTL", "86400"))  # 1 день
CACHE_CLEAN_INTERVAL = int(os.getenv("CACHE_CLEAN_INTERVAL", "3600"))  # 1 час

# Настройки пула соединений
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))

class CacheManager:
    """Менеджер кэша с поддержкой Redis"""
    
    def __init__(self):
        """Инициализирует менеджер кэша"""
        self.redis_client = None
        self.local_cache = {}
        self.last_cleanup = time.time()
        
        # Инициализируем Redis, если он используется
        if USE_REDIS:
            try:
                import redis
                self.redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    password=REDIS_PASSWORD,
                    decode_responses=True
                )
                logger.info(f"Подключение к Redis настроено: {REDIS_HOST}:{REDIS_PORT}")
            except ImportError:
                logger.warning("Библиотека redis не установлена, используется локальный кэш")
            except Exception as e:
                logger.error(f"Ошибка подключения к Redis: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Получает значение из кэша
        
        Args:
            key: Ключ кэша
            
        Returns:
            Значение из кэша или None
        """
        # Проверяем, нужно ли очистить устаревшие записи
        await self._maybe_cleanup()
        
        if self.redis_client:
            try:
                # Получаем значение из Redis
                value = self.redis_client.get(key)
                if value:
                    # Обновляем время доступа
                    self.redis_client.expire(key, CACHE_TTL)
                    return json.loads(value)
            except Exception as e:
                logger.error(f"Ошибка получения значения из Redis: {e}")
        
        # Если Redis недоступен или значение не найдено, используем локальный кэш
        if key in self.local_cache:
            item = self.local_cache[key]
            # Проверяем, не устарела ли запись
            if time.time() - item["timestamp"] < CACHE_TTL:
                return item["value"]
            else:
                # Удаляем устаревшую запись
                del self.local_cache[key]
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = CACHE_TTL) -> bool:
        """
        Устанавливает значение в кэше
        
        Args:
            key: Ключ кэша
            value: Значение для сохранения
            ttl: Время жизни в секундах
            
        Returns:
            True, если значение успешно сохранено
        """
        if self.redis_client:
            try:
                # Сохраняем значение в Redis
                return self.redis_client.setex(
                    name=key,
                    time=ttl,
                    value=json.dumps(value)
                )
            except Exception as e:
                logger.error(f"Ошибка сохранения значения в Redis: {e}")
        
        # Если Redis недоступен, используем локальный кэш
        self.local_cache[key] = {
            "value": value,
            "timestamp": time.time()
        }
        return True
    
    async def delete(self, key: str) -> bool:
        """
        Удаляет значение из кэша
        
        Args:
            key: Ключ кэша
            
        Returns:
            True, если значение успешно удалено
        """
        success = True
        
        if self.redis_client:
            try:
                # Удаляем из Redis
                self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"Ошибка удаления значения из Redis: {e}")
                success = False
        
        # Удаляем из локального кэша
        if key in self.local_cache:
            del self.local_cache[key]
        
        return success
    
    async def clear(self) -> bool:
        """
        Очищает весь кэш
        
        Returns:
            True, если кэш успешно очищен
        """
        success = True
        
        if self.redis_client:
            try:
                # Очищаем Redis (удаляем все ключи с префиксом бота)
                keys = self.redis_client.keys("bot:*")
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Ошибка очистки Redis: {e}")
                success = False
        
        # Очищаем локальный кэш
        self.local_cache.clear()
        
        return success
    
    async def _maybe_cleanup(self) -> None:
        """Очищает устаревшие записи, если прошло достаточно времени"""
        current_time = time.time()
        if current_time - self.last_cleanup < CACHE_CLEAN_INTERVAL:
            return
        
        # Обновляем время последней очистки
        self.last_cleanup = current_time
        
        # Очищаем устаревшие записи в локальном кэше
        keys_to_delete = []
        for key, item in self.local_cache.items():
            if current_time - item["timestamp"] >= CACHE_TTL:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.local_cache[key]
        
        if keys_to_delete:
            logger.debug(f"Очищено {len(keys_to_delete)} устаревших записей из локального кэша")

class DBConnectionManager:
    """Менеджер подключений к базе данных с поддержкой пула соединений"""
    
    def __init__(self):
        """Инициализирует менеджер подключений к БД"""
        self.pool = None
        
        # Инициализируем пул соединений, если используется PostgreSQL
        if USE_POSTGRES:
            try:
                import psycopg2
                from psycopg2 import pool
                
                self.pool = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=DB_POOL_SIZE,
                    host=PG_HOST,
                    port=PG_PORT,
                    dbname=PG_DB,
                    user=PG_USER,
                    password=PG_PASSWORD
                )
                logger.info(f"Пул соединений PostgreSQL настроен: {PG_HOST}:{PG_PORT}/{PG_DB}")
            except ImportError:
                logger.warning("Библиотека psycopg2 не установлена")
            except Exception as e:
                logger.error(f"Ошибка создания пула соединений PostgreSQL: {e}")
    
    async def get_connection(self):
        """
        Получает соединение из пула или создает новое соединение SQLite
        
        Returns:
            Соединение с БД
        """
        if USE_POSTGRES and self.pool:
            try:
                return self.pool.getconn()
            except Exception as e:
                logger.error(f"Ошибка получения соединения из пула: {e}")
        
        # Используем SQLite
        import sqlite3
        from config import DB_PATH
        return sqlite3.connect(DB_PATH)
    
    async def release_connection(self, conn):
        """
        Возвращает соединение в пул или закрывает соединение SQLite
        
        Args:
            conn: Соединение с БД
        """
        if USE_POSTGRES and self.pool:
            try:
                self.pool.putconn(conn)
            except Exception as e:
                logger.error(f"Ошибка возврата соединения в пул: {e}")
                try:
                    conn.close()
                except:
                    pass
        else:
            # Закрываем соединение SQLite
            try:
                conn.close()
            except Exception as e:
                logger.error(f"Ошибка закрытия соединения SQLite: {e}")

class LoadBalancer:
    """Простой балансировщик нагрузки для распределения запросов"""
    
    def __init__(self):
        """Инициализирует балансировщик нагрузки"""
        self.services = {}
        self.last_used = {}
        self.locks = {}
    
    def register_service(self, service_name: str, instances: List[Dict[str, Any]]) -> bool:
        """
        Регистрирует сервис с несколькими экземплярами
        
        Args:
            service_name: Имя сервиса
            instances: Список словарей с информацией об экземплярах
            
        Returns:
            True, если сервис успешно зарегистрирован
        """
        self.services[service_name] = instances
        self.last_used[service_name] = -1
        self.locks[service_name] = asyncio.Lock()
        return True
    
    async def get_instance(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Выбирает экземпляр сервиса по методу round-robin
        
        Args:
            service_name: Имя сервиса
            
        Returns:
            Словарь с информацией об экземпляре
        """
        if service_name not in self.services:
            return None
        
        # Используем блокировку для обеспечения потокобезопасности
        async with self.locks[service_name]:
            instances = self.services[service_name]
            
            # Если нет доступных экземпляров, возвращаем None
            if not instances:
                return None
            
            # Выбираем следующий экземпляр по кругу
            self.last_used[service_name] = (self.last_used[service_name] + 1) % len(instances)
            return instances[self.last_used[service_name]]

# Создаем глобальные экземпляры
cache_manager = CacheManager()
db_manager = DBConnectionManager()
load_balancer = LoadBalancer()

# Функция для проверки режима высокой доступности
def is_ha_mode() -> bool:
    """
    Проверяет, включен ли режим высокой доступности
    
    Returns:
        True, если режим включен
    """
    return APP_ENV == "production" and (USE_REDIS or USE_POSTGRES)

# Инициализация компонентов масштабирования
async def init_scaling_components() -> bool:
    """
    Инициализирует компоненты масштабирования
    
    Returns:
        True, если инициализация успешна
    """
    try:
        # Регистрируем модели как сервис (для примера)
        load_balancer.register_service("llm_model", [
            {"id": "primary", "weight": 1.0, "status": "active"},
            {"id": "backup", "weight": 0.5, "status": "standby"}
        ])
        
        logger.info(f"Режим высокой доступности: {'включен' if is_ha_mode() else 'выключен'}")
        
        if USE_REDIS:
            logger.info(f"Распределенный кэш (Redis): включен")
        else:
            logger.info(f"Локальный кэш: включен")
        
        if USE_POSTGRES:
            logger.info(f"База данных: PostgreSQL с пулом соединений (размер: {DB_POOL_SIZE})")
        else:
            logger.info(f"База данных: SQLite")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка инициализации компонентов масштабирования: {e}")
        return False

if __name__ == "__main__":
    # При запуске файла напрямую выполняем тестовую инициализацию
    async def main():
        await init_scaling_components()
        
        test_key = "test:key"
        test_value = {"data": "test_value", "timestamp": datetime.now().isoformat()}
        
        await cache_manager.set(test_key, test_value)
        result = await cache_manager.get(test_key)
        
        print(f"Тест кэша: {'успешно' if result == test_value else 'ошибка'}")
    
    asyncio.run(main())
