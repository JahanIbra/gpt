import psutil
import os
import asyncio
import threading
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Callable

from config import (
    MEMORY_THRESHOLD, 
    RESOURCE_CHECK_INTERVAL, 
    ADMIN_IDS,
    logger,
    APP_ENV
)

class SystemMonitor:
    """Класс для мониторинга системных ресурсов"""
    
    def __init__(self):
        """Инициализирует монитор системных ресурсов"""
        self.running = False
        self.task = None
        self.stats = {}
        self.alerts = set()  # Множество для хранения уже отправленных предупреждений
        self.last_check = datetime.now()
        self.notify_callback = None
        self.lock = threading.Lock()
        self.state_file = os.path.join("data", "system_state.json")
        self._load_state()
    
    def _load_state(self) -> None:
        """Загружает состояние из файла"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.stats = state.get('stats', {})
                    # Преобразуем строки с датами обратно в datetime
                    if 'alerts' in state:
                        self.alerts = set(state['alerts'])
        except Exception as e:
            logger.error(f"Ошибка загрузки состояния системного монитора: {e}")
    
    def _save_state(self) -> None:
        """Сохраняет состояние в файл"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w', encoding='utf-8') as f:
                state = {
                    'stats': self.stats,
                    'alerts': list(self.alerts)
                }
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения состояния системного монитора: {e}")
    
    def set_admin_notify_callback(self, callback: Callable) -> None:
        """
        Устанавливает функцию для уведомления администраторов
        
        Args:
            callback: Функция для отправки уведомлений администраторам
        """
        self.notify_callback = callback
    
    async def start_monitoring(self) -> None:
        """Запускает мониторинг системных ресурсов"""
        if self.running:
            return
            
        self.running = True
        self.task = asyncio.create_task(self._monitor_loop())
        logger.info("Мониторинг системных ресурсов запущен")
    
    async def stop_monitoring(self) -> None:
        """Останавливает мониторинг системных ресурсов"""
        if not self.running:
            return
            
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Мониторинг системных ресурсов остановлен")
    
    async def _monitor_loop(self) -> None:
        """Основной цикл мониторинга"""
        while self.running:
            try:
                # Собираем системные метрики
                metrics = self._collect_metrics()
                
                # Проверяем превышение порогов
                await self._check_thresholds(metrics)
                
                # Обновляем статистику
                self._update_stats(metrics)
                
                # Сохраняем состояние
                self._save_state()
                
                # Ждем до следующей проверки
                await asyncio.sleep(RESOURCE_CHECK_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("Задача мониторинга отменена")
                break
                
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)  # Ждем минуту перед повторной попыткой
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """
        Собирает метрики системы
        
        Returns:
            Словарь с метриками системы
        """
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count(),
                "load": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            },
            "memory": {
                "percent": psutil.virtual_memory().percent,
                "available": psutil.virtual_memory().available,
                "total": psutil.virtual_memory().total
            },
            "disk": {
                "percent": psutil.disk_usage('/').percent,
                "free": psutil.disk_usage('/').free,
                "total": psutil.disk_usage('/').total
            },
            "uptime": {
                "seconds": time.time() - psutil.boot_time(),
                "since": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
        }
        
        return metrics
    
    async def _check_thresholds(self, metrics: Dict[str, Any]) -> None:
        """
        Проверяет превышение пороговых значений и отправляет уведомления
        
        Args:
            metrics: Словарь с метриками системы
        """
        alerts = []
        
        # Проверяем использование памяти
        if metrics["memory"]["percent"] > MEMORY_THRESHOLD:
            alert_key = f"memory_{datetime.now().strftime('%Y%m%d')}"
            if alert_key not in self.alerts:
                alerts.append(f"⚠️ Предупреждение: высокое использование памяти ({metrics['memory']['percent']}%)")
                self.alerts.add(alert_key)
        
        # Проверяем использование диска
        if metrics["disk"]["percent"] > 90:
            alert_key = f"disk_{datetime.now().strftime('%Y%m%d')}"
            if alert_key not in self.alerts:
                alerts.append(f"⚠️ Предупреждение: критически мало места на диске ({metrics['disk']['percent']}%)")
                self.alerts.add(alert_key)
        
        # Проверяем использование CPU
        if metrics["cpu"]["percent"] > 90:
            alert_key = f"cpu_{datetime.now().strftime('%Y%m%d_%H')}"
            if alert_key not in self.alerts:
                alerts.append(f"⚠️ Предупреждение: высокая загрузка CPU ({metrics['cpu']['percent']}%)")
                self.alerts.add(alert_key)
        
        # Отправляем уведомления, если есть
        if alerts and self.notify_callback:
            alert_message = "\n".join(alerts)
            for admin_id in ADMIN_IDS:
                try:
                    await self.notify_callback(admin_id, alert_message)
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления администратору {admin_id}: {e}")
    
    def _update_stats(self, metrics: Dict[str, Any]) -> None:
        """
        Обновляет статистику системы
        
        Args:
            metrics: Словарь с метриками системы
        """
        with self.lock:
            self.stats = {
                "last_update": metrics["timestamp"],
                "system": {
                    "cpu": {
                        "percent": metrics["cpu"]["percent"],
                        "count": metrics["cpu"]["count"],
                        "load": metrics["cpu"]["load"]
                    },
                    "ram": {
                        "percent": metrics["memory"]["percent"],
                        "available_mb": metrics["memory"]["available"] // (1024 * 1024),
                        "total_mb": metrics["memory"]["total"] // (1024 * 1024)
                    },
                    "disk": {
                        "percent": metrics["disk"]["percent"],
                        "free_gb": metrics["disk"]["free"] // (1024 * 1024 * 1024),
                        "total_gb": metrics["disk"]["total"] // (1024 * 1024 * 1024)
                    },
                    "uptime": {
                        "days": metrics["uptime"]["seconds"] // (60 * 60 * 24),
                        "hours": (metrics["uptime"]["seconds"] % (60 * 60 * 24)) // (60 * 60)
                    }
                }
            }
    
    async def get_system_diagnostics(self) -> Dict[str, Any]:
        """
        Возвращает диагностическую информацию о системе
        
        Returns:
            Словарь с диагностикой системы
        """
        # Если нет свежих данных, собираем их
        if not self.stats or "last_update" not in self.stats:
            metrics = self._collect_metrics()
            self._update_stats(metrics)
        
        # Дополнительно собираем информацию о процессах
        try:
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info().rss // (1024 * 1024)  # в MB
            process_cpu = process.cpu_percent()
            process_threads = process.num_threads()
            process_name = process.name()
            
            processes_info = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
                try:
                    # Получаем информацию только для наиболее ресурсоемких процессов
                    if proc.info['memory_percent'] > 1.0 or proc.info['cpu_percent'] > 5.0:
                        processes_info.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'memory_percent': proc.info['memory_percent'],
                            'cpu_percent': proc.info['cpu_percent']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Сортируем по использованию памяти
            processes_info.sort(key=lambda x: x['memory_percent'], reverse=True)
            
            # Берем только топ-5
            processes_info = processes_info[:5]
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о процессах: {e}")
            process_memory = 0
            process_cpu = 0
            process_threads = 0
            process_name = "unknown"
            processes_info = []
        
        # Формируем полную диагностику
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "system": self.stats.get("system", {}),
            "process": {
                "name": process_name,
                "memory_mb": process_memory,
                "cpu_percent": process_cpu,
                "threads": process_threads
            },
            "top_processes": processes_info
        }
        
        return diagnostics
    
    def get_status(self) -> Tuple[bool, str]:
        """
        Возвращает общий статус системы
        
        Returns:
            Кортеж (статус_ок, описание)
        """
        if not self.stats or "system" not in self.stats:
            return False, "Нет данных о состоянии системы"
        
        system = self.stats["system"]
        
        if system["ram"]["percent"] > MEMORY_THRESHOLD:
            return False, f"Критически мало памяти: {system['ram']['percent']}%"
            
        if system["disk"]["percent"] > 90:
            return False, f"Критически мало места на диске: {system['disk']['percent']}%"
            
        if system["cpu"]["percent"] > 90:
            return False, f"Высокая загрузка CPU: {system['cpu']['percent']}%"
            
        return True, "Система работает нормально"

# Создаем глобальный экземпляр монитора системы
system_monitor = SystemMonitor()

async def start_resource_monitoring():
    """
    Запускает мониторинг системных ресурсов
    
    Returns:
        True если мониторинг запущен успешно
    """
    try:
        await system_monitor.start_monitoring()
        logger.info("Запущен мониторинг системных ресурсов")
        return True
    except Exception as e:
        logger.error(f"Ошибка запуска мониторинга системных ресурсов: {e}")
        return False

# Добавляем функцию start_monitoring, отсутствующую в текущей версии файла
async def start_monitoring() -> None:
    """
    Запускает мониторинг системных ресурсов
    (Эта функция является алиасом для start_resource_monitoring для поддержки существующего кода)
    """
    await start_resource_monitoring()
