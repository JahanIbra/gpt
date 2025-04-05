"""
Модуль для диагностики и мониторинга работы бота.
Предоставляет функции для определения состояния компонентов и выявления проблем.
"""

import os
import sys
import psutil
import logging
import sqlite3
import socket
import json
import time
import platform
import requests
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bot_diagnostics")

# Пути по умолчанию
DEFAULT_CONFIG_PATH = "config.py"
DEFAULT_DB_PATH = "bot.db"
DEFAULT_LOG_PATH = "logs/bot.log"
DEFAULT_FAISS_PATH = "faiss_index"
DEFAULT_PDF_PATH = "pdf_docs"
DEFAULT_PDF_INDEX_PATH = "pdf_index"

def run_full_diagnostics() -> Dict[str, Any]:
    """
    Запускает полную диагностику системы и приложения
    
    Returns:
        Словарь с результатами диагностики
    """
    diagnostics = {
        "timestamp": datetime.now().isoformat(),
        "system": get_system_info(),
        "application": get_application_info(),
        "network": check_network(),
        "errors": [],
        "warnings": [],
        "recommendations": []
    }
    
    # Добавляем рекомендации на основе диагностики
    diagnostics["recommendations"] = generate_recommendations(diagnostics)
    
    return diagnostics

def get_system_info() -> Dict[str, Any]:
    """
    Получает информацию о системе
    
    Returns:
        Словарь с системной информацией
    """
    try:
        # Информация о CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count_physical = psutil.cpu_count(logical=False)
        cpu_count_logical = psutil.cpu_count()
        
        # Информация о памяти
        memory = psutil.virtual_memory()
        
        # Информация о диске
        disk = psutil.disk_usage('/')
        
        # Информация о системе
        system_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
            "cpu": {
                "percent": cpu_percent,
                "cores": cpu_count_physical,
                "logical_cores": cpu_count_logical
            },
            "ram": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "free": disk.free,
                "percent": disk.percent
            },
            "uptime": get_uptime()
        }
        
        return system_info
    except Exception as e:
        logger.error(f"Ошибка получения системной информации: {e}")
        return {
            "error": str(e),
            "platform": platform.platform(),
            "python_version": platform.python_version()
        }

def get_application_info() -> Dict[str, Any]:
    """
    Получает информацию о приложении
    
    Returns:
        Словарь с информацией о приложении
    """
    try:
        result = {
            "env": os.environ.get("APP_ENV", "unknown"),
            "working_directory": os.getcwd(),
            "database": check_database(),
            "model": check_model(),
            "faiss_index": check_faiss_index(),
            "pdf_index": check_pdf_index(),
            "modules": check_required_modules()
        }
        
        return result
    except Exception as e:
        logger.error(f"Ошибка получения информации о приложении: {e}")
        return {"error": str(e)}

def check_database() -> Dict[str, Any]:
    """
    Проверяет наличие и состояние базы данных
    
    Returns:
        Словарь с информацией о базе данных
    """
    try:
        # Ищем путь к базе данных в config.py
        db_path = DEFAULT_DB_PATH
        if os.path.exists(DEFAULT_CONFIG_PATH):
            with open(DEFAULT_CONFIG_PATH, 'r') as f:
                config_content = f.read()
                import re
                match = re.search(r'DB_PATH\s*=\s*["\']([^"\']+)["\']', config_content)
                if match:
                    db_path = match.group(1)
        
        # Проверяем существование файла базы данных
        exists = os.path.exists(db_path)
        
        if not exists:
            return {
                "exists": False,
                "path": db_path,
                "tables": []
            }
        
        # Проверяем структуру базы данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем список таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Получаем размер базы данных
        size = os.path.getsize(db_path)
        
        # Проверяем количество записей в основных таблицах
        table_counts = {}
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                table_counts[table] = count
            except sqlite3.Error:
                table_counts[table] = "error"
        
        conn.close()
        
        return {
            "exists": True,
            "path": db_path,
            "size": size,
            "tables": tables,
            "table_counts": table_counts
        }
        
    except Exception as e:
        logger.error(f"Ошибка проверки базы данных: {e}")
        return {
            "exists": False,
            "error": str(e)
        }

