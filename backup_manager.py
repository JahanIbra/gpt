import os
import shutil
import asyncio
import sqlite3
import tarfile
import tempfile
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import glob
import hashlib

from config import (
    DB_PATH, 
    FAISS_INDEX_PATH, 
    PDF_INDEX_PATH, 
    PDF_DOCS_DIR, 
    BACKUP_DIR,
    BACKUP_RETENTION_DAYS,
    MAX_BACKUPS,
    logger
)

class BackupManager:
    """Класс для управления резервными копиями данных"""
    
    def __init__(self, backup_dir: str = BACKUP_DIR):
        """
        Инициализирует менеджер резервного копирования
        
        Args:
            backup_dir: Директория для хранения резервных копий
        """
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)
    
    async def create_full_backup(self, backup_name: Optional[str] = None) -> str:
        """
        Создает полную резервную копию всех данных
        
        Args:
            backup_name: Имя резервной копии (опционально)
            
        Returns:
            Путь к созданной резервной копии
        """
        try:
            # Если имя не указано, используем текущую дату и время
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"full_backup_{timestamp}"
            
            # Путь к архиву
            backup_path = os.path.join(self.backup_dir, f"{backup_name}.tar.gz")
            
            # Создаем временную директорию для подготовки файлов
            with tempfile.TemporaryDirectory() as temp_dir:
                # Создаем структуру директорий
                os.makedirs(os.path.join(temp_dir, "database"), exist_ok=True)
                os.makedirs(os.path.join(temp_dir, "faiss_index"), exist_ok=True)
                os.makedirs(os.path.join(temp_dir, "pdf_index"), exist_ok=True)
                os.makedirs(os.path.join(temp_dir, "pdf_docs"), exist_ok=True)
                
                # Копируем файл базы данных
                if os.path.exists(DB_PATH):
                    # Создаем копию базы данных
                    db_temp_path = os.path.join(temp_dir, "database", "bot.db")
                    
                    # Безопасно копируем базу данных
                    await self._safe_copy_database(DB_PATH, db_temp_path)
                
                # Копируем индекс FAISS
                if os.path.exists(FAISS_INDEX_PATH):
                    for file in os.listdir(FAISS_INDEX_PATH):
                        source = os.path.join(FAISS_INDEX_PATH, file)
                        target = os.path.join(temp_dir, "faiss_index", file)
                        shutil.copy2(source, target)
                
                # Копируем индекс PDF
                if os.path.exists(PDF_INDEX_PATH):
                    for file in os.listdir(PDF_INDEX_PATH):
                        source = os.path.join(PDF_INDEX_PATH, file)
                        target = os.path.join(temp_dir, "pdf_index", file)
                        shutil.copy2(source, target)
                
                # Копируем PDF-документы
                if os.path.exists(PDF_DOCS_DIR):
                    for file in os.listdir(PDF_DOCS_DIR):
                        if file.endswith(".pdf"):
                            source = os.path.join(PDF_DOCS_DIR, file)
                            target = os.path.join(temp_dir, "pdf_docs", file)
                            shutil.copy2(source, target)
                
                # Создаем метаданные резервной копии
                metadata = {
                    "backup_name": backup_name,
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "files": {
                        "database": os.path.exists(os.path.join(temp_dir, "database", "bot.db")),
                        "faiss_index": len(os.listdir(os.path.join(temp_dir, "faiss_index"))),
                        "pdf_index": len(os.listdir(os.path.join(temp_dir, "pdf_index"))),
                        "pdf_docs": len(os.listdir(os.path.join(temp_dir, "pdf_docs")))
                    }
                }
                
                # Сохраняем метаданные
                with open(os.path.join(temp_dir, "metadata.json"), "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                
                # Создаем архив
                with tarfile.open(backup_path, "w:gz") as tar:
                    tar.add(temp_dir, arcname="")
            
            # Проверяем созданный архив
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Резервная копия не была создана: {backup_path}")
            
            # Очищаем старые резервные копии
            await self.cleanup_old_backups()
            
            logger.info(f"Создана полная резервная копия: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {e}")
            # В случае ошибки удаляем неполный архив, если он был создан
            if backup_name and os.path.exists(os.path.join(self.backup_dir, f"{backup_name}.tar.gz")):
                os.remove(os.path.join(self.backup_dir, f"{backup_name}.tar.gz"))
            raise
    
    async def restore_from_backup(self, backup_path: str) -> bool:
        """
        Восстанавливает данные из резервной копии
        
        Args:
            backup_path: Путь к резервной копии
            
        Returns:
            True если восстановление успешно
        """
        try:
            # Проверяем существование архива
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Резервная копия не найдена: {backup_path}")
            
            # Создаем временную директорию для распаковки
            with tempfile.TemporaryDirectory() as temp_dir:
                # Распаковываем архив
                with tarfile.open(backup_path, "r:gz") as tar:
                    tar.extractall(path=temp_dir)
                
                # Проверяем наличие метаданных
                metadata_path = os.path.join(temp_dir, "metadata.json")
                if not os.path.exists(metadata_path):
                    raise ValueError("Метаданные резервной копии не найдены")
                
                # Загружаем метаданные
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                
                # Проверяем версию
                if metadata.get("version") != "1.0":
                    logger.warning(f"Неизвестная версия резервной копии: {metadata.get('version')}")
                
                # Восстанавливаем базу данных, если она есть в резервной копии
                db_backup_path = os.path.join(temp_dir, "database", "bot.db")
                if os.path.exists(db_backup_path):
                    await self._safe_restore_database(db_backup_path, DB_PATH)
                
                # Восстанавливаем индекс FAISS
                faiss_backup_dir = os.path.join(temp_dir, "faiss_index")
                if os.path.exists(faiss_backup_dir) and os.listdir(faiss_backup_dir):
                    # Очищаем текущий индекс
                    if os.path.exists(FAISS_INDEX_PATH):
                        for file in os.listdir(FAISS_INDEX_PATH):
                            os.remove(os.path.join(FAISS_INDEX_PATH, file))
                    
                    # Копируем индекс из резервной копии
                    for file in os.listdir(faiss_backup_dir):
                        source = os.path.join(faiss_backup_dir, file)
                        target = os.path.join(FAISS_INDEX_PATH, file)
                        shutil.copy2(source, target)
                
                # Восстанавливаем индекс PDF
                pdf_index_backup_dir = os.path.join(temp_dir, "pdf_index")
                if os.path.exists(pdf_index_backup_dir) and os.listdir(pdf_index_backup_dir):
                    # Очищаем текущий индекс
                    if os.path.exists(PDF_INDEX_PATH):
                        for file in os.listdir(PDF_INDEX_PATH):
                            os.remove(os.path.join(PDF_INDEX_PATH, file))
                    
                    # Копируем индекс из резервной копии
                    for file in os.listdir(pdf_index_backup_dir):
                        source = os.path.join(pdf_index_backup_dir, file)
                        target = os.path.join(PDF_INDEX_PATH, file)
                        shutil.copy2(source, target)
                
                # Восстанавливаем PDF-документы
                pdf_docs_backup_dir = os.path.join(temp_dir, "pdf_docs")
                if os.path.exists(pdf_docs_backup_dir) and os.listdir(pdf_docs_backup_dir):
                    # Очищаем текущую директорию
                    if os.path.exists(PDF_DOCS_DIR):
                        for file in os.listdir(PDF_DOCS_DIR):
                            if file.endswith(".pdf"):
                                os.remove(os.path.join(PDF_DOCS_DIR, file))
                    
                    # Копируем документы из резервной копии
                    for file in os.listdir(pdf_docs_backup_dir):
                        if file.endswith(".pdf"):
                            source = os.path.join(pdf_docs_backup_dir, file)
                            target = os.path.join(PDF_DOCS_DIR, file)
                            shutil.copy2(source, target)
            
            logger.info(f"Данные успешно восстановлены из резервной копии: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка восстановления из резервной копии: {e}")
            raise
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """
        Возвращает список доступных резервных копий
        
        Returns:
            Список словарей с информацией о резервных копиях
        """
        try:
            # Получаем список файлов резервных копий
            backup_files = glob.glob(os.path.join(self.backup_dir, "*.tar.gz"))
            
            # Сортируем по времени создания (новые в начале)
            backup_files.sort(key=os.path.getmtime, reverse=True)
            
            backups = []
            for backup_file in backup_files:
                # Получаем информацию о файле
                file_stat = os.stat(backup_file)
                file_size = file_stat.st_size
                file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
                
                # Пытаемся получить дополнительную информацию из архива
                metadata = {}
                try:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        with tarfile.open(backup_file, "r:gz") as tar:
                            # Извлекаем только метаданные
                            metadata_member = None
                            for member in tar.getmembers():
                                if member.name == "metadata.json":
                                    metadata_member = member
                                    break
                            
                            if metadata_member:
                                tar.extract(metadata_member, path=temp_dir)
                                metadata_path = os.path.join(temp_dir, "metadata.json")
                                
                                with open(metadata_path, "r", encoding="utf-8") as f:
                                    metadata = json.load(f)
                except Exception as e:
                    logger.warning(f"Не удалось прочитать метаданные из резервной копии {backup_file}: {e}")
                
                # Формируем информацию о резервной копии
                backup_info = {
                    "path": backup_file,
                    "filename": os.path.basename(backup_file),
                    "size": file_size,
                    "created_at": file_mtime.isoformat(),
                    "metadata": metadata
                }
                backups.append(backup_info)
            
            return backups
            
        except Exception as e:
            logger.error(f"Ошибка получения списка резервных копий: {e}")
            return []
    
    async def cleanup_old_backups(self) -> int:
        """
        Удаляет старые резервные копии
        
        Returns:
            Количество удаленных резервных копий
        """
        try:
            # Получаем список резервных копий
            backups = await self.list_backups()
            
            # Если количество резервных копий меньше максимального, выходим
            if len(backups) <= MAX_BACKUPS:
                return 0
            
            # Вычисляем дату, старше которой нужно удалить резервные копии
            cutoff_date = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)
            
            # Оставляем MAX_BACKUPS самых новых резервных копий и удаляем старые
            deleted_count = 0
            for backup in backups[MAX_BACKUPS:]:
                backup_date = datetime.fromisoformat(backup["created_at"])
                
                # Удаляем, если резервная копия старше cutoff_date
                if backup_date < cutoff_date:
                    os.remove(backup["path"])
                    deleted_count += 1
                    logger.info(f"Удалена старая резервная копия: {backup['filename']}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка очистки старых резервных копий: {e}")
            return 0
    
    async def delete_backup(self, backup_path: str) -> bool:
        """
        Удаляет резервную копию
        
        Args:
            backup_path: Путь к резервной копии
            
        Returns:
            True если удаление успешно
        """
        try:
            # Проверяем существование файла
            if not os.path.exists(backup_path):
                logger.warning(f"Резервная копия не найдена: {backup_path}")
                return False
            
            # Удаляем файл
            os.remove(backup_path)
            logger.info(f"Резервная копия удалена: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления резервной копии: {e}")
            return False
    
    async def _safe_copy_database(self, source_path: str, target_path: str) -> bool:
        """
        Безопасно копирует файл базы данных
        
        Args:
            source_path: Путь к исходному файлу
            target_path: Путь к целевому файлу
            
        Returns:
            True если копирование успешно
        """
        try:
            # Создаем директорию для целевого файла, если она не существует
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Копируем базу данных через sqlite3, чтобы избежать проблем с блокировкой
            source_conn = sqlite3.connect(source_path)
            source_conn.backup(sqlite3.connect(target_path))
            source_conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка копирования базы данных: {e}")
            return False
    
    async def _safe_restore_database(self, source_path: str, target_path: str) -> bool:
        """
        Безопасно восстанавливает файл базы данных
        
        Args:
            source_path: Путь к исходному файлу
            target_path: Путь к целевому файлу
            
        Returns:
            True если восстановление успешно
        """
        try:
            # Создаем директорию для целевого файла, если она не существует
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Создаем резервную копию текущей базы данных, если она существует
            if os.path.exists(target_path):
                backup_path = f"{target_path}.bak"
                shutil.copy2(target_path, backup_path)
            
            # Копируем базу данных через sqlite3, чтобы избежать проблем с блокировкой
            source_conn = sqlite3.connect(source_path)
            
            # Если целевой файл существует, удаляем его
            if os.path.exists(target_path):
                os.remove(target_path)
            
            # Восстанавливаем базу данных
            source_conn.backup(sqlite3.connect(target_path))
            source_conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка восстановления базы данных: {e}")
            
            # Восстанавливаем резервную копию, если она есть и произошла ошибка
            backup_path = f"{target_path}.bak"
            if os.path.exists(backup_path):
                if os.path.exists(target_path):
                    os.remove(target_path)
                shutil.copy2(backup_path, target_path)
                os.remove(backup_path)
            
            return False

# Создаем глобальный экземпляр менеджера резервного копирования
backup_manager = BackupManager()
