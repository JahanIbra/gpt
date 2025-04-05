import os
import re
import hashlib
import sqlite3
import asyncio
import fitz  # PyMuPDF
import time
import json
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import threading

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

from config import (
    DB_PATH, 
    PDF_DOCS_DIR, 
    PDF_INDEX_PATH, 
    PDF_CHUNK_SIZE, 
    PDF_CHUNK_OVERLAP,
    EMBEDDING_MODEL,
    logger
)
from models import get_embeddings
from error_handler import catch_exceptions

# Блокировка для потокобезопасности
_pdf_lock = threading.Lock()
index_lock = threading.Lock()

# Глобальные переменные
pdf_embeddings = None

def init_embeddings() -> HuggingFaceEmbeddings:
    """
    Инициализирует модель для генерации эмбеддингов
    
    Returns:
        Модель эмбеддингов
    """
    global pdf_embeddings
    if pdf_embeddings is None:
        try:
            pdf_embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"}
            )
            logger.info(f"PDF модель эмбеддингов {EMBEDDING_MODEL} успешно инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации модели эмбеддингов для PDF: {e}")
            raise
    return pdf_embeddings

def init_pdf_index() -> bool:
    """
    Инициализирует индекс PDF-документов
    
    Returns:
        True если инициализация прошла успешно
    """
    try:
        # Создаем директории, если их нет
        os.makedirs(PDF_INDEX_PATH, exist_ok=True)
        os.makedirs(PDF_DOCS_DIR, exist_ok=True)
        
        # Инициализируем таблицы в базе данных
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Создаем таблицу для хранения метаданных PDF-файлов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdf_files (
            file_hash TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            page_count INTEGER NOT NULL,
            indexed BOOLEAN NOT NULL DEFAULT 0,
            timestamp TEXT NOT NULL
        )
        ''')
        
        # Создаем таблицу для кэширования результатов поиска в PDF
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdf_cache (
            query_hash TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            result TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        ''')
        
        conn.commit()
        conn.close()
        
        # Проверяем существование индекса
        if not os.path.exists(os.path.join(PDF_INDEX_PATH, "index.faiss")):
            logger.info("PDF индекс не найден, будет создан при добавлении первого документа")
        else:
            logger.info("PDF индекс найден")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка инициализации индекса PDF: {e}")
        return False

def extract_text_from_pdf(pdf_path: str) -> Tuple[str, int]:
    """
    Извлекает текст из PDF-файла
    
    Args:
        pdf_path: Путь к PDF-файлу
        
    Returns:
        Кортеж (извлеченный_текст, количество_страниц)
    """
    try:
        # Открываем PDF-файл
        doc = fitz.open(pdf_path)
        
        # Получаем количество страниц
        page_count = doc.page_count
        
        # Извлекаем текст из всех страниц
        text = ""
        for page_num in range(page_count):
            page = doc.load_page(page_num)
            text += page.get_text()
            text += f"\n--- Страница {page_num + 1} ---\n"
        
        doc.close()
        
        return text, page_count
        
    except Exception as e:
        logger.error(f"Ошибка извлечения текста из PDF {pdf_path}: {e}")
        return "", 0

def chunk_text(text: str, chunk_size: int = PDF_CHUNK_SIZE, chunk_overlap: int = PDF_CHUNK_OVERLAP) -> List[str]:
    """
    Разбивает текст на перекрывающиеся чанки
    
    Args:
        text: Текст для разбиения
        chunk_size: Размер чанка
        chunk_overlap: Размер перекрытия
        
    Returns:
        Список чанков
    """
    try:
        # Создаем экземпляр разделителя текста
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )
        
        # Разбиваем текст на чанки
        chunks = text_splitter.split_text(text)
        
        return chunks
        
    except Exception as e:
        logger.error(f"Ошибка разбиения текста на чанки: {e}")
        return []

