from typing import Dict, List, Any, Optional, Tuple
import asyncio
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

from config import logger, ADMIN_IDS
from admin_utils import (
    admin_base_menu,
    handle_admin_db_callback
)
from admin_messaging import (
    start_message_composition,
    handle_broadcast_message,
    handle_broadcast_button
)

async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает панель администратора"""
    # Проверяем, что пользователь администратор
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к панели администратора.")
        return
    
    # Формируем кнопки панели администратора
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🗃️ Управление базами данных", callback_data="admin_db")],
        [InlineKeyboardButton("🔄 Системные операции", callback_data="admin_system")],
        [InlineKeyboardButton("📣 Сообщение пользователям", callback_data="admin_broadcast")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение с панелью администратора
    await update.message.reply_text(
        "👨‍💼 <b>Панель администратора</b>\n\n"
        "Выберите нужный раздел:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

def register_handlers(application: Application) -> None:
    """Регистрирует обработчики команд и сообщений"""
    # Команды администратора
    application.add_handler(CommandHandler("admin", handle_admin_panel, filters=filters.User(user_id=ADMIN_IDS)))
    
    # Обработчики для админ-панели
    application.add_handler(CallbackQueryHandler(handle_admin_db_callback, pattern=r"^admin_db"))
    application.add_handler(CallbackQueryHandler(handle_broadcast_button, pattern=r"^broadcast_"))
    
    # Другие обработчики
    # ...
from typing import Dict, List, Any, Optional, Tuple
import asyncio
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

from config import logger, ADMIN_IDS
from admin_utils import (
    admin_base_menu,
    handle_admin_db_callback
)
from admin_messaging import (
    start_message_composition,
    handle_broadcast_message,
    handle_broadcast_button
)

# Переименовываем функцию с admin_panel на handle_admin_panel
async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает панель администратора"""
    # Проверяем, что пользователь администратор
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к панели администратора.")
        return
    
    # Формируем кнопки панели администратора
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🗃️ Управление базами данных", callback_data="admin_db")],
        [InlineKeyboardButton("🔄 Системные операции", callback_data="admin_system")],
        [InlineKeyboardButton("📣 Сообщение пользователям", callback_data="admin_broadcast")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение с панелью администратора
    await update.message.reply_text(
        "👨‍💼 <b>Панель администратора</b>\n\n"
        "Выберите нужный раздел:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

def register_handlers(application: Application) -> None:
    """Регистрирует обработчики команд и сообщений"""
    # Команды администратора
    application.add_handler(CommandHandler("admin", handle_admin_panel, filters=filters.User(user_id=ADMIN_IDS)))
    
    # Обработчики для админ-панели
    application.add_handler(CallbackQueryHandler(handle_admin_db_callback, pattern=r"^admin_db"))
    application.add_handler(CallbackQueryHandler(handle_broadcast_button, pattern=r"^broadcast_"))
    
    # Другие обработчики
    # ...
from typing import Dict, List, Any, Optional, Tuple
import asyncio
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

from config import logger, ADMIN_IDS
from admin_utils import (
    admin_base_menu,
    handle_admin_db_callback
)
from admin_messaging import (
    start_message_composition,
    handle_broadcast_message,
    handle_broadcast_button
)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает панель администратора"""
    # Проверяем, что пользователь администратор
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к панели администратора.")
        return
    
    # Формируем кнопки панели администратора
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🗃️ Управление базами данных", callback_data="admin_db")],
        [InlineKeyboardButton("🔄 Системные операции", callback_data="admin_system")],
        [InlineKeyboardButton("📣 Сообщение пользователям", callback_data="admin_broadcast")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение с панелью администратора
    await update.message.reply_text(
        "👨‍💼 <b>Панель администратора</b>\n\n"
        "Выберите нужный раздел:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

def register_handlers(application: Application) -> None:
    """Регистрирует обработчики команд и сообщений"""
    # Команды администратора
    application.add_handler(CommandHandler("admin", admin_panel, filters=filters.User(user_id=ADMIN_IDS)))
    
    # Обработчики для админ-панели
    application.add_handler(CallbackQueryHandler(handle_admin_db_callback, pattern=r"^admin_db"))
    application.add_handler(CallbackQueryHandler(handle_broadcast_button, pattern=r"^broadcast_"))
    
    # Другие обработчики
    # ...

# Обновим функцию register_handlers, заменив handle_admin_panel на admin_panel
def register_handlers_fixed(application: Application) -> None:
    """Регистрирует обработчики команд и сообщений (исправленная версия)"""
    # Команды администратора
    application.add_handler(CommandHandler("admin", admin_panel, filters=filters.User(user_id=ADMIN_IDS)))
    
    # Обработчики для админ-панели
    application.add_handler(CallbackQueryHandler(handle_admin_db_callback, pattern=r"^admin_db"))
    application.add_handler(CallbackQueryHandler(handle_broadcast_button, pattern=r"^broadcast_"))
    
    # Другие обработчики
    # ...
import hashlib
import os
import csv
import re
import time
import asyncio
import io
import json
import tempfile
import shutil
from typing import Optional, List, Dict, Tuple, Any, Callable, Union
import sys

# Добавим полный импорт для telegram модуля как запасной вариант
import telegram as telegram_module  # импортируем как telegram_module, чтобы избежать конфликтов
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from telegram.ext import ContextTypes, Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
from telegram.constants import ParseMode
import fitz  # type: ignore # для PDF (PyMuPDF)
import threading

# Сделаем доступным telegram как модуль для использования при импорте
telegram = telegram_module  # экспортируем как telegram для использования в импортах

from config import ADMIN_IDS, PDF_DOCS_DIR, logger, APP_ENV, TELEGRAM_TOKEN
from models import is_russian, llm
from database import load_knowledge, load_cache, save_cache, add_to_cache, get_cached_answer, get_unanswered_questions, mark_question_as_answered, add_unanswered_question
from knowledge_base import add_knowledge_node, get_children, get_topic_nodes, save_knowledge
from answer_generator import find_best_answer, generate_russian_answer
from pdf_handler import extract_text_from_pdf, index_pdf_file, process_pdf_file, update_all_pdf_index
from question_processing import generate_clarification, analyze_and_rephrase_question
from analytics import analytics
from security import security_manager, admin_required, rate_limit, validate_user_input, prevent_bot_abuse, check_bot_abuse
from enhanced_logging import logger, LoggingContext, log_critical_error
from error_handler import handle_error, ErrorHandler, async_error_handler, catch_exceptions
from vector_search import update_faiss_index
from admin_utils import admin_base_menu, handle_admin_db_callback
from backup_manager import backup_manager

# Добавляем константу AWAITING_KNOWLEDGE_QUESTION для импорта
AWAITING_KNOWLEDGE_QUESTION = 100
# Добавляем константу AWAITING_KNOWLEDGE_ANSWER для импорта
AWAITING_KNOWLEDGE_ANSWER = 101
# Добавляем константу AWAITING_PDF_FILE для импорта
AWAITING_PDF_FILE = 102

# Добавляем функцию add_knowledge_question в начало файла для импорта
@async_error_handler
@admin_required
async def add_knowledge_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Добавляет новый вопрос и ответ в базу знаний.
    Должна вызываться с двумя аргументами в context.args: вопрос и ответ.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    # Проверяем, что переданы необходимые аргументы
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ <b>Недостаточно аргументов</b>\n\n"
            "Использование: /add_knowledge_question \"Вопрос\" \"Ответ\"",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        return
    
    # Получаем вопрос и ответ из аргументов
    # Объединяем все аргументы кроме последнего в вопрос
    question = " ".join(context.args[:-1])
    # Последний аргумент - ответ
    answer = context.args[-1]
    
    try:
        # Загружаем базу знаний
        knowledge = load_knowledge()
        
        # Генерируем новый ID
        new_id = 1
        if knowledge:
            new_id = max(int(item.get("id", 0)) for item in knowledge) + 1
        
        # Создаем новую запись
        new_entry = {
            "id": new_id,
            "question": question,
            "answer": answer,
            "topic_path": "прямое добавление",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Добавляем в базу знаний
        knowledge.append(new_entry)
        
        # Сохраняем обновленную базу знаний
        save_knowledge(knowledge)
        
        # Обновляем индекс в фоновом режиме
        asyncio.create_task(update_faiss_index())
        
        # Подтверждаем добавление
        await update.message.reply_text(
            "✅ <b>Вопрос и ответ успешно добавлены в базу знаний!</b>\n\n"
            f"ID: {new_id}\n"
            f"Вопрос: {question}\n"
            f"Ответ: {answer}",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Ошибка добавления в базу знаний: {e}")
        
        await update.message.reply_text(
            f"❌ <b>Ошибка добавления в базу знаний</b>\n\n"
            f"Произошла ошибка: {str(e)}\n\n"
            f"Пожалуйста, попробуйте еще раз или обратитесь к разработчику.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )

# Добавляем функцию add_knowledge_answer в начало файла для импорта
@async_error_handler
@admin_required
async def add_knowledge_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Добавляет ответ к существующему вопросу в базе знаний.
    Должна вызываться с двумя аргументами в context.args: ID вопроса и текст ответа.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    # Проверяем, что переданы необходимые аргументы
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ <b>Недостаточно аргументов</b>\n\n"
            "Использование: /add_knowledge_answer <ID> \"Ответ\"",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        return
    
    try:
        # Получаем ID вопроса и текст ответа
        question_id = int(context.args[0])
        answer = " ".join(context.args[1:])
        
        # Загружаем базу знаний
        knowledge = load_knowledge()
        
        # Ищем запись с указанным ID
        entry = next((item for item in knowledge if int(item.get("id", 0)) == question_id), None)
        
        if not entry:
            await update.message.reply_text(
                f"❌ <b>Вопрос с ID {question_id} не найден</b>\n\n"
                "Пожалуйста, проверьте ID и попробуйте снова.",
                parse_mode=telegram_module.constants.ParseMode.HTML
            )
            return
        
        # Обновляем ответ
        entry["answer"] = answer
        
        # Сохраняем обновленную базу знаний
        save_knowledge(knowledge)
        
        # Обновляем индекс в фоновом режиме
        asyncio.create_task(update_faiss_index())
        
        # Подтверждаем обновление
        await update.message.reply_text(
            "✅ <b>Ответ успешно обновлен!</b>\n\n"
            f"ID: {question_id}\n"
            f"Вопрос: {entry['question']}\n"
            f"Новый ответ: {answer}",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        
    except ValueError:
        await update.message.reply_text(
            "❌ <b>Некорректный ID</b>\n\n"
            "ID должен быть числом. Пожалуйста, проверьте ввод и попробуйте снова.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Ошибка обновления ответа: {e}")
        await update.message.reply_text(
            f"❌ <b>Ошибка обновления ответа</b>\n\n"
            f"Произошла ошибка: {str(e)}\n\n"
            f"Пожалуйста, попробуйте еще раз или обратитесь к разработчику.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )

# Определим функцию handle_admin_callback в начале файла чтобы она была доступна для импорта
@async_error_handler
async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик административных callback-запросов.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # Проверяем, что пользователь администратор
    if user_id not in ADMIN_IDS:
        await query.answer("У вас нет доступа к этой функции", show_alert=True)
        return
    
    await query.answer()  # Отвечаем на запрос, чтобы убрать загрузку
    data = query.data
    
    if data == "admin_stats":
        await handle_admin_stats(update, context)
    elif data == "admin_db":
        await admin_base_menu(update, context)
    elif data == "admin_update_indexes":
        await handle_admin_update_indexes(update, context)
    elif data == "admin_backup":
        await handle_admin_backup(update, context)
    else:
        logger.warning(f"Неизвестная админ команда: {data}")
        await query.message.reply_text(
            "⚠️ Неизвестная команда администратора."
        )

# Определим функцию start_teach в начале файла, чтобы она была доступна для импорта
@async_error_handler
@admin_required
async def start_teach(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Запускает режим обучения бота для администраторов.
    Позволяет добавлять новые вопросы и ответы в базу знаний.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    # Начинаем режим обучения
    context.user_data['mode'] = 'teach_qa'
    context.user_data['teach_state'] = 'waiting_question'
    
    instruction_text = (
        "🧠 <b>Режим обучения запущен</b>\n\n"
        "В этом режиме вы можете добавить новые вопросы и ответы в базу знаний бота.\n\n"
        "<b>Инструкция:</b>\n"
        "1. Отправьте вопрос\n"
        "2. После этого отправьте ответ на вопрос\n"
        "3. Бот сохранит пару вопрос-ответ в базе знаний\n\n"
        "Для завершения режима обучения отправьте команду /stop"
    )
    
    # Создаем клавиатуру с кнопкой отмены
    keyboard = [[InlineKeyboardButton("❌ Отменить", callback_data="cancel_teach")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        instruction_text,
        parse_mode=telegram_module.constants.ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    await update.message.reply_text(
        "Пожалуйста, отправьте вопрос, который вы хотите добавить в базу знаний:",
        parse_mode=telegram_module.constants.ParseMode.HTML
    )

# Добавляем функцию start_add_pdf в начало файла для импорта
@async_error_handler
@admin_required
async def start_add_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Запускает режим добавления PDF-файлов в базу знаний.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    # Устанавливаем режим добавления PDF
    context.user_data['mode'] = 'add_pdf'
    
    # Инструкция для администратора
    instruction_text = (
        "📄 <b>Режим добавления PDF-файлов</b>\n\n"
        "Отправьте PDF-файл, который вы хотите добавить в базу знаний.\n\n"
        "После загрузки файл будет обработан и проиндексирован для поиска."
    )
    
    # Отправляем сообщение с инструкцией
    await update.message.reply_text(
        instruction_text,
        parse_mode=telegram_module.constants.ParseMode.HTML
    )

# Добавляем функцию process_pdf в начало файла для импорта
@async_error_handler
@admin_required
async def process_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает PDF-файл, отправленный пользователем, и добавляет его содержимое в базу знаний.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    # Проверяем, прикреплен ли документ
    if not update.message.document:
        await update.message.reply_text(
            "❌ <b>Ошибка</b>\n\n"
            "Пожалуйста, отправьте PDF-файл для обработки.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        return
    
    document = update.message.document
    
    # Проверяем, что файл имеет расширение .pdf
    if not document.file_name.lower().endswith('.pdf'):
        await update.message.reply_text(
            "❌ <b>Неподдерживаемый формат файла</b>\n\n"
            "Пожалуйста, отправьте файл в формате PDF.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        return
    
    # Загружаем файл
    file = await context.bot.get_file(document.file_id)
    file_name = document.file_name
    pdf_path = os.path.join(PDF_DOCS_DIR, file_name)
    
    # Создаем директорию, если она не существует
    os.makedirs(PDF_DOCS_DIR, exist_ok=True)
    
    await file.download_to_drive(pdf_path)
    
    await update.message.reply_text(
        "📄 <b>PDF-файл загружен</b>\n\n"
        "Начинается обработка и индексация файла...",
        parse_mode=telegram_module.constants.ParseMode.HTML
    )
    
    try:
        # Обрабатываем PDF-файл
        result = await process_pdf_file(pdf_path)
        
        # Сообщаем об успешной обработке
        await update.message.reply_text(
            "✅ <b>PDF-файл успешно обработан и добавлен в базу знаний</b>\n\n"
            f"Файл: {file_name}\n"
            f"Извлечено страниц: {result.get('pages', 0)}\n"
            f"Извлечено текста: {result.get('text_length', 0)} символов\n\n"
            "Теперь вы можете задавать вопросы, включающие содержимое этого документа.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Ошибка обработки PDF-файла: {e}")
        await update.message.reply_text(
            f"❌ <b>Ошибка обработки PDF-файла</b>\n\n"
            f"Произошла ошибка: {str(e)}\n\n"
            f"Пожалуйста, попробуйте другой файл или обратитесь к разработчику.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )

# Добавляем функцию handle_teach_qa для реализации обработки обучения
@async_error_handler
async def handle_teach_qa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает сообщения в режиме обучения бота (teach_qa).
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    # Проверяем, что пользователь - администратор
    if update.effective_user.id not in ADMIN_IDS:
        context.user_data.pop('mode', None)
        await update.message.reply_text(
            "⛔ У вас нет доступа к этой функции.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        return
    
    # Получаем текущее состояние режима обучения
    teach_state = context.user_data.get('teach_state', 'waiting_question')
    
    # Обрабатываем в зависимости от состояния
    if teach_state == 'waiting_question':
        # Сохраняем вопрос и переходим к ожиданию ответа
        context.user_data['current_question'] = update.message.text
        context.user_data['teach_state'] = 'waiting_answer'
        
        await update.message.reply_text(
            f"📝 Получен вопрос: <b>{update.message.text}</b>\n\n"
            f"Теперь отправьте ответ на этот вопрос:",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
    
    elif teach_state == 'waiting_answer':
        # Получаем вопрос и ответ
        question = context.user_data.get('current_question', '')
        answer = update.message.text
        
        # Загружаем базу знаний
        knowledge = load_knowledge()
        
        # Генерируем новый ID
        new_id = 1
        if knowledge:
            new_id = max(int(item.get("id", 0)) for item in knowledge) + 1
        
        # Создаем новую запись
        new_entry = {
            "id": new_id,
            "question": question,
            "answer": answer,
            "topic_path": "обучение через бота",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Добавляем в базу знаний
        knowledge.append(new_entry)
        save_knowledge(knowledge)
        
        # Обновляем индекс в фоновом режиме
        asyncio.create_task(update_faiss_index())
        
        # Подтверждаем добавление
        await update.message.reply_text(
            "✅ <b>Вопрос и ответ успешно добавлены в базу знаний!</b>\n\n"
            f"ID: {new_id}\n"
            f"Вопрос: {question}\n"
            f"Ответ: {answer}\n\n"
            "Вы можете отправить еще один вопрос или команду /stop для завершения режима обучения.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        
        # Возвращаемся к ожиданию вопроса
        context.user_data['teach_state'] = 'waiting_question'
        context.user_data.pop('current_question', None)

# Добавляем функцию handle_teach_bulk для обработки массового обучения
@async_error_handler
async def handle_teach_bulk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает текстовый ввод в режиме массового обучения.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    # Проверяем, что пользователь - администратор
    if update.effective_user.id not in ADMIN_IDS:
        context.user_data.pop('mode', None)
        await update.message.reply_text(
            "⛔ У вас нет доступа к этой функции.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        return
    
    if update.message.text.strip().lower() == '/stop':
        # Завершаем режим обучения
        context.user_data.pop('mode', None)
        await update.message.reply_text(
            "✅ <b>Режим массового обучения завершен</b>",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        return
    
    # Предупреждаем, что нужно загрузить файл
    await update.message.reply_text(
        "📂 <b>Пожалуйста, загрузите файл</b>\n\n"
        "Для массового обучения необходимо загрузить файл в формате CSV или JSON.\n\n"
        "CSV-файл должен иметь два столбца, разделенные точкой с запятой (;):\n"
        "вопрос;ответ\n\n"
        "JSON-файл должен быть в формате:\n"
        "[{\"question\": \"вопрос\", \"answer\": \"ответ\"}, ...]\n\n"
        "Для завершения режима отправьте /stop",
        parse_mode=telegram_module.constants.ParseMode.HTML
    )

# Добавляем функцию handle_admin_edit для обработки режима редактирования
@async_error_handler
async def handle_admin_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает текстовый ввод в режиме редактирования записей.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    # Проверяем, что пользователь - администратор
    if update.effective_user.id not in ADMIN_IDS:
        context.user_data.pop('mode', None)
        await update.message.reply_text(
            "⛔ У вас нет доступа к этой функции.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        return
    
    # Получаем текущее состояние и ID записи для редактирования
    edit_item_id = context.user_data.get('edit_item_id')
    edit_field = context.user_data.get('edit_field')
    
    if not edit_item_id or not edit_field:
        await update.message.reply_text(
            "❌ <b>Ошибка</b>\n\n"
            "Не найдена информация о редактируемой записи. Пожалуйста, начните процесс редактирования заново.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        # Сбрасываем режим редактирования
        context.user_data.pop('mode', None)
        context.user_data.pop('edit_item_id', None)
        context.user_data.pop('edit_field', None)
        return
    
    # Получаем новое значение поля
    new_value = update.message.text
    
    # Загружаем базу знаний
    knowledge = load_knowledge()
    
    # Ищем запись с указанным ID
    entry = next((item for item in knowledge if int(item.get("id", 0)) == edit_item_id), None)
    
    if not entry:
        await update.message.reply_text(
            f"❌ <b>Ошибка</b>\n\n"
            f"Запись с ID {edit_item_id} не найдена в базе знаний.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        # Сбрасываем режим редактирования
        context.user_data.pop('mode', None)
        context.user_data.pop('edit_item_id', None)
        context.user_data.pop('edit_field', None)
        return
    
    # Обновляем поле
    old_value = entry.get(edit_field, "")
    entry[edit_field] = new_value
    
    # Сохраняем обновленную базу знаний
    save_knowledge(knowledge)
    
    # Обновляем индекс в фоновом режиме
    asyncio.create_task(update_faiss_index())
    
    # Подтверждаем обновление
    await update.message.reply_text(
        f"✅ <b>Запись успешно обновлена</b>\n\n"
        f"ID: {edit_item_id}\n"
        f"Поле: {edit_field}\n"
        f"Старое значение: {old_value}\n"
        f"Новое значение: {new_value}",
        parse_mode=telegram_module.constants.ParseMode.HTML
    )
    
    # Сбрасываем режим редактирования
    context.user_data.pop('mode', None)
    context.user_data.pop('edit_item_id', None)
    context.user_data.pop('edit_field', None)

# Функция для добавления массовых записей в базу знаний
async def add_bulk_entries(entries: List[Dict[str, str]]) -> int:
    """
    Добавляет массово вопросы и ответы в базу знаний.
    
    Args:
        entries: Список словарей с ключами "question" и "answer"
    
    Returns:
        int: Количество успешно добавленных записей
    """
    # Загружаем базу знаний
    knowledge = load_knowledge()
    
    # Определяем начальный ID
    start_id = 1
    if knowledge:
        start_id = max(int(item.get("id", 0)) for item in knowledge) + 1
    
    # Счетчик успешно добавленных записей
    success_count = 0
    
    # Добавляем записи
    for i, entry in enumerate(entries):
        question = entry.get("question", "").strip()
        answer = entry.get("answer", "").strip()
        
        # Проверяем, что вопрос и ответ не пустые
        if not question or not answer:
            continue
        
        # Создаем новую запись
        new_entry = {
            "id": start_id + i,
            "question": question,
            "answer": answer,
            "topic_path": "массовое добавление",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Добавляем в базу знаний
        knowledge.append(new_entry)
        success_count += 1
    
    # Сохраняем обновленную базу знаний
    if success_count > 0:
        save_knowledge(knowledge)
        # Обновляем индекс в фоновом режиме
        asyncio.create_task(update_faiss_index())
    
    return success_count

# Состояния для конечных автоматов диалогов
(
    WAITING_QUESTION, WAITING_ANSWER, WAITING_BULK_DATA, 
    WAITING_FILE, WAITING_PDF_FILE, WAITING_EDIT_INPUT
) = range(6)

# Команды бота
@validate_user_input
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /start и приветствует пользователя.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    user_id = update.effective_user.id
    analytics.record_event(
        user_id, 
        event_type="command", 
        event_data={"command": "start"}
    )
    
    # Проверяем, не заблокирован ли пользователь
    if security_manager.is_blocked(user_id):
        logger.warning(f"Заблокированный пользователь {user_id} пытается использовать бота")
        await update.message.reply_text("⛔ Ваш доступ к боту ограничен. Обратитесь к администратору.")
        return
    
    logger.info(f"Пользователь {update.effective_user.id} запустил бота")
    welcome_message = (
        "Мир Вам! 🌙 \n\n"
        "Я бот, который отвечает на вопросы по исламской тематике. "
        "Задайте мне вопрос, и я постараюсь найти на него ответ в своей базе знаний.\n\n"
        "Вы можете просто написать свой вопрос или использовать следующие команды:\n"
        "/help - Получить справку по использованию бота\n"
    )
    
    # Добавление команд админа для админов
    if user_id in ADMIN_IDS:
        welcome_message += "\n👑 <b>Команды администратора:</b>\n"
        welcome_message += "/teach_auto - Начать режим автоматического обучения\n"
        welcome_message += "/add_pdf - Добавить PDF-файл в базу знаний\n"
        welcome_message += "/base - Открыть панель администрирования\n"
        welcome_message += "/analyze - Получить аналитику использования бота\n"
    
    await update.message.reply_text(welcome_message, parse_mode='HTML')

@async_error_handler
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user_first_name = update.effective_user.first_name
    
    # Регистрируем событие в аналитике
    analytics.record_event(
        update.effective_user.id,
        "bot_start",
        {"username": update.effective_user.username}
    )
    
    welcome_text = (
        f"👋 Ассаламу алейкум, {user_first_name}!\n\n"
        f"Я бот на основе ИИ для ответов на вопросы об исламе.\n\n"
        f"🔍 <b>Просто напишите свой вопрос</b>, и я постараюсь дать на него ответ "
        f"на основе проверенных источников.\n\n"
        f"🕋 <b>Примеры вопросов:</b>\n"
        f"• Что такое намаз?\n"
        f"• Как держать пост в Рамадан?\n"
        f"• Что такое закят и кому его давать?\n\n"
        f"📚 Я также могу искать информацию в PDF-документах.\n\n"
        f"<i>Помните, что я всего лишь программа и могу ошибаться. "
        f"При необходимости обращайтесь к имамам и учёным.</i>"
    )
    
    # Создаем клавиатуру с кнопками
    keyboard = [
        [InlineKeyboardButton("❓ Задать вопрос", callback_data="ask_question")],
        [InlineKeyboardButton("📋 О боте", callback_data="about_bot")]
    ]
    
    # Для администраторов добавляем дополнительные кнопки
    if update.effective_user.id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🛠️ Админ-панель", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode=telegram_module.constants.ParseMode.HTML
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет справочную информацию"""
    # Исправляем незавершенный вызов корутины
    await update.message.reply_text("Справочная информация по боту")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отображает панель администрирования бота.
    Доступно только для пользователей из списка администраторов.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    # Проверяем, что пользователь - администратор
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text(
            "⛔ У вас нет доступа к этой функции.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        return
    
    admin_text = (
        "🛠️ <b>Административная панель</b>\n\n"
        "Выберите действие:"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📚 Управление базами данных", callback_data="admin_db")],
        [InlineKeyboardButton("🔄 Обновить индексы", callback_data="admin_update_indexes")],
        [InlineKeyboardButton("💾 Резервное копирование", callback_data="admin_backup")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        admin_text,
        parse_mode=telegram_module.constants.ParseMode.HTML,
        reply_markup=reply_markup
    )

async def about_command(update, context):
    # Отправляет информацию о боте
    await update.message.reply_text("Информация о боте: версия 1.0. Все права защищены.")

async def typing_action(bot, chat_id, stop_event):
    """
    Периодически отправляет статус 'печатает...' в указанный чат
    
    Args:
        bot: Объект бота Telegram
        chat_id: ID чата, куда отправлять статус
        stop_event: Событие для остановки отправки статуса
    """
    try:
        while not stop_event.is_set():
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(4)  # Обновляем статус каждые 4 секунды
    except Exception as e:
        logger.error(f"Ошибка отправки статуса 'печатает...': {e}")

@async_error_handler
@prevent_bot_abuse()
@rate_limit(5)  # Не более 5 запросов в минуту
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает входящие сообщения пользователя"""
    # Проверка на активный режим обучения
    if 'mode' in context.user_data:
        mode = context.user_data['mode']
        
        if mode == 'teach_qa':
            return await handle_teach_qa(update, context)
        elif mode == 'teach_bulk':
            return await handle_teach_bulk(update, context)
        elif mode == 'admin_edit':
            return await handle_admin_edit(update, context)
    
    # Обработка обычного сообщения как вопроса
    question = update.message.text.strip()
    
    # Проверяем, что это русский текст
    if not is_russian(question):
        await update.message.reply_text(
            "🌐 Пожалуйста, задавайте вопросы на русском языке."
        )
        return
    
    # Регистрируем вопрос в аналитике
    analytics.record_event(
        update.effective_user.id,
        "query",
        {"query_text": question[:100]}
    )
    
    # Создаем событие для остановки статуса "печатает..."
    stop_typing = asyncio.Event()
    
    # Запускаем периодическую отправку статуса "печатает..."
    typing_task = asyncio.create_task(
        typing_action(context.bot, update.effective_chat.id, stop_typing)
    )
    
    try:
        # Анализируем вопрос для улучшения поиска
        analysis = await analyze_and_rephrase_question(question)
        
        # Ищем ответ
        answer, is_from_cache = await find_best_answer(
            question=question,
            variations=analysis["variations"],
            best_query=analysis["best_search_query"]
        )
        
        # Если ответ не найден, добавляем вопрос в список неотвеченных
        if not answer or "не найден" in answer.lower():
            add_unanswered_question(update.effective_user.id, question)
        
        # Создаем клавиатуру обратной связи
        keyboard = [
            [InlineKeyboardButton("👍 Полезно", callback_data=f"feedback:useful:{hash(question)}")],
            [InlineKeyboardButton("👎 Неполезно", callback_data=f"feedback:not_useful:{hash(question)}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Останавливаем отправку статуса "печатает..."
        stop_typing.set()
        
        # Ждем завершения задачи typing_task
        try:
            await typing_task
        except asyncio.CancelledError:
            pass
        
        # Отправляем ответ пользователю
        await update.message.reply_text(
            answer,
            parse_mode=telegram_module.constants.ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    finally:
        # Убеждаемся, что статус "печатает..." остановлен
        if not stop_typing.is_set():
            stop_typing.set()
        
        # Если задача еще не завершена, отменяем её
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try:
                await typing_task
            except asyncio.CancelledError:
                pass

@async_error_handler
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия на инлайн-кнопки"""
    query = update.callback_query
    await query.answer()  # Отвечаем на запрос, чтобы убрать индикатор загрузки
    
    data = query.data
    
    if data == "ask_question":
        await query.message.reply_text(
            "🔍 Пожалуйста, задайте ваш вопрос."
        )
    
    elif data == "about_bot":
        about_text = (
            "🤖 <b>О боте</b>\n\n"
            "Я - бот на основе искусственного интеллекта, созданный для ответов на вопросы об исламе.\n\n"
            "🔍 Я использую:<ul>"
            "<li>Базу знаний с проверенной информацией</li>"
            "<li>Индексированные PDF-документы от надежных источников</li>"
            "<li>Языковую модель для формирования ответов</li></ul>\n"
            "📚 Вы можете задать любой вопрос об исламе, и я постараюсь найти на него ответ.\n\n"
            "<i>Помните, что я лишь инструмент и могу ошибаться. "
            "По важным религиозным вопросам всегда консультируйтесь с имамом или учёным.</i>"
        )
        
        await query.message.edit_text(
            about_text,
            parse_mode=telegram_module.constants.ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")]
            ])
        )
    
    elif data == "back_to_start":
        # Возвращаемся к стартовому сообщению
        await query.message.delete()
        await start_command(update, context)
    
    elif data == "admin_panel":
        # Проверяем, что пользователь админ
        if update.effective_user.id in ADMIN_IDS:
            admin_text = (
                "🛠️ <b>Административная панель</b>\n\n"
                "Выберите действие:"
            )
            
            keyboard = [
                [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
                [InlineKeyboardButton("📚 Управление базами данных", callback_data="admin_db")],
                [InlineKeyboardButton("🔄 Обновить индексы", callback_data="admin_update_indexes")],
                [InlineKeyboardButton("💾 Резервное копирование", callback_data="admin_backup")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")]
            ]
            
            await query.message.edit_text(
                admin_text,
                parse_mode=telegram_module.constants.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.message.edit_text(
                "⛔ У вас нет доступа к этой функции.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")]
                ])
            )
    
    elif data.startswith("admin_db:"):
        # Обработка команд управления базой данных
        await handle_admin_db_callback(update, context)
    
    elif data.startswith("feedback:"):
        # Обработка обратной связи о качестве ответа
        parts = data.split(":")
        if len(parts) == 3:
            feedback_type = parts[1]
            question_hash = parts[2]
            
            # Регистрируем обратную связь в аналитике
            analytics.record_event(
                update.effective_user.id,
                "feedback",
                {"type": feedback_type, "question_hash": question_hash}
            )
            
            # Благодарим пользователя за обратную связь
            await query.edit_message_reply_markup(None)
            await query.message.reply_text(
                "🙏 Спасибо за ваш отзыв! Это помогает нам улучшать качество ответов."
            )
            
            # Если ответ неполезен, предлагаем задать вопрос иначе
            if feedback_type == "not_useful":
                await query.message.reply_text(
                    "🔄 Попробуйте задать вопрос другими словами для получения более точного ответа."
                )

    elif data.startswith("update_index"):
        # Обновление индекса PDF
        await query.edit_message_text(
            "🔄 <b>Обновление индекса PDF</b>\n\n"
            "Выполняется обновление индекса PDF-документов...",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        
        # Запускаем обновление индекса
        success = await update_all_pdf_index()
        
        if success:
            await query.edit_message_text(
                "✅ <b>Индекс PDF успешно обновлен</b>\n\n"
                "Индекс PDF-документов обновлен и готов к использованию.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="admin_pdf")]]),
                parse_mode=telegram_module.constants.ParseMode.HTML
            )
        else:
            await query.edit_message_text(
                "❌ <b>Ошибка обновления индекса PDF</b>\n\n"
                "Произошла ошибка при обновлении индекса. Проверьте логи для подробностей.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="admin_pdf")]]),
                parse_mode=telegram_module.constants.ParseMode.HTML
            )

@async_error_handler
async def handle_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает запрос на получение статистики использования бота от администратора.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    # Проверяем, что пользователь администратор
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        if update.callback_query:
            await update.callback_query.answer("У вас нет доступа к этой функции", show_alert=True)
        else:
            await update.message.reply_text("⛔ У вас нет доступа к этой функции.")
        return
    
    # Получаем статистику из модуля аналитики
    stats_data = analytics.get_stats()
    
    # Формируем сообщение с результатами
    current_time = time.strftime("%d.%m.%Y %H:%M:%S")
    stats_message = f"📊 <b>Статистика использования бота</b>\n\n"
    
    if stats_data:
        total_users = stats_data.get('total_users', 0)
        total_questions = stats_data.get('total_questions', 0)
        active_users_today = stats_data.get('active_users_today', 0)
        questions_today = stats_data.get('questions_today', 0)
        cache_hits = stats_data.get('cache_hits', 0)
        cache_misses = stats_data.get('cache_misses', 0)
        
        stats_message += f"🧑‍💻 <b>Пользователи:</b>\n"
        stats_message += f"• Всего пользователей: {total_users}\n"
        stats_message += f"• Активных пользователей сегодня: {active_users_today}\n\n"
        
        stats_message += f"❓ <b>Вопросы:</b>\n"
        stats_message += f"• Всего вопросов: {total_questions}\n"
        stats_message += f"• Вопросов сегодня: {questions_today}\n\n"
        
        stats_message += f"🔍 <b>Кэширование:</b>\n"
        cache_total = cache_hits + cache_misses
        cache_hit_rate = (cache_hits / cache_total * 100) if cache_total > 0 else 0
        stats_message += f"• Попаданий в кэш: {cache_hits}\n"
        stats_message += f"• Промахов кэша: {cache_misses}\n"
        stats_message += f"• Эффективность кэша: {cache_hit_rate:.1f}%\n\n"
    else:
        stats_message += "ℹ️ Статистика пуста или недоступна.\n\n"
    
    stats_message += f"🕒 Данные актуальны на: {current_time}"
    
    # Создаем клавиатуру с кнопками
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats:refresh")],
        [InlineKeyboardButton("📊 Подробная статистика", callback_data="admin_stats:detailed")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем или обновляем сообщение
    if update.callback_query:
        await update.callback_query.edit_message_text(
            stats_message,
            reply_markup=reply_markup,
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            stats_message,
            reply_markup=reply_markup,
            parse_mode=telegram_module.constants.ParseMode.HTML
        )

@async_error_handler
async def handle_admin_update_indexes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает запрос на обновление индексов от администратора.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        if update.callback_query:
            await update.callback_query.answer("У вас нет доступа к этой функции", show_alert=True)
        else:
            await update.message.reply_text("⛔ У вас нет доступа к этой функции.")
        return
    
    # Формируем информационное сообщение
    message_text = (
        "🔄 <b>Обновление индексов базы знаний</b>\n\n"
        "Выберите действие, которое хотите выполнить:"
    )
    
    # Создаем клавиатуру с кнопками
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить индекс базы знаний", callback_data="update_index:knowledge")],
        [InlineKeyboardButton("🔄 Обновить индекс PDF-файлов", callback_data="update_index:pdf")],
        [InlineKeyboardButton("🔄 Обновить все индексы", callback_data="update_index:all")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем или обновляем сообщение
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=telegram_module.constants.ParseMode.HTML
        )

@async_error_handler
async def handle_admin_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает запрос на управление резервными копиями от администратора.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        if update.callback_query:
            await update.callback_query.answer("У вас нет доступа к этой функции", show_alert=True)
        else:
            await update.message.reply_text("⛔ У вас нет доступа к этой функции.")
        return
    
    # Формируем информационное сообщение
    message_text = (
        "💾 <b>Управление резервными копиями</b>\n\n"
        "Выберите действие, которое хотите выполнить:"
    )
    
    # Создаем клавиатуру с кнопками
    keyboard = [
        [InlineKeyboardButton("📤 Создать резервную копию", callback_data="backup:create")],
        [InlineKeyboardButton("📥 Восстановить из копии", callback_data="backup:restore_list")],
        [InlineKeyboardButton("📋 Список резервных копий", callback_data="backup:list")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем или обновляем сообщение
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=telegram_module.constants.ParseMode.HTML
        )

@async_error_handler
async def handle_backup_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает действия с резервными копиями.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id not in ADMIN_IDS:
        await query.answer("У вас нет доступа к этой функции", show_alert=True)
        return
    
    # Отвечаем на запрос, чтобы убрать индикатор загрузки
    await query.answer()
    
    # Получаем действие из callback_data
    action = query.data.split(":", 1)[1] if ":" in query.data else ""
    
    if action == "create":
        # Создание резервной копии
        await query.edit_message_text(
            "💾 <b>Создание резервной копии</b>\n\n"
            "Пожалуйста, подождите, идет создание резервной копии...",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        
        try:
            # Создаем резервную копию
            backup_path = await backup_manager.create_backup()
            
            # Сообщаем о результате
            await query.edit_message_text(
                f"✅ <b>Резервная копия успешно создана</b>\n\n"
                f"Файл: {os.path.basename(backup_path)}\n"
                f"Размер: {os.path.getsize(backup_path) / 1024 / 1024:.2f} МБ\n"
                f"Дата: {time.strftime('%d.%m.%Y %H:%M:%S')}",
                parse_mode=telegram_module.constants.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="admin_backup")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {str(e)}")
            await query.edit_message_text(
                f"❌ <b>Ошибка создания резервной копии</b>\n\n"
                f"Причина: {str(e)}",
                parse_mode=telegram_module.constants.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="admin_backup")]
                ])
            )
    
    elif action == "list":
        # Отображение списка резервных копий
        await query.edit_message_text(
            "📋 <b>Список резервных копий</b>\n\n"
            "Загрузка списка резервных копий...",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        
        try:
            # Получаем список резервных копий
            backups = await backup_manager.list_backups()
            
            if backups:
                # Формируем сообщение со списком
                message = "📋 <b>Список резервных копий</b>\n\n"
                
                for i, backup in enumerate(backups, 1):
                    message += f"{i}. <b>{backup['name']}</b>\n"
                    message += f"   📅 Дата: {backup['date']}\n"
                    message += f"   📦 Размер: {backup['size'] / 1024 / 1024:.2f} МБ\n\n"
                
                # Добавляем кнопки навигации
                keyboard = [
                    [InlineKeyboardButton("◀️ Назад", callback_data="admin_backup")]
                ]
                
                await query.edit_message_text(
                    message,
                    parse_mode=telegram_module.constants.ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(
                    "📋 <b>Список резервных копий</b>\n\n"
                    "Резервные копии не найдены.",
                    parse_mode=telegram_module.constants.ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("◀️ Назад", callback_data="admin_backup")]
                    ])
                )
        except Exception as e:
            logger.error(f"Ошибка получения списка резервных копий: {str(e)}")
            await query.edit_message_text(
                f"❌ <b>Ошибка получения списка резервных копий</b>\n\n"
                f"Причина: {str(e)}",
                parse_mode=telegram_module.constants.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="admin_backup")]
                ])
            )
    
    elif action == "restore_list":
        # Отображение списка резервных копий для восстановления
        await query.edit_message_text(
            "📥 <b>Восстановление из резервной копии</b>\n\n"
            "Загрузка списка доступных резервных копий...",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        
        try:
            # Получаем список резервных копий
            backups = await backup_manager.list_backups()
            
            if backups:
                # Формируем сообщение со списком
                message = "📥 <b>Выберите резервную копию для восстановления</b>\n\n"
                message += "⚠️ <b>Внимание!</b> Восстановление перезапишет текущие данные!\n\n"
                
                # Создаем клавиатуру с кнопками для каждой резервной копии
                keyboard = []
                
                for i, backup in enumerate(backups, 1):
                    backup_name = backup['name']
                    backup_date = backup['date']
                    
                    # Добавляем информацию о резервной копии
                    message += f"{i}. <b>{backup_name}</b>\n"
                    message += f"   📅 Дата: {backup_date}\n"
                    message += f"   📦 Размер: {backup['size'] / 1024 / 1024:.2f} МБ\n\n"
                    
                    # Добавляем кнопку для восстановления
                    keyboard.append([InlineKeyboardButton(
                        f"🔄 Восстановить копию #{i}",
                        callback_data=f"backup:restore:{backup_name}"
                    )])
                
                # Добавляем кнопку "Назад"
                keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_backup")])
                
                await query.edit_message_text(
                    message,
                    parse_mode=telegram_module.constants.ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(
                    "📥 <b>Восстановление из резервной копии</b>\n\n"
                    "Резервные копии не найдены.",
                    parse_mode=telegram_module.constants.ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("◀️ Назад", callback_data="admin_backup")]
                    ])
                )
        except Exception as e:
            logger.error(f"Ошибка получения списка резервных копий: {str(e)}")
            await query.edit_message_text(
                f"❌ <b>Ошибка получения списка резервных копий</b>\n\n"
                f"Причина: {str(e)}",
                parse_mode=telegram_module.constants.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="admin_backup")]
                ])
            )
    
    elif action.startswith("restore:"):
        # Восстановление из резервной копии
        backup_name = action.split(":", 1)[1]
        
        # Запрашиваем подтверждение
        await query.edit_message_text(
            f"⚠️ <b>Подтверждение восстановления</b>\n\n"
            f"Вы уверены, что хотите восстановить данные из резервной копии:\n"
            f"<b>{backup_name}</b>?\n\n"
            f"Все текущие данные будут перезаписаны!",
            parse_mode=telegram_module.constants.ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, восстановить", callback_data=f"backup:confirm_restore:{backup_name}")],
                [InlineKeyboardButton("❌ Отмена", callback_data="backup:restore_list")]
            ])
        )
    
    elif action.startswith("confirm_restore:"):
        # Подтверждение восстановления
        backup_name = action.split(":", 1)[1]
        
        await query.edit_message_text(
            f"🔄 <b>Восстановление из резервной копии</b>\n\n"
            f"Восстановление данных из резервной копии: <b>{backup_name}</b>\n\n"
            f"Пожалуйста, подождите... Это может занять некоторое время.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        
        try:
            # Выполняем восстановление
            await backup_manager.restore_backup(backup_name)
            
            # Сообщаем об успешном восстановлении
            await query.edit_message_text(
                f"✅ <b>Данные успешно восстановлены</b>\n\n"
                f"Восстановление из резервной копии <b>{backup_name}</b> выполнено успешно.",
                parse_mode=telegram_module.constants.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="admin_backup")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка восстановления из резервной копии: {str(e)}")
            await query.edit_message_text(
                f"❌ <b>Ошибка восстановления данных</b>\n\n"
                f"Причина: {str(e)}",
                parse_mode=telegram_module.constants.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="admin_backup")]
                ])
            )
    
    else:
        # Неизвестное действие
        await query.edit_message_text(
            "❌ <b>Неизвестное действие</b>\n\n"
            "Пожалуйста, вернитесь назад и попробуйте снова.",
            parse_mode=telegram_module.constants.ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад", callback_data="admin_backup")]
            ])
        )