def check_model() -> Dict[str, Any]:
    """
    Проверяет наличие и состояние модели
    
    Returns:
        Словарь с информацией о модели
    """
    try:
        # Ищем путь к модели в config.py
        model_path = ""
        if os.path.exists(DEFAULT_CONFIG_PATH):
            with open(DEFAULT_CONFIG_PATH, 'r') as f:
                config_content = f.read()
                import re
                match = re.search(r'MISTRAL_MODEL_PATH\s*=\s*["\']([^"\']+)["\']', config_content)
                if match:
                    model_path = match.group(1)
        
        if not model_path:
            return {
                "exists": False,
                "message": "Путь к модели не найден в конфигурации"
            }
        
        # Проверяем существование файла модели
        exists = os.path.exists(model_path)
        
        if not exists:
            return {
                "exists": False,
                "path": model_path
            }
        
        # Получаем размер файла модели
        size = os.path.getsize(model_path)
        
        return {
            "exists": True,
            "path": model_path,
            "size": size,
            "size_gb": size / (1024 * 1024 * 1024)
        }
        
    except Exception as e:
        logger.error(f"Ошибка проверки модели: {e}")
        return {
            "exists": False,
            "error": str(e)
        }

def check_faiss_index() -> Dict[str, Any]:
    """
    Проверяет наличие и состояние индекса FAISS
    
    Returns:
        Словарь с информацией об индексе FAISS
    """
    try:
        # Ищем путь к индексу в config.py
        index_path = DEFAULT_FAISS_PATH
        if os.path.exists(DEFAULT_CONFIG_PATH):
            with open(DEFAULT_CONFIG_PATH, 'r') as f:
                config_content = f.read()
                import re
                match = re.search(r'FAISS_INDEX_PATH\s*=\s*["\']([^"\']+)["\']', config_content)
                if match:
                    index_path = match.group(1)
        
        # Проверяем существование директории индекса
        exists = os.path.exists(index_path) and os.path.isdir(index_path)
        
        if not exists:
            return {
                "exists": False,
                "path": index_path
            }
        
        # Получаем список файлов в директории индекса
        files = os.listdir(index_path)
        
        # Проверяем наличие файлов индекса
        has_index_files = any(f.endswith('.faiss') for f in files)
        has_docstore_files = any(f.endswith('.pkl') for f in files)
        
        # Получаем общий размер файлов
        total_size = sum(os.path.getsize(os.path.join(index_path, f)) for f in files if os.path.isfile(os.path.join(index_path, f)))
        
        # Проверяем время последнего изменения
        try:
            last_modified = max(os.path.getmtime(os.path.join(index_path, f)) for f in files if os.path.isfile(os.path.join(index_path, f)))
            last_modified_date = datetime.fromtimestamp(last_modified).isoformat()
        except (ValueError, FileNotFoundError):
            last_modified_date = None
        
        return {
            "exists": True,
            "path": index_path,
            "has_index_files": has_index_files,
            "has_docstore_files": has_docstore_files,
            "files": files,
            "total_size": total_size,
            "last_modified": last_modified_date
        }
        
    except Exception as e:
        logger.error(f"Ошибка проверки индекса FAISS: {e}")
        return {
            "exists": False,
            "error": str(e)
        }

def check_pdf_index() -> Dict[str, Any]:
    """
    Проверяет наличие и состояние индекса PDF
    
    Returns:
        Словарь с информацией об индексе PDF
    """
    try:
        # Ищем пути к PDF файлам и индексу в config.py
        pdf_docs_dir = DEFAULT_PDF_PATH
        pdf_index_dir = DEFAULT_PDF_INDEX_PATH
        
        if os.path.exists(DEFAULT_CONFIG_PATH):
            with open(DEFAULT_CONFIG_PATH, 'r') as f:
                config_content = f.read()
                import re
                match_docs = re.search(r'PDF_DOCS_DIR\s*=\s*["\']([^"\']+)["\']', config_content)
                if match_docs:
                    pdf_docs_dir = match_docs.group(1)
                
                match_index = re.search(r'PDF_INDEX_PATH\s*=\s*["\']([^"\']+)["\']', config_content)
                if match_index:
                    pdf_index_dir = match_index.group(1)
        
        # Проверяем существование директорий
        docs_exists = os.path.exists(pdf_docs_dir) and os.path.isdir(pdf_docs_dir)
        index_exists = os.path.exists(pdf_index_dir) and os.path.isdir(pdf_index_dir)
        
        # Получаем информацию о PDF файлах
        pdf_files = []
        pdf_count = 0
        
        if docs_exists:
            pdf_files = [f for f in os.listdir(pdf_docs_dir) if f.lower().endswith('.pdf')]
            pdf_count = len(pdf_files)
        
        # Получаем информацию об индексах PDF
        pdf_indices = []
        index_count = 0
        
        if index_exists:
            pdf_indices = os.listdir(pdf_index_dir)
            index_count = len(pdf_indices)
        
        return {
            "docs_exists": docs_exists,
            "index_exists": index_exists,
            "docs_path": pdf_docs_dir,
            "index_path": pdf_index_dir,
            "pdf_files": pdf_files,
            "pdf_count": pdf_count,
            "pdf_indices": pdf_indices,
            "index_count": index_count,
            "consistency": pdf_count == index_count
        }
        
    except Exception as e:
        logger.error(f"Ошибка проверки индекса PDF: {e}")
        return {
            "docs_exists": False,
            "index_exists": False,
            "error": str(e)
        }

