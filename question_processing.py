import re
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Set
import hashlib
import string

from config import logger
from models import get_embeddings, async_generate, safe_generate
from error_handler import catch_exceptions
from enhanced_logging import LoggingContext

async def analyze_and_rephrase_question(question: str) -> Dict[str, Any]:
    """
    Анализирует вопрос и предлагает оптимизированные варианты для поиска
    
    Args:
        question: Вопрос пользователя
    
    Returns:
        Словарь с результатами анализа и оптимизации
    """
    with LoggingContext(logger, operation="analyze_question"):
        # Предварительная обработка вопроса
        cleaned_question = preprocess_question(question)
        
        # Генерируем вариации запроса
        variations = generate_query_variations(cleaned_question)
        
        # Определяем ключевые слова
        keywords = extract_keywords(cleaned_question)
        
        # Формируем оптимальный запрос для поиска
        best_search_query = form_optimal_query(cleaned_question, keywords)
        
        # Определяем категорию вопроса
        category = determine_question_category(cleaned_question)
        
        # Формируем результат
        result = {
            "original": question,
            "cleaned": cleaned_question,
            "variations": variations,
            "keywords": keywords,
            "best_search_query": best_search_query,
            "category": category
        }
        
        return result

def preprocess_question(question: str) -> str:
    """
    Предварительная обработка вопроса для улучшения поиска
    
    Args:
        question: Вопрос пользователя
    
    Returns:
        Обработанный вопрос
    """
    # Приводим к нижнему регистру
    processed = question.lower()
    
    # Удаляем лишние пробелы и специальные символы
    processed = re.sub(r'\s+', ' ', processed)
    processed = processed.strip()
    
    # Убираем специфические маркеры вопросов
    question_markers = [r'^скажите\s+', r'^подскажите\s+', r'^расскажите\s+', r'^объясните\s+']
    for marker in question_markers:
        processed = re.sub(marker, '', processed)
    
    # Заменяем сокращения и общие обороты
    replacements = {
        r'\bпж\b': 'пожалуйста',
        r'\bплз\b': 'пожалуйста',
        r'\bинфу\b': 'информацию',
        r'\bинфа\b': 'информация'
    }
    
    for pattern, replacement in replacements.items():
        processed = re.sub(pattern, replacement, processed)
    
    # Удаляем знаки вопроса в конце и добавляем один, если нужно
    processed = processed.rstrip('?!.,;:')
    if not processed.endswith('?') and is_question(processed):
        processed += '?'
    
    return processed

def is_question(text: str) -> bool:
    """
    Определяет, является ли текст вопросом
    
    Args:
        text: Текст для анализа
    
    Returns:
        True, если текст является вопросом
    """
    # Проверяем наличие вопросительных слов
    question_words = ['кто', 'что', 'где', 'когда', 'почему', 'зачем', 'как', 'какой', 'каким', 'сколько']
    
    for word in question_words:
        if re.search(r'\b' + word + r'\b', text.lower()):
            return True
    
    # Проверяем структуру вопроса (начинается с глагола)
    if re.match(r'^(могу|можно|нужно|должен|является|есть|будет|был|имеет)', text.lower()):
        return True
    
    return False

def generate_query_variations(question: str) -> List[str]:
    """
    Генерирует различные вариации запроса для улучшения поиска
    
    Args:
        question: Вопрос для обработки
    
    Returns:
        Список вариаций запроса
    """
    variations = []
    
    # Добавляем оригинальный вопрос
    variations.append(question)
    
    # Убираем вопросительный знак и добавляем как вариацию
    if question.endswith('?'):
        variations.append(question[:-1])
    
    # Убираем общие вводные фразы
    intro_patterns = [
        r'^скажите,?\s+',
        r'^подскажите,?\s+',
        r'^объясните,?\s+',
        r'^расскажите,?\s+',
        r'^хотел\s+(?:бы|узнать|спросить),?\s+',
        r'^хочу\s+(?:узнать|спросить),?\s+',
        r'^интересует,?\s+',
        r'^можете\s+(?:рассказать|объяснить|сказать),?\s+'
    ]
    
    for pattern in intro_patterns:
        without_intro = re.sub(pattern, '', question, flags=re.IGNORECASE)
        if without_intro != question:
            variations.append(without_intro)
    
    # Преобразуем вопрос в утверждение для некоторых типов вопросов
    if re.match(r'^что\s+такое\s+', question, re.IGNORECASE):
        statement = re.sub(r'^что\s+такое\s+', '', question, flags=re.IGNORECASE)
        variations.append(statement)
    
    # Добавляем короткую версию (только ключевые слова)
    keywords = extract_keywords(question)
    if keywords:
        variations.append(' '.join(keywords))
    
    # Убираем дубликаты и возвращаем уникальные вариации
    unique_variations = list(dict.fromkeys(variations))
    
    return unique_variations