@async_error_handler
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает загрузку документов в чат с ботом.
    Проверяет, находится ли пользователь в режиме загрузки PDF или другом режиме.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    # Проверяем, не заблокирован ли пользователь
    user_id = update.effective_user.id
    if security_manager.is_blocked(user_id):
        logger.warning(f"Заблокированный пользователь {user_id} пытается загрузить документ")
        await update.message.reply_text("⛔ Ваш доступ к боту ограничен. Обратитесь к администратору.")
        return
    
    # Проверяем режим пользователя
    if 'mode' in context.user_data:
        mode = context.user_data['mode']
        
        if mode == 'add_pdf':
            # Режим добавления PDF
            # Проверяем, что документ - PDF
            if update.message.document.file_name.lower().endswith('.pdf'):
                # Загружаем и обрабатываем PDF
                file = await context.bot.get_file(update.message.document.file_id)
                file_name = update.message.document.file_name
                
                # Создаем путь для сохранения PDF
                pdf_path = os.path.join(PDF_DOCS_DIR, file_name)
                
                # Проверяем, существует ли директория, и создаем ее при необходимости
                os.makedirs(PDF_DOCS_DIR, exist_ok=True)
                
                # Загружаем файл
                await file.download_to_drive(pdf_path)
                
                await update.message.reply_text(
                    "📄 <b>PDF-файл загружен</b>\n\n"
                    "Начинается обработка и индексация файла...",
                    parse_mode=telegram_module.constants.ParseMode.HTML
                )
                
                try:
                    # Обрабатываем и индексируем PDF
                    result = await process_pdf_file(pdf_path)
                    
                    # Сообщаем о результате
                    await update.message.reply_text(
                        "✅ <b>PDF-файл успешно обработан и добавлен в базу знаний</b>\n\n"
                        f"Файл: {file_name}\n"
                        f"Извлечено страниц: {result.get('pages', 0)}\n"
                        f"Извлечено текста: {result.get('text_length', 0)} символов\n\n"
                        "Теперь вы можете задавать вопросы, включающие содержимое этого документа.",
                        parse_mode=telegram_module.constants.ParseMode.HTML
                    )
                    
                    # Сбрасываем режим
                    context.user_data.pop('mode', None)
                    
                except Exception as e:
                    logger.error(f"Ошибка обработки PDF-файла: {str(e)}")
                    await update.message.reply_text(
                        f"❌ <b>Ошибка обработки PDF-файла</b>\n\n"
                        f"Произошла ошибка: {str(e)}\n\n"
                        f"Пожалуйста, попробуйте другой файл или обратитесь к разработчику.",
                        parse_mode=telegram_module.constants.ParseMode.HTML
                    )
            else:
                # Если файл не PDF
                await update.message.reply_text(
                    "❌ <b>Неподдерживаемый тип файла</b>\n\n"
                    "Пожалуйста, загрузите файл в формате PDF.",
                    parse_mode=telegram_module.constants.ParseMode.HTML
                )
        
        elif mode == 'teach_bulk':
            # Режим массового обучения
            # Обрабатываем документ как файл с данными для обучения
            file_name = update.message.document.file_name.lower()
            
            if file_name.endswith('.csv') or file_name.endswith('.json'):
                # Скачиваем файл
                file = await context.bot.get_file(update.message.document.file_id)
                
                # Создаем временный файл для загрузки
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    await file.download_to_drive(temp_file.name)
                    temp_path = temp_file.name
                
                try:
                    # Обрабатываем файл в зависимости от формата
                    entries = []
                    
                    if file_name.endswith('.csv'):
                        # Обрабатываем CSV-файл
                        with open(temp_path, 'r', encoding='utf-8') as f:
                            csv_reader = csv.reader(f, delimiter=';')
                            for row in csv_reader:
                                if len(row) >= 2:
                                    entries.append({'question': row[0], 'answer': row[1]})
                    
                    elif file_name.endswith('.json'):
                        # Обрабатываем JSON-файл
                        with open(temp_path, 'r', encoding='utf-8') as f:
                            entries = json.load(f)
                    
                    # Добавляем записи в базу знаний
                    success_count = await add_bulk_entries(entries)
                    
                    await update.message.reply_text(
                        f"✅ <b>Массовое обучение завершено</b>\n\n"
                        f"Добавлено {success_count} из {len(entries)} записей.\n\n"
                        f"Вы можете отправить еще один файл или команду /stop для завершения режима.",
                        parse_mode=telegram_module.constants.ParseMode.HTML
                    )
                    
                except Exception as e:
                    logger.error(f"Ошибка обработки файла: {str(e)}")
                    
                    await update.message.reply_text(
                        f"❌ <b>Ошибка обработки файла</b>\n\n"
                        f"Произошла ошибка: {str(e)}\n\n"
                        f"Пожалуйста, проверьте формат файла и попробуйте снова.",
                        parse_mode=telegram_module.constants.ParseMode.HTML
                    )
                
                finally:
                    # Удаляем временный файл
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
            else:
                # Неподдерживаемый формат файла
                await update.message.reply_text(
                    f"❌ <b>Неподдерживаемый формат файла</b>\n\n"
                    f"Поддерживаются только форматы CSV и JSON.",
                    parse_mode=telegram_module.constants.ParseMode.HTML
                )
    else:
        # Если пользователь не в специальном режиме, проверяем, является ли он администратором
        if user_id in ADMIN_IDS:
            # Для администраторов предлагаем режим добавления PDF
            file_name = update.message.document.file_name.lower()
            
            if file_name.endswith('.pdf'):
                await update.message.reply_text(
                    "📄 <b>Обнаружен PDF-файл</b>\n\n"
                    "Хотите добавить этот файл в базу знаний?",
                    parse_mode=telegram_module.constants.ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Да, добавить", callback_data=f"add_pdf:{update.message.document.file_id}")],
                        [InlineKeyboardButton("❌ Нет", callback_data="cancel_add_pdf")]
                    ])
                )
            else:
                # Для других типов файлов просто сообщаем, что они не поддерживаются
                await update.message.reply_text(
                    "ℹ️ Бот не может обрабатывать этот тип файла."
                )
        else:
            # Для обычных пользователей сообщаем, что загрузка файлов не поддерживается
            await update.message.reply_text(
                "ℹ️ Загрузка файлов не поддерживается. Пожалуйста, задайте вопрос текстом."
            )

