from typing import Dict, List, Any, Tuple, Optional
import hashlib
import time
import asyncio
from datetime import datetime

from config import logger, ADMIN_IDS
from models import safe_generate, async_generate, is_russian
from vector_search import search_similar_questions
from pdf_handler import search_in_pdf_indexed
from database import get_cached_answer, add_to_cache, load_knowledge
from error_handler import catch_exceptions

async def find_best_answer(
    question: str, 
    variations: List[str] = None, 
    best_query: Optional[str] = None
) -> Tuple[str, bool]:
    """
    Находит наилучший ответ на вопрос, используя различные источники данных
    
    Args:
        question: Исходный вопрос
        variations: Варианты формулировки вопроса
        best_query: Оптимизированный запрос для поиска
        
    Returns:
        Кортеж (ответ, найден_в_кэше)
    """
    try:
        # Проверяем, на русском ли языке вопрос
        if not is_russian(question):
            return "Пожалуйста, задавайте вопросы на русском языке.", False
        
        # Проверяем кэш
        question_hash = hashlib.md5(question.encode('utf-8')).hexdigest()
        if cached := get_cached_answer(question_hash):
            logger.info(f"Найден кэшированный ответ для вопроса: {question[:50]}...")
            return cached["answer"], True
        
        # Поиск в базе знаний через векторный поиск
        search_query = best_query or question
        similar_docs = await search_similar_questions(search_query, k=3)
        
        # Если найдены похожие вопросы в базе знаний
        if similar_docs and similar_docs[0][1] < 0.8:  # Если релевантность высокая (меньше дистанция)
            knowledge = load_knowledge()
            
            # Получаем наиболее релевантный вопрос
            best_match = similar_docs[0][0].page_content
            match_id = similar_docs[0][0].metadata.get("id", "")
            
            # Находим соответствующий ответ в базе знаний
            for item in knowledge:
                # Ищем по ID или по тексту вопроса
                if str(item.get("id", "")) == str(match_id) or item["question"] == best_match:
                    # Форматируем ответ
                    context = f"Исходный вопрос пользователя: {question}\n\n"
                    context += f"Похожий вопрос из базы знаний: {item['question']}\n\n"
                    context += f"Ответ из базы знаний: {item['answer']}"
                    
                    logger.info(f"Найден релевантный ответ в базе знаний для вопроса: {question[:50]}...")
                    # Генерируем ответ на основе контекста
                    answer = await generate_answer(question, context)
                    add_to_cache(question, answer)
                    return answer, False
        
        # Пробуем найти контекст в PDF-документах
        pdf_context = await search_in_pdf_indexed(question)
        if pdf_context:
            logger.info(f"Найден контекст в PDF для вопроса: {question[:50]}...")
            answer = await generate_answer(question, pdf_context)
            add_to_cache(question, answer)
            return answer, False
        
        # Если ничего не нашли, генерируем ответ без контекста
        logger.info(f"Не найдено релевантной информации для вопроса: {question[:50]}...")
        answer = await generate_answer(question)
        if answer:
            add_to_cache(question, answer)
            return answer, False
        
        # Если не удалось сгенерировать ответ
        return "Извините, я не смог найти ответ на ваш вопрос. Попробуйте переформулировать запрос или задать другой вопрос.", False
    
    except Exception as e:
        logger.error(f"Ошибка при поиске ответа: {e}")
        return f"Произошла ошибка при обработке вашего вопроса: {str(e)}", False

@catch_exceptions()
async def generate_answer(question: str, context: Optional[str] = None) -> str:
    """
    Генерирует ответ на вопрос с использованием языковой модели
    
    Args:
        question: Вопрос пользователя
        context: Контекст для генерации ответа (опционально)
        
    Returns:
        Сгенерированный ответ
    """
    try:
        if context:
            prompt = f"""[INST]Ты — искусственный интеллект-ассистент, отвечающий на русском языке.
            
Используй только предоставленный контекст ниже для ответа на вопрос.
Если в контексте недостаточно информации, так и скажи. Не придумывай информацию.
Отвечай структурированно, используй маркированные списки, если это уместно.
Давай четкие и лаконичные ответы.
            
Контекст:
{context}

Вопрос: {question}
Ответ:[/INST]"""
        else:
            prompt = f"""[INST]Ты — искусственный интеллект-ассистент, отвечающий на русском языке.

Вопрос: {question}

Если ты не знаешь ответа на этот вопрос, честно признай это.
Отвечай структурированно и лаконично.
Ответ:[/INST]"""

        # Генерируем ответ
        start_time = time.time()
        result = await async_generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=800,
            stop=["[INST]"]
        )
        generation_time = time.time() - start_time
        
        if "error" in result:
            logger.error(f"Ошибка генерации: {result.get('message', 'Неизвестная ошибка')}")
            return "Извините, произошла ошибка при генерации ответа. Пожалуйста, попробуйте еще раз."
        
        answer = result["choices"][0]["message"]["content"].strip()
        
        # Логируем время генерации
        logger.info(f"Ответ сгенерирован за {generation_time:.2f} сек")
        
        return answer
    
    except Exception as e:
        logger.error(f"Ошибка генерации ответа: {e}")
        return "Извините, произошла ошибка при генерации ответа. Пожалуйста, попробуйте еще раз."

async def search_and_answer(question: str) -> str:
    """
    Ищет информацию и формирует ответ на вопрос
    
    Args:
        question: Вопрос пользователя
        
    Returns:
        Ответ на вопрос
    """
    # Получаем ответ
    answer, is_cached = await find_best_answer(question)
    
    # Форматируем полный ответ
    if is_cached:
        return f"{answer}\n\n(Ответ из кэша)"
    return answer

def generate_russian_answer(query: str, context: str = None, use_llm: bool = True) -> str:
    """
    Синхронная функция для генерации ответа на русском языке
    
    Args:
        query: Вопрос пользователя
        context: Контекст для генерации ответа
        use_llm: Использовать ли LLM для генерации
        
    Returns:
        Сгенерированный ответ
    """
    if not is_russian(query):
        return "Пожалуйста, задавайте вопросы на русском языке."
    
    if not use_llm:
        return "Я могу ответить на этот вопрос, но для этого мне нужно использовать языковую модель."
    
    if context:
        prompt = f"""[INST]Ты — искусственный интеллект-ассистент, отвечающий на русском языке.
        
Используй только предоставленный контекст ниже для ответа на вопрос.
Если в контексте недостаточно информации, так и скажи. Не придумывай информацию.
Отвечай структурированно, используй маркированные списки, если это уместно.
            
Контекст:
{context}

Вопрос: {query}
Ответ:[/INST]"""
    else:
        prompt = f"""[INST]Ты — искусственный интеллект-ассистент, отвечающий на русском языке.

Вопрос: {query}

Если ты не знаешь ответа на этот вопрос, честно признай это.
Ответ:[/INST]"""
    
    # Синхронная генерация
    try:
        result = safe_generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=800
        )
        
        if "error" in result:
            return "Извините, произошла ошибка при генерации ответа. Пожалуйста, попробуйте еще раз."
        
        answer = result["choices"][0]["message"]["content"].strip()
        return answer
        
    except Exception as e:
        logger.error(f"Ошибка синхронной генерации: {e}")
        return "Извините, произошла ошибка при обработке вашего запроса."