def extract_keywords(text: str) -> List[str]:
    """
    Извлекает ключевые слова из текста
    
    Args:
        text: Текст для обработки
    
    Returns:
        Список ключевых слов
    """
    # Список стоп-слов (частые слова, которые не несут смысловой нагрузки)
    stop_words = {
        'и', 'в', 'на', 'с', 'по', 'к', 'у', 'о', 'от', 'из', 'за', 'для', 'что', 'как',
        'а', 'но', 'же', 'ли', 'бы', 'то', 'не', 'да', 'так', 'это', 'или', 'этот', 'эта',
        'эти', 'этого', 'этой', 'этих', 'его', 'её', 'их', 'все', 'всё', 'всех', 'вся',
        'мне', 'меня', 'я', 'он', 'она', 'оно', 'они', 'мы', 'вы', 'ты', 'кто', 'что', 'который',
        'где', 'когда', 'почему', 'зачем', 'можно', 'нужно', 'надо', 'мочь', 'быть'
    }
    
    # Разбиваем текст на слова и фильтруем стоп-слова
    words = text.lower().replace('?', '').split()
    
    # Удаляем знаки препинания из слов
    words = [word.strip(string.punctuation) for word in words]
    
    # Фильтруем стоп-слова и короткие слова
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Если после фильтрации не осталось ключевых слов, возвращаем все слова длиннее 3 символов
    if not keywords:
        keywords = [word for word in words if len(word) > 3]
    
    return keywords

def form_optimal_query(question: str, keywords: List[str]) -> str:
    """
    Формирует оптимальный запрос для поиска на основе вопроса и ключевых слов
    
    Args:
        question: Исходный вопрос
        keywords: Список ключевых слов
    
    Returns:
        Оптимизированный запрос для поиска
    """
    # Если вопрос короткий (до 5 слов), используем его как есть
    if len(question.split()) <= 5:
        return question
    
    # Для длинных вопросов используем только важные части
    
    # Пытаемся извлечь суть вопроса с помощью шаблонов
    patterns = [
        (r'что\s+такое\s+([\w\s]+?)(?:\?|$)', r'\1'),  # "Что такое X?" -> "X"
        (r'как\s+([\w\s]+?)(?:\?|$)', r'как \1'),      # "Как X?" -> "как X"
        (r'почему\s+([\w\s]+?)(?:\?|$)', r'почему \1') # "Почему X?" -> "почему X"
    ]
    
    for pattern, replacement in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return match.expand(replacement).strip()
    
    # Если не удалось найти шаблон, используем первые 3-5 ключевых слов
    if len(keywords) > 0:
        return ' '.join(keywords[:min(5, len(keywords))])
    
    # Если все не сработало, возвращаем исходный вопрос
    return question