async def index_pdf_file(pdf_path: str, pdf_hash: str = None) -> bool:
    """
    Индексирует PDF-файл для векторного поиска
    
    Args:
        pdf_path: Путь к PDF-файлу
        pdf_hash: Хеш PDF-файла (опционально)
        
    Returns:
        True, если индексация успешна
    """
    try:
        # Проверяем существование файла
        if not os.path.exists(pdf_path):
            logger.error(f"PDF-файл не найден: {pdf_path}")
            return False
        
        # Получаем хеш файла, если он не передан
        if not pdf_hash:
            with open(pdf_path, 'rb') as file:
                content = file.read()
                pdf_hash = hashlib.md5(content).hexdigest()
        
        # Получаем имя файла
        filename = os.path.basename(pdf_path)
        
        # Извлекаем текст из PDF
        text, page_count = extract_text_from_pdf(pdf_path)
        
        if not text:
            logger.error(f"Не удалось извлечь текст из PDF: {pdf_path}")
            return False
        
        # Разбиваем текст на чанки
        chunks = chunk_text(text)
        
        if not chunks:
            logger.error(f"Ошибка разбиения текста на чанки: {pdf_path}")
            return False
        
        # Создаем метаданные для чанков
        metadatas = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "source": filename,
                "file_hash": pdf_hash,
                "chunk_id": i,
                "total_chunks": len(chunks),
                "page_count": page_count
            }
            metadatas.append(metadata)
        
        # Создаем векторное хранилище
        embeddings = init_embeddings()
        
        # Создаем директорию для индекса, если она не существует
        index_dir = os.path.join(PDF_INDEX_PATH, pdf_hash)
        os.makedirs(index_dir, exist_ok=True)
        
        # Создаем FAISS индекс для PDF
        vectorstore = FAISS.from_texts(chunks, embeddings, metadatas=metadatas)
        
        # Сохраняем индекс
        vectorstore.save_local(index_dir)
        
        # Обновляем базу данных
        with _pdf_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Проверяем, существует ли запись для этого PDF
            c.execute("SELECT * FROM pdf_files WHERE file_hash=?", (pdf_hash,))
            exists = c.fetchone()
            
            timestamp = datetime.now().isoformat()
            
            if exists:
                # Обновляем существующую запись
                c.execute("""
                UPDATE pdf_files 
                SET indexed=1, page_count=?, timestamp=?
                WHERE file_hash=?
                """, (page_count, timestamp, pdf_hash))
            else:
                # Создаем новую запись
                c.execute("""
                INSERT INTO pdf_files (file_hash, filename, page_count, indexed, timestamp)
                VALUES (?, ?, ?, 1, ?)
                """, (pdf_hash, filename, page_count, timestamp))
            
            conn.commit()
            conn.close()
        
        logger.info(f"PDF-файл успешно проиндексирован: {filename} ({pdf_hash})")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка индексации PDF-файла {pdf_path}: {e}")
        return False

async def process_pdf_file(file_path: str) -> Dict[str, Any]:
    """
    Обрабатывает PDF-файл и добавляет его в систему
    
    Args:
        file_path: Путь к PDF-файлу
        
    Returns:
        Словарь с результатами обработки
    """
    try:
        # Проверяем, что файл существует
        if not os.path.exists(file_path):
            return {"success": False, "error": "Файл не найден"}
        
        # Проверяем, что это PDF-файл
        if not file_path.lower().endswith('.pdf'):
            return {"success": False, "error": "Файл не является PDF-документом"}
        
        # Получаем хеш файла
        with open(file_path, 'rb') as f:
            content = f.read()
            file_hash = hashlib.md5(content).hexdigest()
        
        # Получаем имя файла
        filename = os.path.basename(file_path)
        
        # Проверяем, существует ли уже такой файл в системе
        with _pdf_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            c.execute("SELECT * FROM pdf_files WHERE file_hash=?", (file_hash,))
            existing = c.fetchone()
            
            conn.close()
        
        # Если файл уже существует, возвращаем соответствующее сообщение
        if existing:
            return {
                "success": False,
                "error": "Этот PDF-файл уже существует в системе",
                "already_exists": True,
                "file_hash": file_hash
            }
        
        # Создаем директорию для PDF-файлов, если она не существует
        os.makedirs(PDF_DOCS_DIR, exist_ok=True)
        
        # Копируем файл в директорию PDF-файлов
        target_path = os.path.join(PDF_DOCS_DIR, filename)
        
        # Если файл с таким именем уже существует, добавляем хеш к имени
        if os.path.exists(target_path):
            name, ext = os.path.splitext(filename)
            new_filename = f"{name}_{file_hash[:8]}{ext}"
            target_path = os.path.join(PDF_DOCS_DIR, new_filename)
        
        # Копируем файл
        with open(file_path, 'rb') as src, open(target_path, 'wb') as dst:
            dst.write(src.read())
        
        # Регистрируем файл в базе данных
        with _pdf_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Получаем количество страниц
            doc = fitz.open(target_path)
            page_count = doc.page_count
            doc.close()
            
            # Записываем информацию о файле
            timestamp = datetime.now().isoformat()
            
            c.execute("""
            INSERT INTO pdf_files (file_hash, filename, page_count, indexed, timestamp)
            VALUES (?, ?, ?, 0, ?)
            """, (file_hash, os.path.basename(target_path), page_count, timestamp))
            
            conn.commit()
            conn.close()
        
        # Запускаем процесс индексации в фоновом режиме
        asyncio.create_task(index_pdf_file(target_path, file_hash))
        
        return {
            "success": True,
            "file_hash": file_hash,
            "filename": os.path.basename(target_path),
            "page_count": page_count,
            "indexing_started": True
        }
        
    except Exception as e:
        logger.error(f"Ошибка обработки PDF-файла {file_path}: {e}")
        return {"success": False, "error": str(e)}

