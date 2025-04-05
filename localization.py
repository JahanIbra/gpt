from typing import Dict, Any, Optional, List
import json
import os
import re
from config import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, logger

class Localizer:
    """Класс для локализации текстовых сообщений"""
    
    def __init__(self, default_language: str = DEFAULT_LANGUAGE):
        """
        Инициализирует локализатор
        
        Args:
            default_language: Язык по умолчанию
        """
        self.default_language = default_language
        self.translations = {}
        self.load_translations()
    
    def load_translations(self):
        """Загружает все доступные переводы"""
        try:
            # Ищем файлы переводов в директории locales
            locales_dir = os.path.join(os.path.dirname(__file__), 'locales')
            
            # Создаем директорию, если она не существует
            if not os.path.exists(locales_dir):
                os.makedirs(locales_dir)
                self._create_default_translations(locales_dir)
            
            # Загружаем все доступные файлы переводов
            for lang in SUPPORTED_LANGUAGES:
                lang_file = os.path.join(locales_dir, f'{lang}.json')
                
                # Если файл перевода не существует, создаем его
                if not os.path.exists(lang_file):
                    if lang == DEFAULT_LANGUAGE:
                        self._create_default_translations(locales_dir)
                    else:
                        # Для других языков копируем файл по умолчанию
                        default_file = os.path.join(locales_dir, f'{DEFAULT_LANGUAGE}.json')
                        if os.path.exists(default_file):
                            with open(default_file, 'r', encoding='utf-8') as f:
                                default_translations = json.load(f)
                            
                            # Создаем новый файл с теми же ключами
                            with open(lang_file, 'w', encoding='utf-8') as f:
                                json.dump(default_translations, f, ensure_ascii=False, indent=2)
                
                # Загружаем переводы
                if os.path.exists(lang_file):
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        self.translations[lang] = json.load(f)
            
            logger.info(f"Загружены переводы для языков: {', '.join(self.translations.keys())}")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки переводов: {e}")
            # Если не удалось загрузить переводы, создаем пустой словарь
            if DEFAULT_LANGUAGE not in self.translations:
                self.translations[DEFAULT_LANGUAGE] = {}
    
    def _create_default_translations(self, locales_dir: str):
        """
        Создает файл перевода для языка по умолчанию
        
        Args:
            locales_dir: Директория с локализациями
        """
        # Базовые переводы для русского языка
        ru_translations = {
            "welcome": "Добро пожаловать! Я бот-ассистент, созданный для ответов на вопросы об исламе.",
            "help_message": "Я могу ответить на ваши вопросы об исламе. Просто напишите свой вопрос, и я постараюсь найти ответ.",
            "not_found": "К сожалению, я не смог найти ответ на ваш вопрос. Попробуйте задать его иначе или обратитесь к имаму.",
            "admin_required": "У вас нет доступа к этой функции. Она доступна только администраторам.",
            "rate_limit": "Слишком много запросов. Пожалуйста, подождите немного перед следующим запросом.",
            "invalid_input": "Введенные данные содержат недопустимый контент.",
            "blocked": "Ваш доступ к боту ограничен. Обратитесь к администратору.",
            "error": "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз позже.",
            "feedback_thanks": "Спасибо за ваш отзыв! Это помогает нам улучшать качество ответов.",
            "ask_again": "Попробуйте задать вопрос другими словами для получения более точного ответа.",
            "categories": {
                "namaz": "Намаз",
                "zakat": "Закят",
                "fasting": "Пост (ураза)",
                "hajj": "Хадж",
                "shahada": "Шахада",
                "nikah": "Никах (брак)",
                "divorce": "Развод",
                "funeral": "Погребение",
                "halal_haram": "Халяль и харам",
                "quran": "Коран",
                "hadith": "Хадисы",
                "aqeedah": "Акыда",
                "fiqh": "Фикх"
            }
        }
        
        # Создаем файл для русского языка
        ru_file = os.path.join(locales_dir, 'ru.json')
        with open(ru_file, 'w', encoding='utf-8') as f:
            json.dump(ru_translations, f, ensure_ascii=False, indent=2)
        
        # Базовые переводы для английского языка
        en_translations = {
            "welcome": "Welcome! I am an assistant bot created to answer questions about Islam.",
            "help_message": "I can answer your questions about Islam. Just write your question, and I will try to find the answer.",
            "not_found": "Unfortunately, I couldn't find an answer to your question. Try asking it differently or consult an imam.",
            "admin_required": "You don't have access to this function. It is only available to administrators.",
            "rate_limit": "Too many requests. Please wait a moment before your next request.",
            "invalid_input": "The entered data contains invalid content.",
            "blocked": "Your access to the bot is restricted. Contact an administrator.",
            "error": "An error occurred while processing your request. Please try again later.",
            "feedback_thanks": "Thank you for your feedback! This helps us improve the quality of answers.",
            "ask_again": "Try asking the question in different words to get a more accurate answer.",
            "categories": {
                "namaz": "Salat (Prayer)",
                "zakat": "Zakat",
                "fasting": "Fasting (Ramadan)",
                "hajj": "Hajj",
                "shahada": "Shahada",
                "nikah": "Nikah (Marriage)",
                "divorce": "Divorce",
                "funeral": "Funeral",
                "halal_haram": "Halal and Haram",
                "quran": "Quran",
                "hadith": "Hadith",
                "aqeedah": "Aqeedah",
                "fiqh": "Fiqh"
            }
        }
        
        # Создаем файл для английского языка, если он поддерживается
        if 'en' in SUPPORTED_LANGUAGES:
            en_file = os.path.join(locales_dir, 'en.json')
            with open(en_file, 'w', encoding='utf-8') as f:
                json.dump(en_translations, f, ensure_ascii=False, indent=2)
    
    def get(self, key: str, lang: str = None, **kwargs) -> str:
        """
        Возвращает локализованную строку по ключу
        
        Args:
            key: Ключ для перевода (может быть вложенным через точку, например 'categories.namaz')
            lang: Код языка (если не указан, используется язык по умолчанию)
            **kwargs: Параметры для форматирования строки
            
        Returns:
            Локализованная строка
        """
        if lang is None:
            lang = self.default_language
        
        if lang not in self.translations:
            lang = self.default_language
        
        # Для вложенных ключей используем рекурсивный поиск
        keys = key.split('.')
        value = self.translations[lang]
        
        try:
            for k in keys:
                value = value[k]
            
            # Если значение - строка, форматируем её с переданными параметрами
            if isinstance(value, str) and kwargs:
                return value.format(**kwargs)
            
            return value
        except (KeyError, TypeError):
            # Если ключ не найден, возвращаем ключ
            logger.warning(f"Ключ локализации не найден: {key} (язык: {lang})")
            return key
    
    def get_all_keys(self, lang: str = None) -> List[str]:
        """
        Возвращает все доступные ключи для указанного языка
        
        Args:
            lang: Код языка (если не указан, используется язык по умолчанию)
            
        Returns:
            Список ключей
        """
        if lang is None:
            lang = self.default_language
        
        if lang not in self.translations:
            lang = self.default_language
        
        def extract_keys(data, prefix=""):
            result = []
            for k, v in data.items():
                key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    result.extend(extract_keys(v, key))
                else:
                    result.append(key)
            return result
        
        return extract_keys(self.translations[lang])
    
    def add_translation(self, key: str, value: str, lang: str = None) -> bool:
        """
        Добавляет новый перевод в словарь
        
        Args:
            key: Ключ для перевода
            value: Переведенная строка
            lang: Код языка (если не указан, используется язык по умолчанию)
            
        Returns:
            True, если перевод успешно добавлен
        """
        if lang is None:
            lang = self.default_language
        
        if lang not in self.translations:
            self.translations[lang] = {}
        
        # Для вложенных ключей создаем необходимую структуру
        keys = key.split('.')
        current = self.translations[lang]
        
        # Проходим по всем ключам кроме последнего и создаем структуру
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        
        # Устанавливаем значение для последнего ключа
        current[keys[-1]] = value
        
        # Сохраняем изменения в файл
        try:
            locales_dir = os.path.join(os.path.dirname(__file__), 'locales')
            lang_file = os.path.join(locales_dir, f'{lang}.json')
            
            with open(lang_file, 'w', encoding='utf-8') as f:
                json.dump(self.translations[lang], f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения перевода: {e}")
            return False

# Создаем глобальный экземпляр локализатора
localizer = Localizer()

def _(key: str, lang: str = None, **kwargs) -> str:
    """
    Функция-помощник для получения локализованной строки
    
    Args:
        key: Ключ для перевода
        lang: Код языка
        **kwargs: Параметры для форматирования строки
        
    Returns:
        Локализованная строка
    """
    return localizer.get(key, lang, **kwargs)
