import os
import re
import asyncio
import threading
from typing import Optional, Dict, Any, List, Tuple, Union
from datetime import datetime

from langchain_community.embeddings import HuggingFaceEmbeddings
from llama_cpp import Llama

from config import (
    LLM_CONTEXT_SIZE,
    LLM_THREADS,
    LLM_GPU_LAYERS,
    LLM_TEMPERATURE,
    EMBEDDING_MODEL,
    logger
)

# Глобальные переменные
llm = None
embeddings = None
model_lock = threading.Lock()

def init_llm(model_path: str) -> bool:
    """
    Инициализирует LLM модель
    
    Args:
        model_path: Путь к файлу модели
        
    Returns:
        True если инициализация успешна
    """
    global llm
    
    # Проверяем, что файл модели существует
    if not os.path.exists(model_path):
        logger.error(f"Файл модели не найден: {model_path}")
        return False
    
    with model_lock:
        if llm is not None:
            logger.info("LLM модель уже инициализирована")
            return True
        
        try:
            logger.info(f"Инициализация LLM модели {model_path}")
            
            # Инициализируем модель
            llm = Llama(
                model_path=model_path,
                n_ctx=LLM_CONTEXT_SIZE,
                n_threads=LLM_THREADS,
                n_gpu_layers=LLM_GPU_LAYERS,
                verbose=False
            )
            
            logger.info("LLM модель успешно инициализирована")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка инициализации LLM модели: {e}")
            return False

def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Возвращает модель для генерации эмбеддингов
    
    Returns:
        Инициализированная модель эмбеддингов
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

def is_russian(text: str, threshold: float = 0.5) -> bool:
    """
    Проверяет, является ли текст русскоязычным
    
    Args:
        text: Текст для проверки
        threshold: Порог доли кириллических символов
        
    Returns:
        True если текст на русском языке
    """
    if not text:
        return False
    
    # Считаем кириллические символы
    cyrillic_count = len(re.findall(r'[а-яА-ЯёЁ]', text))
    
    # Считаем общее количество символов (без пробелов и знаков препинания)
    total_count = len(re.findall(r'[a-zA-Zа-яА-ЯёЁ0-9]', text))
    
    if total_count == 0:
        return False
    
    ratio = cyrillic_count / total_count
    
    return ratio > threshold

async def async_generate(prompt: str, system_message: str = None, temperature: float = None) -> str:
    """
    Асинхронно генерирует ответ на запрос
    
    Args:
        prompt: Текст запроса
        system_message: Системное сообщение (опционально)
        temperature: Температура генерации (опционально)
        
    Returns:
        Сгенерированный текст
    """
    global llm
    
    if llm is None:
        logger.error("LLM модель не инициализирована")
        return "Ошибка: модель не инициализирована"
    
    if temperature is None:
        temperature = LLM_TEMPERATURE
    
    try:
        # Формируем системное сообщение, если оно указано
        messages = []
        
        if system_message:
            messages.append({
                "role": "system",
                "content": system_message
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Создаем отдельный поток для выполнения генерации
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: llm.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=2048
            )
        )
        
        # Извлекаем ответ из JSON
        answer = response['choices'][0]['message']['content']
        
        return answer
        
    except Exception as e:
        logger.error(f"Ошибка генерации ответа: {e}")
        return f"Ошибка генерации ответа: {str(e)}"

def safe_generate(prompt: str, system_message: str = None, temperature: float = None) -> str:
    """
    Синхронно генерирует ответ на запрос
    
    Args:
        prompt: Текст запроса
        system_message: Системное сообщение (опционально)
        temperature: Температура генерации (опционально)
        
    Returns:
        Сгенерированный текст
    """
    global llm
    
    if llm is None:
        logger.error("LLM модель не инициализирована")
        return "Ошибка: модель не инициализирована"
    
    if temperature is None:
        temperature = LLM_TEMPERATURE
    
    try:
        # Формируем системное сообщение, если оно указано
        messages = []
        
        if system_message:
            messages.append({
                "role": "system",
                "content": system_message
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Выполняем генерацию синхронно
        with model_lock:
            response = llm.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=2048
            )
        
        # Извлекаем ответ из JSON
        answer = response['choices'][0]['message']['content']
        
        return answer
        
    except Exception as e:
        logger.error(f"Ошибка генерации ответа: {e}")
        return f"Ошибка генерации ответа: {str(e)}"