def check_required_modules() -> Dict[str, bool]:
    """
    Проверяет наличие необходимых модулей
    
    Returns:
        Словарь с информацией о модулях
    """
    required_modules = [
        "langchain", "faiss-cpu", "llama-cpp-python", 
        "transformers", "torch", "sentence_transformers",
        "PyMuPDF", "python-telegram-bot", "PyPDF2", "psutil"
    ]
    
    modules_status = {}
    
    for module in required_modules:
        try:
            __import__(module.replace("-", "_"))
            modules_status[module] = True
        except ImportError:
            modules_status[module] = False
    
    return modules_status

def check_network() -> Dict[str, Any]:
    """
    Проверяет сетевое соединение
    
    Returns:
        Словарь с информацией о сети
    """
    try:
        # Получаем информацию о хосте и IP
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        
        # Проверяем подключение к важным сервисам
        connectivity = {
            "internet": check_internet_connection(),
            "telegram": check_telegram_api(),
            "huggingface": check_huggingface_api()
        }
        
        return {
            "hostname": hostname,
            "ip_address": ip_address,
            "connectivity": connectivity
        }
        
    except Exception as e:
        logger.error(f"Ошибка проверки сети: {e}")
        return {
            "error": str(e)
        }

def check_internet_connection() -> bool:
    """
    Проверяет наличие интернет-соединения
    
    Returns:
        True, если соединение есть
    """
    try:
        # Пытаемся подключиться к Google DNS
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except (socket.timeout, socket.error):
        return False

