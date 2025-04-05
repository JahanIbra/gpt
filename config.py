import os
import sys
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
from pathlib import Path

# Загружаем переменные окружения из .env файла
load_dotenv()

# Базовые настройки
BASE_DIR = os.getenv("BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
APP_ENV = os.getenv("APP_ENV", "development")  # development, testing, production

# Настройка логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(stream=sys.stdout)
    ]
)
logger = logging.getLogger("bot")

# Telegram Bot
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN and APP_ENV != "testing":
    logger.error("TELEGRAM_TOKEN не найден в переменных окружения")
    
# Преобразуем строку с ID администраторов в список целых чисел
ADMIN_IDS = []
admin_ids_str = os.getenv("ADMIN_IDS", "")
if admin_ids_str:
    ADMIN_IDS = [int(admin_id.strip()) for admin_id in admin_ids_str.split(",") if admin_id.strip()]

# Пути к файлам и директориям
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "data", "bot.db"))
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", os.path.join(BASE_DIR, "data", "faiss_index"))
PDF_INDEX_PATH = os.getenv("PDF_INDEX_PATH", os.path.join(BASE_DIR, "data", "pdf_index"))
PDF_DOCS_DIR = os.getenv("PDF_DOCS_DIR", os.path.join(BASE_DIR, "data", "pdf_docs"))
MISTRAL_MODEL_PATH = os.getenv("MISTRAL_MODEL_PATH", "/root/mistral-7b-instruct-v0.3.Q4_K_M.gguf")
BACKUP_DIR = os.getenv("BACKUP_DIR", os.path.join(BASE_DIR, "backups"))

# Создаем необходимые директории
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(FAISS_INDEX_PATH, exist_ok=True)
os.makedirs(PDF_INDEX_PATH, exist_ok=True)
os.makedirs(PDF_DOCS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(MISTRAL_MODEL_PATH), exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# Настройки LLM
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
LLM_CONTEXT_SIZE = int(os.getenv("LLM_CONTEXT_SIZE", "4096"))
LLM_THREADS = int(os.getenv("LLM_THREADS", "6"))
LLM_GPU_LAYERS = int(os.getenv("LLM_GPU_LAYERS", "0"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))  # Значение температуры для генерации текста (0.0 - 1.0)

# Настройки PDF
PDF_CHUNK_SIZE = int(os.getenv("PDF_CHUNK_SIZE", "1000"))
PDF_CHUNK_OVERLAP = int(os.getenv("PDF_CHUNK_OVERLAP", "200"))

# Настройки мониторинга системы
MEMORY_THRESHOLD = float(os.getenv("MEMORY_THRESHOLD", "80.0"))
RESOURCE_CHECK_INTERVAL = int(os.getenv("RESOURCE_CHECK_INTERVAL", "300"))

# Настройки резервного копирования
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "7"))
MAX_BACKUPS = int(os.getenv("MAX_BACKUPS", "5"))

# Защита от флуда
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "5"))  # Количество сообщений
RATE_LIMIT_TIME = int(os.getenv("RATE_LIMIT_TIME", "60"))  # Период в секундах

# Локализация
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ru")
SUPPORTED_LANGUAGES = ["ru", "en"]

# Логируем основные настройки
logger.info(f"Среда выполнения: {APP_ENV}")
logger.info(f"Уровень логирования: {LOG_LEVEL}")
logger.info(f"База данных: {DB_PATH}")
logger.info(f"Модель: {MISTRAL_MODEL_PATH}")