async def search_in_pdf_indexed(query: str, top_k: int = 5) -> Optional[str]:
    """
    Выполняет поиск в индексированных PDF-файлах
    
    Args:
        query: Поисковый запрос
        top_k: Количество лучших результатов для включения
        
    Returns:
        Контекст из найденных PDF или None, если ничего не найдено
    """
    try:
        # Проверяем, есть ли индексы PDF
        if not os.path.exists(PDF_INDEX_PATH) or not os.listdir(PDF_INDEX_PATH):
            logger.warning("Нет индексированных PDF-файлов для поиска")
            return None
        
        # Получаем список PDF-индексов
        pdf_indexes = os.listdir(PDF_INDEX_PATH)
        
        # Создаем векторные хранилища для каждого индекса
        embeddings = init_embeddings()
        
        # Создаем список для хранения результатов
        all_documents = []
        
        # Для каждого индекса выполняем поиск
        for pdf_hash in pdf_indexes:
            index_path = os.path.join(PDF_INDEX_PATH, pdf_hash)
            
            # Проверяем, что это директория с индексом
            if not os.path.isdir(index_path):
                continue
            
            try:
                # Загружаем индекс FAISS
                vectorstore = FAISS.load_local(index_path, embeddings)
                
                # Выполняем поиск похожих документов
                docs = vectorstore.similarity_search(query, k=top_k)
                
                # Добавляем документы к результатам
                all_documents.extend(docs)
            except Exception as e:
                logger.error(f"Ошибка поиска в индексе {pdf_hash}: {e}")
                continue
        
        # Если результатов нет, возвращаем None
        if not all_documents:
            return None
        
        # Сортируем все документы по релевантности (если применимо)
        # В данном случае мы берем первые top_k результатов из всех индексов
        context_parts = []
        
        # Берем только top_k наиболее релевантных фрагментов
        for i, doc in enumerate(all_documents[:top_k]):
            source = doc.metadata.get("source", "Неизвестный источник")
            chunk_id = doc.metadata.get("chunk_id", "unknown")
            
            context_part = f"[Фрагмент {i+1} из документа '{source}', часть {chunk_id}]\n{doc.page_content}\n"
            context_parts.append(context_part)
        
        # Объединяем все части контекста
        context = "\n".join(context_parts)
        
        return context
        
    except Exception as e:
        logger.error(f"Ошибка поиска в индексированных PDF: {e}")
        return None

async def update_all_pdf_index() -> bool:
    """
    Обновляет индексы всех PDF-файлов
    
    Returns:
        True, если все индексы успешно обновлены
    """
    try:
        # Проверяем существование директории PDF-файлов
        if not os.path.exists(PDF_DOCS_DIR):
            logger.error(f"Директория PDF-файлов не найдена: {PDF_DOCS_DIR}")
            return False
        
        # Получаем список всех PDF-файлов
        pdf_files = [f for f in os.listdir(PDF_DOCS_DIR) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            logger.warning("Нет PDF-файлов для индексации")
            return True
        
        # Подключаемся к базе данных для получения информации о файлах
        with _pdf_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Получаем информацию о всех файлах
            c.execute("SELECT file_hash, filename FROM pdf_files")
            db_files = {filename: file_hash for file_hash, filename in c.fetchall()}
            
            conn.close()
        
        # Создаем список задач на индексацию
        tasks = []
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(PDF_DOCS_DIR, pdf_file)
            
            # Если файл есть в базе, используем его хеш
            if pdf_file in db_files:
                file_hash = db_files[pdf_file]
                tasks.append(index_pdf_file(pdf_path, file_hash))
            else:
                # Если файла нет в базе, индексируем его без указания хеша
                tasks.append(index_pdf_file(pdf_path))
        
        # Запускаем все задачи параллельно
        results = await asyncio.gather(*tasks)
        
        # Проверяем результаты
        success = all(results)
        
        if success:
            logger.info(f"Все PDF-файлы ({len(pdf_files)}) успешно индексированы")
        else:
            failed_count = results.count(False)
            logger.warning(f"Не удалось индексировать {failed_count} из {len(pdf_files)} PDF-файлов")
        
        return success
        
    except Exception as e:
        logger.error(f"Ошибка обновления индексов PDF: {e}")
        return False

async def delete_pdf_file(file_hash: str) -> bool:
    """
    Удаляет PDF-файл и его индекс из системы
    
    Args:
        file_hash: Хеш файла
        
    Returns:
        True, если удаление успешно
    """
    try:
        # Получаем информацию о файле из базы данных
        with _pdf_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("SELECT filename FROM pdf_files WHERE file_hash=?", (file_hash,))
            result = c.fetchone()
            
            conn.close()
            
            if not result:
                logger.error(f"PDF-файл с хешем {file_hash} не найден в базе данных")
                return False
            
            filename = result["filename"]
        
        # Путь к файлу
        file_path = os.path.join(PDF_DOCS_DIR, filename)
        
        # Путь к индексу
        index_path = os.path.join(PDF_INDEX_PATH, file_hash)
        
        # Удаляем файл, если он существует
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"PDF-файл удален: {file_path}")
        
        # Удаляем индекс, если он существует
        if os.path.exists(index_path) and os.path.isdir(index_path):
            # Удаляем все файлы в директории
            for file in os.listdir(index_path):
                os.remove(os.path.join(index_path, file))
            
            # Удаляем директорию
            os.rmdir(index_path)
            logger.info(f"Индекс PDF-файла удален: {index_path}")
        
        # Удаляем запись из базы данных
        with _pdf_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            c.execute("DELETE FROM pdf_files WHERE file_hash=?", (file_hash,))
            
            # Удаляем связанные записи в кэше PDF
            c.execute("DELETE FROM pdf_cache WHERE event_data LIKE ?", (f'%{file_hash}%',))
            
            conn.commit()
            conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка удаления PDF-файла {file_hash}: {e}")
        return False