def determine_question_category(question: str) -> str:
    """
    Определяет категорию вопроса
    
    Args:
        question: Вопрос для анализа
    
    Returns:
        Название категории
    """
    # Словарь шаблонов и соответствующих категорий
    category_patterns = [
        (r'\b(?:намаз|салят|молитв|как\s+молиться|время\s+молитв)\b', 'namaz'),
        (r'\b(?:закят|закат|пожертвован|садака|садака)\b', 'zakat'),
        (r'\b(?:пост|ураза|рамадан|говеть|разговение|ифтар|сухур)\b', 'fasting'),
        (r'\b(?:хадж|умра|паломничеств|кааба|мекка|медина)\b', 'hajj'),
        (r'\b(?:шахада|свидетельств|шахад|иман|вера|столп[ыи])\b', 'shahada'),
        (r'\b(?:никах|брак|жених|невеста|махр|свадьб|женитьб|замужеств)\b', 'nikah'),
        (r'\b(?:талак|развод|развест)\b', 'divorce'),
        (r'\b(?:джаназа|похорон|могила|кладбище|умерш|смерт)\b', 'funeral'),
        (r'\b(?:халяль|харам|дозволен|запрещен|грех|можно\s+ли)\b', 'halal_haram'),
        (r'\b(?:коран|аят|сура|таджвид|чтение\s+корана)\b', 'quran'),
        (r'\b(?:хадис|сунна|пророка|мухаммад)\b', 'hadith'),
        (r'\b(?:акыда|вероучени|убеждени|теологи|таухид|иман|единобожи)\b', 'aqeedah'),
        (r'\b(?:фикх|шариат|мазхаб|ханафи|шафии|малики|ханбали|усуль|право)\b', 'fiqh')
    ]
    
    # Проверяем вопрос на соответствие шаблонам
    for pattern, category in category_patterns:
        if re.search(pattern, question, re.IGNORECASE):
            return category
    
    # Если не нашли соответствия, возвращаем общую категорию
    return 'general'

@catch_exceptions()
async def generate_clarification(question: str) -> Optional[str]:
    """
    Генерирует уточняющий вопрос для слишком общих запросов
    
    Args:
        question: Вопрос пользователя
    
    Returns:
        Уточняющий вопрос или None, если уточнение не требуется
    """
    # Если вопрос достаточно длинный, уточнение обычно не требуется
    if len(question.split()) > 7:
        return None
    
    # Шаблон для выявления общих вопросов
    general_patterns = [
        r'^\s*(?:что\s+такое|расскажите\s+про|расскажите\s+о|объясните|опишите)\s+\w+\s*\??$',
        r'^\s*\w+\s+это\s+\w+\s*\??$',
        r'^\s*(?:как|каким\s+образом)\s+\w+\s*\??$'
    ]
    
    is_general = any(re.match(pattern, question, re.IGNORECASE) for pattern in general_patterns)
    
    if not is_general:
        return None
    
    # Генерируем уточняющий вопрос с помощью модели
    prompt = f"""[INST]Проанализируй следующий вопрос на русском языке и определи, является ли он слишком общим.
Если вопрос общий, предложи 1-2 уточняющих вопроса, которые помогут дать более точный ответ. 
Не используй фразу "Ваш вопрос слишком общий", а сразу задай уточняющие вопросы.
Если вопрос уже конкретный и не требует уточнений, верни только слово "Не требуется".

Вопрос: {question}

Уточняющие вопросы или "Не требуется":[/INST]"""
    
    result = await async_generate(
        prompt=prompt,
        temperature=0.7,
        max_tokens=200
    )
    
    if "error" in result:
        logger.error(f"Ошибка генерации уточняющего вопроса: {result.get('message', '')}")
        return None
    
    response = result["choices"][0]["message"]["content"].strip()
    
    # Если модель решила, что уточнение не требуется
    if "не требуется" in response.lower():
        return None
    
    return response

@catch_exceptions()
async def rewrite_question(question: str) -> str:
    """
    Переписывает вопрос в более формальной форме
    
    Args:
        question: Исходный вопрос
    
    Returns:
        Переформулированный вопрос
    """
    prompt = f"""[INST]Переформулируй следующий вопрос, чтобы он был более формальным, 
четким и подходящим для поиска информации. Сохрани исходный смысл.
Убери разговорные элементы, сленг и ошибки, если они есть.
Верни только переформулированный вопрос без дополнительных комментариев.

Исходный вопрос: {question}

Переформулированный вопрос:[/INST]"""
    
    result = await async_generate(
        prompt=prompt,
        temperature=0.3,
        max_tokens=200
    )
    
    if "error" in result:
        logger.error(f"Ошибка переформулирования вопроса: {result.get('message', '')}")
        return question  # Возвращаем исходный вопрос в случае ошибки
    
    rewritten = result["choices"][0]["message"]["content"].strip()
    
    # Если модель вернула пустой результат или слишком короткий
    if not rewritten or len(rewritten) < 5:
        return question
    
    return rewritten