@async_error_handler
async def handle_pdf_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает callback-запросы, связанные с PDF-файлами.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # Проверяем, что пользователь - администратор
    if user_id not in ADMIN_IDS:
        await query.answer("У вас нет доступа к этой функции", show_alert=True)
        return
    
    # Отвечаем на запрос, чтобы убрать индикатор загрузки
    await query.answer()
    
    # Получаем действие из callback_data
    data = query.data
    
    if data.startswith("add_pdf:"):
        # Добавление PDF-файла
        file_id = data.split(":", 1)[1]
        
        # Получаем информацию о файле
        file = await context.bot.get_file(file_id)
        document = query.message.reply_to_message.document
        file_name = document.file_name
        
        # Создаем путь для сохранения PDF
        pdf_path = os.path.join(PDF_DOCS_DIR, file_name)
        
        # Проверяем, существует ли директория, и создаем ее при необходимости
        os.makedirs(PDF_DOCS_DIR, exist_ok=True)
        
        await query.edit_message_text(
            "📄 <b>Обработка PDF-файла</b>\n\n"
            "Загрузка и обработка файла...",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
        
        try:
            # Загружаем и обрабатываем PDF-файл
            await file.download_to_drive(pdf_path)
            result = await process_pdf_file(pdf_path)
            
            # Сообщаем о результате
            await query.edit_message_text(
                "✅ <b>PDF-файл успешно обработан и добавлен в базу знаний</b>\n\n"
                f"Файл: {file_name}\n"
                f"Извлечено страниц: {result.get('pages', 0)}\n"
                f"Извлечено текста: {result.get('text_length', 0)} символов\n\n"
                "Теперь вы можете задавать вопросы, включающие содержимое этого документа.",
                parse_mode=telegram_module.constants.ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Ошибка обработки PDF-файла: {str(e)}")
            await query.edit_message_text(
                f"❌ <b>Ошибка обработки PDF-файла</b>\n\n"
                f"Произошла ошибка: {str(e)}\n\n"
                f"Пожалуйста, попробуйте другой файл или обратитесь к разработчику.",
                parse_mode=telegram_module.constants.ParseMode.HTML
            )
    
    elif data == "cancel_add_pdf":
        # Отмена добавления PDF-файла
        await query.edit_message_text(
            "❌ <b>Добавление PDF-файла отменено</b>",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )
    
    else:
        # Неизвестное действие
        await query.edit_message_text(
            "❌ <b>Неизвестное действие</b>\n\n"
            "Пожалуйста, попробуйте снова.",
            parse_mode=telegram_module.constants.ParseMode.HTML
        )

# Добавляем функцию cancel_conversation в начало файла для импорта
@async_error_handler
async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Завершает текущий диалог или режим работы бота.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст бота
    
    Returns:
        int: Код завершения диалога (ConversationHandler.END)
    """
    # Сбрасываем пользовательские данные
    context.user_data.clear()
    
    # Отправляем сообщение о завершении
    await update.message.reply_text(
        "❌ <b>Диалог завершен</b>\n\n"
        "Вы можете начать новый диалог или использовать команды бота.",
        parse_mode=telegram_module.constants.ParseMode.HTML
    )
    
    return ConversationHandler.END