async def get_pdf_info(file_hash: str = None) -> Dict[str, Any]:
    """
    Получает информацию о PDF-файле или обо всех файлах
    
    Args:
        file_hash: Хеш файла (опционально, если None - получить информацию о всех файлах)
        
    Returns:
        Словарь с информацией о файле или список словарей с информацией о всех файлах
    """
    try:
        with _pdf_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            if file_hash:
                # Получаем информацию о конкретном файле
                c.execute("SELECT * FROM pdf_files WHERE file_hash=?", (file_hash,))
                result = c.fetchone()
                
                if not result:
                    return {"error": f"PDF-файл с хешем {file_hash} не найден"}
                
                file_info = dict(result)
                
                # Добавляем информацию о файле
                file_path = os.path.join(PDF_DOCS_DIR, file_info["filename"])
                if os.path.exists(file_path):
                    file_info["exists"] = True
                    file_info["size"] = os.path.getsize(file_path)
                else:
                    file_info["exists"] = False
                
                # Добавляем информацию об индексе
                index_path = os.path.join(PDF_INDEX_PATH, file_hash)
                file_info["index_exists"] = os.path.exists(index_path) and os.path.isdir(index_path)
                
                conn.close()
                return file_info
            else:
                # Получаем информацию о всех файлах
                c.execute("SELECT * FROM pdf_files ORDER BY timestamp DESC")
                results = c.fetchall()
                
                files_info = []
                for result in results:
                    file_info = dict(result)
                    
                    # Добавляем информацию о файле
                    file_path = os.path.join(PDF_DOCS_DIR, file_info["filename"])
                    if os.path.exists(file_path):
                        file_info["exists"] = True
                        file_info["size"] = os.path.getsize(file_path)
                    else:
                        file_info["exists"] = False
                    
                    # Добавляем информацию об индексе
                    index_path = os.path.join(PDF_INDEX_PATH, file_info["file_hash"])
                    file_info["index_exists"] = os.path.exists(index_path) and os.path.isdir(index_path)
                    
                    files_info.append(file_info)
                
                conn.close()
                return {"files": files_info, "count": len(files_info)}
        
    except Exception as e:
        logger.error(f"Ошибка получения информации о PDF-файле: {e}")
        return {"error": str(e)}

async def extract_pdf_metadata(file_path: str) -> Dict[str, Any]:
    """
    Извлекает метаданные из PDF-файла
    
    Args:
        file_path: Путь к PDF-файлу
        
    Returns:
        Словарь с метаданными PDF-файла
    """
    try:
        # Проверяем, что файл существует
        if not os.path.exists(file_path):
            return {"error": "Файл не найден"}
        
        # Открываем PDF-файл
        doc = fitz.open(file_path)
        
        # Получаем базовые метаданные
        metadata = {
            "filename": os.path.basename(file_path),
            "size": os.path.getsize(file_path),
            "page_count": doc.page_count,
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "keywords": doc.metadata.get("keywords", ""),
            "creator": doc.metadata.get("creator", ""),
            "producer": doc.metadata.get("producer", ""),
            "creation_date": doc.metadata.get("creationDate", ""),
            "modification_date": doc.metadata.get("modDate", "")
        }
        
        # Получаем информацию о страницах
        pages_info = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text_length = len(page.get_text())
            pages_info.append({
                "page_number": page_num + 1,
                "text_length": text_length
            })
        
        metadata["pages"] = pages_info
        
        doc.close()
        
        return metadata
        
    except Exception as e:
        logger.error(f"Ошибка извлечения метаданных PDF: {e}")
        return {"error": str(e)}
