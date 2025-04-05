import os
import sys
import time
import hashlib
import argparse
from typing import Dict, Any, Optional
import urllib.request
import ssl
import certifi
import asyncio
from tqdm import tqdm

from config import MISTRAL_MODEL_PATH, logger

# Ссылка на модель Mistral 7B
MISTRAL_MODEL_URL = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/mistral-7b-instruct-v0.3.Q4_K_M.gguf"

def calculate_md5(file_path: str) -> str:
    """
    Вычисляет MD5-хеш файла
    
    Args:
        file_path: Путь к файлу
    
    Returns:
        MD5-хеш файла
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

class DownloadProgressBar:
    """Класс для отображения прогресса загрузки"""
    
    def __init__(self, total_size: int):
        """
        Инициализирует индикатор прогресса
        
        Args:
            total_size: Общий размер файла в байтах
        """
        self.pbar = tqdm(total=total_size, unit='B', unit_scale=True, desc="Загрузка модели")
        self.downloaded = 0
    
    def update(self, block_num: int, block_size: int, total_size: int):
        """
        Обновляет прогресс загрузки
        
        Args:
            block_num: Номер блока
            block_size: Размер блока
            total_size: Общий размер файла
        """
        if total_size != self.pbar.total:
            self.pbar.total = total_size
            self.pbar.refresh()
        
        downloaded = block_num * block_size
        if downloaded < total_size:
            self.pbar.update(downloaded - self.downloaded)
            self.downloaded = downloaded
    
    def close(self):
        """Закрывает индикатор прогресса"""
        self.pbar.close()

async def download_mistral_model() -> Dict[str, Any]:
    """
    Асинхронно загружает модель Mistral
    
    Returns:
        Словарь с результатами загрузки
    """
    # Проверяем существование директории для модели
    os.makedirs(os.path.dirname(MISTRAL_MODEL_PATH), exist_ok=True)
    
    # Проверяем, существует ли уже файл модели
    if os.path.exists(MISTRAL_MODEL_PATH):
        logger.info(f"Модель уже загружена: {MISTRAL_MODEL_PATH}")
        file_size = os.path.getsize(MISTRAL_MODEL_PATH)
        return {
            "success": True,
            "filename": os.path.basename(MISTRAL_MODEL_PATH),
            "path": MISTRAL_MODEL_PATH,
            "size": file_size,
            "already_exists": True
        }
    
    # Создаем временное имя файла для загрузки
    temp_file = f"{MISTRAL_MODEL_PATH}.download"
    
    try:
        # Получаем размер файла
        logger.info(f"Получение информации о файле модели: {MISTRAL_MODEL_URL}")
        
        # Настройка SSL-контекста
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Открываем соединение и получаем метаданные файла
        with urllib.request.urlopen(MISTRAL_MODEL_URL, context=ssl_context) as response:
            file_size = int(response.headers.get('content-length', 0))
            logger.info(f"Размер файла модели: {file_size / (1024*1024):.2f} МБ")
        
        # Загружаем файл с отображением прогресса
        logger.info(f"Начинаем загрузку модели в {temp_file}")
        start_time = time.time()
        progress_bar = DownloadProgressBar(file_size)
        
        # Асинхронная загрузка на самом деле запускает синхронный код в отдельном потоке
        # поэтому используем функцию для синхронной загрузки
        urllib.request.urlretrieve(
            MISTRAL_MODEL_URL, 
            temp_file, 
            reporthook=progress_bar.update
        )
        progress_bar.close()
        
        download_time = time.time() - start_time
        logger.info(f"Модель загружена за {download_time:.2f} секунд")
        
        # Перемещаем файл в целевое местоположение
        os.rename(temp_file, MISTRAL_MODEL_PATH)
        logger.info(f"Модель сохранена в {MISTRAL_MODEL_PATH}")
        
        # Проверяем размер загруженного файла
        actual_size = os.path.getsize(MISTRAL_MODEL_PATH)
        if actual_size != file_size and file_size > 0:
            logger.warning(f"Предупреждение: размер загруженного файла ({actual_size}) "
                         f"отличается от ожидаемого ({file_size})")
        
        return {
            "success": True,
            "filename": os.path.basename(MISTRAL_MODEL_PATH),
            "path": MISTRAL_MODEL_PATH,
            "size": actual_size,
            "download_time": download_time,
            "already_exists": False
        }
        
    except Exception as e:
        logger.error(f"Ошибка загрузки модели: {e}")
        
        # Удаляем временный файл в случае ошибки
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        return {
            "success": False,
            "error": str(e)
        }

def download_model_sync() -> Dict[str, Any]:
    """
    Синхронная версия функции загрузки модели
    
    Returns:
        Словарь с результатами загрузки
    """
    return asyncio.run(download_mistral_model())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Загрузка модели Mistral 7B")
    parser.add_argument("--force", action="store_true", help="Принудительная перезагрузка модели")
    args = parser.parse_args()
    
    if args.force and os.path.exists(MISTRAL_MODEL_PATH):
        logger.info(f"Удаление существующего файла модели: {MISTRAL_MODEL_PATH}")
        os.remove(MISTRAL_MODEL_PATH)
    
    logger.info("Запуск загрузки модели...")
    result = download_model_sync()
    
    if result["success"]:
        if result.get("already_exists", False):
            print(f"✅ Модель уже загружена: {result['path']}")
            print(f"   Размер: {result['size'] / (1024*1024):.2f} МБ")
        else:
            print(f"✅ Модель успешно загружена: {result['path']}")
            print(f"   Размер: {result['size'] / (1024*1024):.2f} МБ")
            print(f"   Время загрузки: {result['download_time']:.2f} сек")
    else:
        print(f"❌ Ошибка загрузки модели: {result['error']}")
        sys.exit(1)
