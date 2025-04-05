import os
import hashlib
import asyncio
import threading
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

import numpy as np
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

from config import FAISS_INDEX_PATH, EMBEDDING_MODEL, logger
from database import load_knowledge, get_cached_answer, add_to_cache

# Глобальный объект для доступа к векторному хранилищу
embeddings = None
faiss_index = None
index_lock = threading.Lock()

def init_embeddings() -> HuggingFaceEmbeddings:
    """
    Инициализирует модель для генерации эмбеддингов
    
    Returns:
        Модель эмбеддингов
    """
    global embeddings
    if embeddings is None:
        try:
            embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"}
            )
            logger.info(f"Модель эмбеддингов {EMBEDDING_MODEL} успешно инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации модели эмбеддингов: {e}")
            raise
    return embeddings

async def create_faiss_index() -> bool:
    """
    Создает индекс FAISS из базы знаний
    
    Returns:
        True если создание прошло успешно
    """
    global faiss_index
    try:
        # Получаем данные из базы знаний
        knowledge_data = load_knowledge()
        
        if not knowledge_data:
            logger.warning("База знаний пуста, создается пустой индекс")
            # Создаем пустой индекс
            dummy_text = ["База знаний пуста"]
            embedder = init_embeddings()
            index = FAISS.from_texts(dummy_text, embedder)
            
            # Сохраняем индекс
            os.makedirs(FAISS_INDEX_PATH, exist_ok=True)
            index.save_local(FAISS_INDEX_PATH)
            
            with index_lock:
                faiss_index = index
            
            logger.info("Создан пустой индекс FAISS")
            return True
        
        # Извлекаем вопросы и ответы
        texts = []
        metadatas = []
        
        for item in knowledge_data:
            texts.append(item["question"])
            metadatas.append({"id": item.get("id", ""), "source": "knowledge_base"})
        
        logger.info(f"Создание индекса FAISS для {len(texts)} вопросов")
        
        # Инициализируем модель эмбеддингов
        embedder = init_embeddings()
        
        # Создаем индекс FAISS
        index = FAISS.from_texts(texts, embedder, metadatas=metadatas)
        
        # Сохраняем индекс
        os.makedirs(FAISS_INDEX_PATH, exist_ok=True)
        index.save_local(FAISS_INDEX_PATH)
        
        with index_lock:
            faiss_index = index
        
        logger.info(f"Индекс FAISS успешно создан и сохранен в {FAISS_INDEX_PATH}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка создания индекса FAISS: {e}")
        return False

async def update_faiss_index() -> bool:
    """
    Обновляет индекс FAISS из базы знаний
    
    Returns:
        True если обновление прошло успешно
    """
    try:
        # Удаляем старый индекс, если он существует
        if os.path.exists(os.path.join(FAISS_INDEX_PATH, "index.faiss")):
            os.remove(os.path.join(FAISS_INDEX_PATH, "index.faiss"))
        
        # Создаем новый индекс
        success = await create_faiss_index()
        
        if success:
            logger.info("Индекс FAISS успешно обновлен")
        else:
            logger.error("Не удалось обновить индекс FAISS")
        
        return success
        
    except Exception as e:
        logger.error(f"Ошибка обновления индекса FAISS: {e}")
        return False

def load_faiss_index() -> Optional[FAISS]:
    """
    Загружает индекс FAISS с диска
    
    Returns:
        Загруженный индекс FAISS или None в случае ошибки
    """
    global faiss_index
    
    with index_lock:
        # Если индекс уже загружен, возвращаем его
        if faiss_index is not None:
            return faiss_index
        
        try:
            # Проверяем существование файла индекса
            if not os.path.exists(os.path.join(FAISS_INDEX_PATH, "index.faiss")):
                logger.warning(f"Индекс FAISS не найден в {FAISS_INDEX_PATH}, создаем новый")
                # Запускаем создание индекса в отдельном потоке
                loop = asyncio.new_event_loop()
                loop.run_until_complete(create_faiss_index())
                loop.close()
            
            # Инициализируем модель эмбеддингов
            embedder = init_embeddings()
            
            # Загружаем индекс
            faiss_index = FAISS.load_local(FAISS_INDEX_PATH, embedder, allow_dangerous_deserialization=True)
            
            logger.info(f"Индекс FAISS успешно загружен из {FAISS_INDEX_PATH}")
            return faiss_index
            
        except Exception as e:
            logger.error(f"Ошибка загрузки индекса FAISS: {e}")
            return None

async def search_similar_questions(query: str, k: int = 3) -> List[Tuple[Any, float]]:
    """
    Выполняет поиск похожих вопросов в индексе FAISS
    
    Args:
        query: Текст запроса
        k: Количество результатов
        
    Returns:
        Список кортежей (документ, оценка)
    """
    global faiss_index
    
    try:
        # Хеш запроса для поиска в кэше
        query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()
        
        # Загружаем индекс, если он еще не загружен
        if faiss_index is None:
            faiss_index = load_faiss_index()
            
            # Если загрузка не удалась, пробуем создать новый индекс
            if faiss_index is None:
                await create_faiss_index()
                faiss_index = load_faiss_index()
        
        # Если индекс все еще None, возвращаем пустой список
        if faiss_index is None:
            logger.error("Не удалось загрузить или создать индекс FAISS")
            return []
        
        # Выполняем поиск
        docs_with_scores = faiss_index.similarity_search_with_score(query, k=k)
        
        return docs_with_scores
        
    except Exception as e:
        logger.error(f"Ошибка поиска в индексе FAISS: {e}")
        return []
