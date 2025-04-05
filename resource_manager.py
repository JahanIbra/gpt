import os
import json
import gc
import psutil
import asyncio
import sqlite3
import tempfile
from typing import Dict, Any, Optional, List
from datetime import datetime

from config import logger, MEMORY_THRESHOLD, DB_PATH
from models import unload_models, is_model_loaded

class ResourceManager:
    """Класс для управления системными ресурсами"""
    
    def __init__(self):
        """Инициализирует менеджер ресурсов"""
        self.memory_threshold = MEMORY_THRESHOLD  # Порог использования памяти (в процентах)
        self.critical_memory_threshold = 95  # Критический порог использования памяти
        self.last_memory_freed = 0  # Время последней очистки памяти
        self.memory_free_cooldown = 60  # Кулдаун между очистками памяти (в секундах)
        self.state_file = "system_state.json"  # Файл для хранения состояния ресурсов
    
    async def check_resources(self) -> Dict[str, Any]:
        """
        Проверяет состояние системных ресурсов
        
        Returns:
            Словарь с информацией о состоянии ресурсов
        """
        # Получаем информацию о памяти
        memory = psutil.virtual_memory()
        
        # Получаем информацию о диске
        disk = psutil.disk_usage('/')
        
        # Получаем информацию о CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_count_physical = psutil.cpu_count(logical=False)
        
        # Получаем информацию о сети
        net_io = psutil.net_io_counters()
        
        # Получаем информацию о текущем процессе
        current_process = psutil.Process(os.getpid())
        process_cpu = current_process.cpu_percent(interval=1)
        process_memory = current_process.memory_info()
        process_threads = current_process.num_threads()
        
        # Получаем температуру CPU, если доступно
        try:
            temps = psutil.sensors_temperatures()
            cpu_temp = temps.get('coretemp', [{'current': 0}])[0]['current'] if 'coretemp' in temps else None
        except (AttributeError, IndexError):
            cpu_temp = None
        
        # Формируем состояние ресурсов
        state = {
            "cpu": {
                "percent": cpu_percent,
                "cores": cpu_count_physical,
                "logical_cores": cpu_count,
                "temperature": cpu_temp
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent,
                "swap_total": psutil.swap_memory().total,
                "swap_used": psutil.swap_memory().used,
                "swap_percent": psutil.swap_memory().percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errors": net_io.errin + net_io.errout
            },
            "process": {
                "cpu_percent": process_cpu,
                "memory_rss": process_memory.rss,
                "memory_vms": process_memory.vms,
                "threads": process_threads,
                "pid": current_process.pid
            },
            "models": {
                "loaded": is_model_loaded(),
                "last_check": datetime.now().isoformat()
            }
        }
        
        # Сохраняем состояние в файл
        self._save_resource_state(state)
        
        return state
    
    async def free_memory(self) -> Dict[str, Any]:
        """
        Освобождает память системы при необходимости
        
        Returns:
            Словарь с результатами операции
        """
        current_time = datetime.now().timestamp()
        
        # Проверяем, не слишком ли часто мы освобождаем память
        if current_time - self.last_memory_freed < self.memory_free_cooldown:
            return {
                "success": False,
                "message": "Memory free on cooldown",
                "time_since_last": current_time - self.last_memory_freed
            }
        
        # Обновляем время последней очистки
        self.last_memory_freed = current_time
        
        # Получаем текущее состояние памяти
        memory = psutil.virtual_memory()
        initial_percent = memory.percent
        
        # Если использование памяти ниже порога, не делаем ничего
        if memory.percent < self.memory_threshold:
            return {
                "success": True,
                "message": "Memory usage below threshold",
                "memory_percent": memory.percent,
                "memory_freed": 0
            }
        
        # Флаг, показывающий, находимся ли мы в критическом состоянии
        is_critical = memory.percent >= self.critical_memory_threshold
        
        # Методы освобождения памяти
        freed_memory = 0
        
        # 1. Сборка мусора
        try:
            gc.collect()
            # Проверяем, сколько памяти было освобождено
            memory_after_gc = psutil.virtual_memory()
            freed_memory += memory.used - memory_after_gc.used
            memory = memory_after_gc
        except Exception as e:
            logger.error(f"Ошибка при сборке мусора: {e}")
        
        # 2. Если модель загружена и память в критическом состоянии, выгружаем модель
        if is_critical and is_model_loaded():
            try:
                memory_before = psutil.virtual_memory().used
                unload_models()
                memory_after = psutil.virtual_memory().used
                
                # Обновляем количество освобожденной памяти
                freed_memory += memory_before - memory_after
                
                logger.warning("Модель выгружена из памяти из-за критического использования памяти")
            except Exception as e:
                logger.error(f"Ошибка при выгрузке модели: {e}")
        
        # 3. Если память все еще в критическом состоянии, очищаем кэш
        if is_critical or memory.percent >= self.memory_threshold:
            try:
                # Очищаем кэш базы данных
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                
                # Получаем текущий размер таблицы кэша
                c.execute("SELECT COUNT(*) FROM cache")
                cache_count_before = c.fetchone()[0]
                
                # Удаляем старые записи из кэша
                c.execute("DELETE FROM cache WHERE last_accessed < datetime('now', '-1 day')")
                
                # Получаем новый размер таблицы кэша
                c.execute("SELECT COUNT(*) FROM cache")
                cache_count_after = c.fetchone()[0]
                
                conn.commit()
                conn.close()
                
                logger.info(f"Очищено {cache_count_before - cache_count_after} записей из кэша")
            except Exception as e:
                logger.error(f"Ошибка при очистке кэша базы данных: {e}")
        
        # Получаем финальное состояние памяти
        final_memory = psutil.virtual_memory()
        
        # Формируем результат операции
        result = {
            "success": True,
            "message": "Memory freed",
            "memory_before": initial_percent,
            "memory_after": final_memory.percent,
            "memory_freed_bytes": freed_memory,
            "memory_freed_mb": freed_memory / (1024 * 1024),
            "critical_state": is_critical
        }
        
        return result
    
    async def monitor_and_manage(self):
        """
        Постоянно мониторит и управляет ресурсами системы
        """
        while True:
            try:
                # Проверяем ресурсы
                state = await self.check_resources()
                
                # Если память превышает порог, освобождаем ее
                if state["memory"]["percent"] > self.memory_threshold:
                    await self.free_memory()
                
                # Ждем перед следующей проверкой
                await asyncio.sleep(60)  # Проверяем каждую минуту
                
            except Exception as e:
                logger.error(f"Ошибка в мониторинге ресурсов: {e}")
                await asyncio.sleep(120)  # Увеличиваем интервал в случае ошибки
    
    def _save_resource_state(self, state: Dict[str, Any]):
        """
        Сохраняет состояние ресурсов в файл
        
        Args:
            state: Словарь с состоянием ресурсов
        """
        try:
            # Добавляем время сохранения
            state["timestamp"] = datetime.now().isoformat()
            
            # Используем временный файл для атомарной записи
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                json.dump(state, temp_file, indent=2)
                temp_path = temp_file.name
            
            # Переименовываем временный файл
            os.replace(temp_path, self.state_file)
            
        except Exception as e:
            logger.error(f"Ошибка сохранения состояния ресурсов: {e}")
    
    async def optimize_for_task(self, task_type: str) -> bool:
        """
        Оптимизирует использование ресурсов для определенной задачи
        
        Args:
            task_type: Тип задачи ("minimal", "balanced", "full")
            
        Returns:
            True, если оптимизация успешна
        """
        try:
            # Проверяем текущее состояние ресурсов
            state = await self.check_resources()
            
            if task_type == "minimal":
                # Минимальное использование ресурсов
                
                # Выгружаем модель, если она загружена
                if is_model_loaded():
                    unload_models()
                
                # Очищаем кэш
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("DELETE FROM cache WHERE last_accessed < datetime('now', '-1 hour')")
                conn.commit()
                conn.close()
                
                # Запускаем сборку мусора
                gc.collect()
                
                logger.info("Система оптимизирована для минимального использования ресурсов")
                
            elif task_type == "balanced":
                # Сбалансированное использование ресурсов
                
                # Проверяем использование памяти
                if state["memory"]["percent"] > 80:
                    # Освобождаем память, если она превышает 80%
                    await self.free_memory()
                
                # Удаляем только очень старый кэш
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("DELETE FROM cache WHERE last_accessed < datetime('now', '-7 day')")
                conn.commit()
                conn.close()
                
                logger.info("Система оптимизирована для сбалансированного использования ресурсов")
                
            elif task_type == "full":
                # Полное использование ресурсов для максимальной производительности
                
                # Убеждаемся, что модель загружена
                if not is_model_loaded():
                    # Здесь мы не загружаем модель напрямую, так как это будет сделано при первом запросе
                    pass
                
                # Сборка мусора для освобождения ненужных объектов
                gc.collect()
                
                logger.info("Система оптимизирована для полного использования ресурсов")
                
            else:
                logger.warning(f"Неизвестный тип задачи для оптимизации: {task_type}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка оптимизации ресурсов для задачи {task_type}: {e}")
            return False