def check_telegram_api() -> bool:
    """
    Проверяет доступность API Telegram
    
    Returns:
        True, если API доступен
    """
    try:
        response = requests.get("https://api.telegram.org", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def check_huggingface_api() -> bool:
    """
    Проверяет доступность API Hugging Face
    
    Returns:
        True, если API доступен
    """
    try:
        response = requests.get("https://huggingface.co/api/models", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def get_uptime() -> int:
    """
    Получает время работы системы в секундах
    
    Returns:
        Время работы в секундах
    """
    return int(time.time() - psutil.boot_time())

def generate_recommendations(diagnostics: Dict[str, Any]) -> List[str]:
    """
    Генерирует рекомендации на основе результатов диагностики
    
    Args:
        diagnostics: Результаты диагностики
        
    Returns:
        Список рекомендаций
    """
    recommendations = []
    
    # Проверяем системные ресурсы
    system = diagnostics["system"]
    
    if system["ram"]["percent"] > 90:
        recommendations.append("Критически высокое использование памяти. Освободите память или увеличьте объем ОЗУ.")
    elif system["ram"]["percent"] > 75:
        recommendations.append("Высокое использование памяти. Рекомендуется закрыть неиспользуемые приложения.")
    
    if system["disk"]["percent"] > 90:
        recommendations.append("Критически мало свободного места на диске. Освободите дисковое пространство.")
    elif system["disk"]["percent"] > 75:
        recommendations.append("Мало свободного места на диске. Рекомендуется очистить неиспользуемые файлы.")
    
    if system["cpu"]["percent"] > 90:
        recommendations.append("Критически высокая загрузка процессора. Проверьте, не запущены ли лишние процессы.")
    
    # Проверяем компоненты приложения
    app = diagnostics["application"]
    
    if not app["database"]["exists"]:
        recommendations.append("База данных не найдена. Инициализируйте базу данных.")
    
    if not app["model"]["exists"]:
        recommendations.append("Модель не найдена. Загрузите модель по указанному пути.")
    
    if not app["faiss_index"]["exists"] or not app.get("faiss_index", {}).get("has_index_files", False):
        recommendations.append("Индекс FAISS не найден или поврежден. Создайте индекс заново.")
    
    if not app["pdf_index"]["docs_exists"]:
        recommendations.append("Директория PDF документов не найдена. Создайте директорию.")
    
    if not app["pdf_index"]["index_exists"]:
        recommendations.append("Директория индексов PDF не найдена. Создайте директорию.")
    
    if app["pdf_index"]["docs_exists"] and app["pdf_index"]["index_exists"] and not app["pdf_index"]["consistency"]:
        recommendations.append("Количество PDF файлов не соответствует количеству индексов. Обновите индексы PDF.")
    
    # Проверяем сетевое подключение
    network = diagnostics["network"]
    
    if not network.get("connectivity", {}).get("internet", True):
        recommendations.append("Нет подключения к интернету. Проверьте сетевое соединение.")
    
    if not network.get("connectivity", {}).get("telegram", True):
        recommendations.append("Нет доступа к API Telegram. Проверьте сетевое соединение и доступность API.")
    
    if not network.get("connectivity", {}).get("huggingface", True):
        recommendations.append("Нет доступа к Hugging Face API. Проверьте сетевое соединение и доступность API.")
    
    # Проверяем модули
    missing_modules = [m for m, status in app["modules"].items() if not status]
    if missing_modules:
        recommendations.append(f"Отсутствуют необходимые модули: {', '.join(missing_modules)}. Установите их с помощью pip.")
    
    return recommendations

def get_diagnostics_summary(diagnostics: Dict[str, Any]) -> str:
    """
    Возвращает краткую сводку о результатах диагностики
    
    Args:
        diagnostics: Результаты диагностики
        
    Returns:
        Строка с краткой сводкой
    """
    summary = "📊 Диагностика системы:\n\n"
    
    # Системная информация
    system = diagnostics["system"]
    summary += f"💻 Система: {system['platform']}\n"
    summary += f"🔄 CPU: {system['cpu']['percent']}% (ядер: {system['cpu']['cores']})\n"
    summary += f"🧠 RAM: {system['ram']['percent']}% (доступно: {system['ram']['available'] // (1024*1024)} МБ)\n"
    summary += f"💾 Диск: {system['disk']['percent']}% (свободно: {system['disk']['free'] // (1024*1024*1024)} ГБ)\n\n"
    
    # Информация о приложении
    app = diagnostics["application"]
    summary += f"🤖 Окружение: {app['env']}\n"
    summary += f"📂 База данных: {'✅' if app['database']['exists'] else '❌'}\n"
    summary += f"🧠 Модель: {'✅' if app['model']['exists'] else '❌'}\n"
    summary += f"🔍 FAISS индекс: {'✅' if app['faiss_index']['exists'] else '❌'}\n"
    summary += f"📄 PDF индекс: {'✅' if app['pdf_index']['index_exists'] else '❌'}\n\n"
    
    # Сетевое подключение
    network = diagnostics["network"]
    connectivity = network.get("connectivity", {})
    summary += f"🌐 Интернет: {'✅' if connectivity.get('internet', False) else '❌'}\n"
    summary += f"📱 Telegram API: {'✅' if connectivity.get('telegram', False) else '❌'}\n"
    summary += f"🤗 Hugging Face API: {'✅' if connectivity.get('huggingface', False) else '❌'}\n\n"
    
    # Рекомендации
    if diagnostics["recommendations"]:
        summary += "📝 Рекомендации:\n"
        for i, recommendation in enumerate(diagnostics["recommendations"], 1):
            summary += f"{i}. {recommendation}\n"
    
    return summary

if __name__ == "__main__":
    # Запускаем диагностику, если скрипт выполняется напрямую
    results = run_full_diagnostics()
    print(get_diagnostics_summary(results))
    
    # Сохраняем результаты в файл
    with open("diagnostic_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"Полные результаты сохранены в файл diagnostic_results.json")
