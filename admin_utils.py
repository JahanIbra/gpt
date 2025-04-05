from typing import Dict, List, Any, Optional, Tuple
import json
import os
import asyncio
import sqlite3
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import DB_PATH, logger, ADMIN_IDS
from database import load_knowledge, save_knowledge
from vector_search import update_faiss_index
from pdf_handler import update_all_pdf_index
from analytics import analytics
from backup_manager import backup_manager

# Константы для CallbackQuery
DB_KNOWLEDGE = "admin_db:knowledge"
DB_CACHE = "admin_db:cache"
DB_PDF = "admin_db:pdf"
DB_UNANSWERED = "admin_db:unanswered"
DB_EXPORT = "admin_db:export"
DB_IMPORT = "admin_db:import"
DB_CLEAR_CACHE = "admin_db:clear_cache"
DB_BACK = "admin_db:back"

async def admin_base_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает меню управления базами данных для администратора"""
    # Проверяем, что пользователь администратор
    if update.effective_user.id not in ADMIN_IDS:
        await update.callback_query.message.edit_text(
            "⛔ У вас нет доступа к этой функции."
        )
        return
    
    # Получаем количество записей в базах данных
    db_stats = await get_database_stats()
    
    # Формируем меню
    keyboard = [
        [InlineKeyboardButton(f"🧠 База знаний ({db_stats['knowledge_count']})", callback_data=DB_KNOWLEDGE)],
        [InlineKeyboardButton(f"💾 Кэш ответов ({db_stats['cache_count']})", callback_data=DB_CACHE)],
        [InlineKeyboardButton(f"📄 PDF документы ({db_stats['pdf_count']})", callback_data=DB_PDF)],
        [InlineKeyboardButton(f"❓ Неотвеченные вопросы ({db_stats['unanswered_count']})", callback_data=DB_UNANSWERED)],
        [InlineKeyboardButton("📤 Экспорт базы знаний", callback_data=DB_EXPORT),
         InlineKeyboardButton("📥 Импорт базы знаний", callback_data=DB_IMPORT)],
        [InlineKeyboardButton("🧹 Очистить кэш", callback_data=DB_CLEAR_CACHE)],
        [InlineKeyboardButton("📣 Сообщение для пользователей", callback_data="admin_broadcast")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = (
        "📊 <b>Управление базами данных</b>\n\n"
        f"Размер базы данных: {db_stats['db_size']:.2f} МБ\n"
        f"Последнее обновление: {db_stats['last_update']}\n\n"
        "Выберите действие:"
    )
    
    # Обновляем сообщение или отправляем новое
    if update.callback_query:
        await update.callback_query.message.edit_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

async def handle_admin_db_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия на кнопки в меню управления базами данных"""
    query = update.callback_query
    await query.answer()
    
    # Получаем callback_data
    data = query.data
    
    if data == DB_KNOWLEDGE:
        await handle_knowledge_menu(update, context)
    elif data == DB_CACHE:
        await handle_cache_menu(update, context)
    elif data == DB_PDF:
        await handle_pdf_menu(update, context)
    elif data == DB_UNANSWERED:
        await handle_unanswered_menu(update, context)
    elif data == DB_EXPORT:
        await handle_export_db(update, context)
    elif data == DB_IMPORT:
        await handle_import_db(update, context)
    elif data == DB_CLEAR_CACHE:
        await handle_clear_cache(update, context)
    elif data == "admin_broadcast":
        # Запускаем новую функциональность отправки сообщений пользователям
        from admin_messaging import start_message_composition
        await start_message_composition(update, context)
    elif data == DB_BACK or data == "admin_panel":
        # Возвращаемся в основное меню администратора
        await admin_base_menu(update, context)
    elif data.startswith("admin_db:knowledge:"):
        await handle_knowledge_action(update, context)
    elif data.startswith("admin_db:cache:"):
        await handle_cache_action(update, context)
    elif data.startswith("admin_db:pdf:"):
        await handle_pdf_action(update, context)
    elif data.startswith("admin_db:unanswered:"):
        await handle_unanswered_action(update, context)

async def get_database_stats() -> Dict[str, Any]:
    """
    Получает статистику базы данных
    
    Returns:
        Словарь с информацией о базе данных
    """
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Получаем размер файла базы данных
        db_size = os.path.getsize(DB_PATH) / (1024 * 1024)  # Размер в МБ
        
        # Получаем количество записей в таблицах
        c.execute("SELECT COUNT(*) FROM knowledge")
        knowledge_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM cache")
        cache_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM pdf_files")
        pdf_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM unanswered_questions WHERE answered=0")
        unanswered_count = c.fetchone()[0]
        
        # Получаем время последнего обновления
        c.execute("SELECT MAX(timestamp) FROM knowledge")
        last_update = c.fetchone()[0] or "Нет данных"
        
        conn.close()
        
        return {
            "db_size": db_size,
            "knowledge_count": knowledge_count,
            "cache_count": cache_count,
            "pdf_count": pdf_count,
            "unanswered_count": unanswered_count,
            "last_update": last_update
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики базы данных: {e}")
        return {
            "db_size": 0,
            "knowledge_count": 0,
            "cache_count": 0,
            "pdf_count": 0,
            "unanswered_count": 0,
            "last_update": "Ошибка"
        }

async def handle_knowledge_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает меню управления базой знаний"""
    # Получаем список записей базы знаний (с ограничением)
    knowledge = load_knowledge()
    
    # Ограничиваем список для отображения
    max_items = 5
    total_items = len(knowledge)
    
    # Получаем номер страницы
    page = context.user_data.get('knowledge_page', 0)
    
    # Вычисляем границы для текущей страницы
    start_idx = page * max_items
    end_idx = min(start_idx + max_items, total_items)
    
    # Формируем сообщение со списком
    message_text = f"🧠 <b>База знаний</b> (всего: {total_items})\n\n"
    
    if knowledge:
        for i in range(start_idx, end_idx):
            item = knowledge[i]
            # Ограничиваем длину вопроса
            question = item.get("question", "Нет вопроса")
            if len(question) > 50:
                question = question[:47] + "..."
            
            message_text += f"{i+1}. {question}\n"
    else:
        message_text += "База знаний пуста."
    
    # Формируем кнопки
    keyboard = []
    
    # Кнопки навигации по страницам
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data="admin_db:knowledge:prev_page"))
    
    if end_idx < total_items:
        nav_buttons.append(InlineKeyboardButton("▶️ Вперед", callback_data="admin_db:knowledge:next_page"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопки для действий
    keyboard.append([InlineKeyboardButton("➕ Добавить запись", callback_data="admin_db:knowledge:add")])
    keyboard.append([InlineKeyboardButton("🔄 Обновить индекс", callback_data="admin_db:knowledge:update_index")])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=DB_BACK)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Обновляем сообщение
    await update.callback_query.message.edit_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def handle_knowledge_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает действия с базой знаний"""
    query = update.callback_query
    action = query.data.split(":")[-1]
    
    if action == "prev_page":
        # Переход на предыдущую страницу
        context.user_data['knowledge_page'] = max(0, context.user_data.get('knowledge_page', 0) - 1)
        await handle_knowledge_menu(update, context)
    
    elif action == "next_page":
        # Переход на следующую страницу
        context.user_data['knowledge_page'] = context.user_data.get('knowledge_page', 0) + 1
        await handle_knowledge_menu(update, context)
    
    elif action == "add":
        # Сообщаем о возможности добавления записи через команду /teach
        await query.message.edit_text(
            "➕ <b>Добавление записи в базу знаний</b>\n\n"
            "Для добавления новой записи используйте команду /teach\n"
            "Для массового добавления используйте /teach_bulk\n\n"
            "После добавления не забудьте обновить индекс FAISS.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_KNOWLEDGE)]]),
            parse_mode=ParseMode.HTML
        )
    
    elif action == "update_index":
        # Обновляем индекс FAISS
        await query.message.edit_text(
            "🔄 <b>Обновление индекса FAISS</b>\n\n"
            "Началось обновление индекса. Это может занять некоторое время...",
            parse_mode=ParseMode.HTML
        )
        
        # Запускаем обновление индекса
        success = await update_faiss_index()
        
        if success:
            await query.message.edit_text(
                "✅ <b>Индекс FAISS успешно обновлен!</b>\n\n"
                "Изменения вступили в силу.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_KNOWLEDGE)]]),
                parse_mode=ParseMode.HTML
            )
        else:
            await query.message.edit_text(
                "❌ <b>Ошибка обновления индекса FAISS</b>\n\n"
                "Не удалось обновить индекс. Проверьте логи для подробностей.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_KNOWLEDGE)]]),
                parse_mode=ParseMode.HTML
            )

async def handle_cache_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает меню управления кэшем ответов"""
    # Получаем информацию о кэше
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Получаем количество записей
        c.execute("SELECT COUNT(*) FROM cache")
        cache_count = c.fetchone()[0]
        
        # Получаем несколько последних записей
        c.execute("""
        SELECT question_hash, question, timestamp 
        FROM cache 
        ORDER BY timestamp DESC 
        LIMIT 5
        """)
        
        recent_items = [dict(row) for row in c.fetchall()]
        conn.close()
        
        # Формируем сообщение
        message_text = f"💾 <b>Кэш ответов</b> (всего: {cache_count})\n\n"
        
        if recent_items:
            message_text += "<b>Последние записи:</b>\n"
            for i, item in enumerate(recent_items):
                # Ограничиваем длину вопроса
                question = item["question"]
                if len(question) > 50:
                    question = question[:47] + "..."
                
                message_text += f"{i+1}. {question}\n"
        else:
            message_text += "Кэш пуст."
        
        # Формируем кнопки
        keyboard = [
            [InlineKeyboardButton("🧹 Очистить кэш", callback_data="admin_db:cache:clear")],
            [InlineKeyboardButton("◀️ Назад", callback_data=DB_BACK)]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Обновляем сообщение
        await update.callback_query.message.edit_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения информации о кэше: {e}")
        await update.callback_query.message.edit_text(
            "❌ <b>Ошибка получения информации о кэше</b>\n\n"
            f"Детали: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_BACK)]]),
            parse_mode=ParseMode.HTML
        )

async def handle_cache_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает действия с кэшем ответов"""
    query = update.callback_query
    action = query.data.split(":")[-1]
    
    if action == "clear":
        # Очищаем кэш
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM cache")
            conn.commit()
            conn.close()
            
            await query.message.edit_text(
                "✅ <b>Кэш успешно очищен!</b>\n\n"
                "Все кэшированные ответы удалены.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_CACHE)]]),
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Ошибка очистки кэша: {e}")
            await query.message.edit_text(
                "❌ <b>Ошибка очистки кэша</b>\n\n"
                f"Детали: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_CACHE)]]),
                parse_mode=ParseMode.HTML
            )

async def handle_pdf_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает меню управления PDF-документами"""
    # Получаем информацию о PDF-файлах
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Получаем список PDF-файлов
        c.execute("""
        SELECT file_hash, filename, page_count, indexed 
        FROM pdf_files 
        ORDER BY timestamp DESC
        """)
        
        pdf_files = [dict(row) for row in c.fetchall()]
        conn.close()
        
        # Формируем сообщение
        message_text = f"📄 <b>PDF-документы</b> (всего: {len(pdf_files)})\n\n"
        
        if pdf_files:
            for i, file in enumerate(pdf_files[:5]):  # Показываем только первые 5 файлов
                status = "✅" if file["indexed"] == 1 else "⏳"
                message_text += f"{i+1}. {status} {file['filename']} ({file['page_count']} стр.)\n"
            
            if len(pdf_files) > 5:
                message_text += f"\n...и еще {len(pdf_files) - 5} файлов\n"
        else:
            message_text += "Нет загруженных PDF-файлов."
        
        # Формируем кнопки
        keyboard = [
            [InlineKeyboardButton("➕ Загрузить PDF", callback_data="admin_db:pdf:upload")],
            [InlineKeyboardButton("🔄 Обновить индекс PDF", callback_data="admin_db:pdf:update_index")],
            [InlineKeyboardButton("◀️ Назад", callback_data=DB_BACK)]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Обновляем сообщение
        await update.callback_query.message.edit_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения информации о PDF-файлах: {e}")
        await update.callback_query.message.edit_text(
            "❌ <b>Ошибка получения информации о PDF-файлах</b>\n\n"
            f"Детали: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_BACK)]]),
            parse_mode=ParseMode.HTML
        )

async def handle_pdf_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает действия с PDF-документами"""
    query = update.callback_query
    action = query.data.split(":")[-1]
    
    if action == "upload":
        # Сообщаем о возможности загрузки PDF через команду /add_pdf
        await query.message.edit_text(
            "➕ <b>Загрузка PDF-документа</b>\n\n"
            "Для загрузки PDF-файла используйте команду /add_pdf\n"
            "После загрузки новый документ будет автоматически проиндексирован.\n\n"
            "Для обновления индекса всех PDF-файлов используйте кнопку 'Обновить индекс PDF'.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_PDF)]]),
            parse_mode=ParseMode.HTML
        )
    
    elif action == "update_index":
        # Обновляем индекс PDF
        await query.message.edit_text(
            "🔄 <b>Обновление индекса PDF</b>\n\n"
            "Началось обновление индекса PDF-документов. Это может занять некоторое время...",
            parse_mode=ParseMode.HTML
        )
        
        # Запускаем обновление индекса
        success = await update_all_pdf_index()
        
        if success:
            await query.message.edit_text(
                "✅ <b>Индекс PDF успешно обновлен!</b>\n\n"
                "Изменения вступили в силу.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_PDF)]]),
                parse_mode=ParseMode.HTML
            )
        else:
            await query.message.edit_text(
                "❌ <b>Ошибка обновления индекса PDF</b>\n\n"
                "Не удалось обновить индекс. Проверьте логи для подробностей.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_PDF)]]),
                parse_mode=ParseMode.HTML
            )

async def handle_unanswered_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает меню управления неотвеченными вопросами"""
    # Получаем информацию о неотвеченных вопросах
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Получаем количество записей
        c.execute("SELECT COUNT(*) FROM unanswered_questions WHERE answered=0")
        unanswered_count = c.fetchone()[0]
        
        # Получаем несколько последних записей
        c.execute("""
        SELECT id, user_id, question, timestamp 
        FROM unanswered_questions 
        WHERE answered=0
        ORDER BY timestamp DESC 
        LIMIT 5
        """)
        
        recent_items = [dict(row) for row in c.fetchall()]
        conn.close()
        
        # Формируем сообщение
        message_text = f"❓ <b>Неотвеченные вопросы</b> (всего: {unanswered_count})\n\n"
        
        if recent_items:
            for i, item in enumerate(recent_items):
                # Ограничиваем длину вопроса
                question = item["question"]
                if len(question) > 50:
                    question = question[:47] + "..."
                
                message_text += f"{i+1}. [User: {item['user_id']}] {question}\n"
        else:
            message_text += "Нет неотвеченных вопросов."
        
        # Формируем кнопки
        keyboard = [
            [InlineKeyboardButton("📝 Ответить", callback_data="admin_db:unanswered:answer")],
            [InlineKeyboardButton("🧹 Очистить все", callback_data="admin_db:unanswered:clear_all")],
            [InlineKeyboardButton("◀️ Назад", callback_data=DB_BACK)]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Обновляем сообщение
        await update.callback_query.message.edit_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения информации о неотвеченных вопросах: {e}")
        await update.callback_query.message.edit_text(
            "❌ <b>Ошибка получения информации о неотвеченных вопросах</b>\n\n"
            f"Детали: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_BACK)]]),
            parse_mode=ParseMode.HTML
        )

async def handle_unanswered_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает действия с неотвеченными вопросами"""
    query = update.callback_query
    action = query.data.split(":")[-1]
    
    if action == "answer":
        # Выводим список неотвеченных вопросов для ответа
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Получаем записи для ответа
            c.execute("""
            SELECT id, user_id, question, timestamp 
            FROM unanswered_questions 
            WHERE answered=0
            ORDER BY timestamp DESC 
            LIMIT 10
            """)
            
            items = [dict(row) for row in c.fetchall()]
            conn.close()
            
            if not items:
                await query.message.edit_text(
                    "✅ <b>Все вопросы отвечены!</b>\n\n"
                    "Нет неотвеченных вопросов.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_UNANSWERED)]]),
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Формируем сообщение
            message_text = "📝 <b>Ответить на вопрос</b>\n\n"
            message_text += "Выберите вопрос, на который хотите ответить:\n\n"
            
            # Формируем кнопки
            keyboard = []
            for i, item in enumerate(items):
                # Ограничиваем длину вопроса
                question = item["question"]
                if len(question) > 30:
                    question = question[:27] + "..."
                
                keyboard.append([InlineKeyboardButton(
                    f"{i+1}. {question}",
                    callback_data=f"admin_db:unanswered:answer_to:{item['id']}"
                )])
            
            keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=DB_UNANSWERED)])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Обновляем сообщение
            await query.message.edit_text(
                message_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Ошибка получения вопросов для ответа: {e}")
            await query.message.edit_text(
                "❌ <b>Ошибка получения вопросов для ответа</b>\n\n"
                f"Детали: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_UNANSWERED)]]),
                parse_mode=ParseMode.HTML
            )
    
    elif action == "clear_all":
        # Очищаем все неотвеченные вопросы
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Отмечаем все вопросы как отвеченные
            c.execute("UPDATE unanswered_questions SET answered=1 WHERE answered=0")
            conn.commit()
            conn.close()
            
            await query.message.edit_text(
                "✅ <b>Все неотвеченные вопросы очищены!</b>\n\n"
                "Все вопросы отмечены как отвеченные.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_UNANSWERED)]]),
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Ошибка очистки неотвеченных вопросов: {e}")
            await query.message.edit_text(
                "❌ <b>Ошибка очистки неотвеченных вопросов</b>\n\n"
                f"Детали: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_UNANSWERED)]]),
                parse_mode=ParseMode.HTML
            )
            
    elif action.startswith("answer_to:"):
        # Обработка ответа на конкретный вопрос
        question_id = int(action.split(":")[-1])
        
        # Получаем информацию о вопросе
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("SELECT * FROM unanswered_questions WHERE id=?", (question_id,))
            question_data = dict(c.fetchone())
            
            # Отмечаем вопрос как отвеченный
            c.execute("UPDATE unanswered_questions SET answered=1 WHERE id=?", (question_id,))
            conn.commit()
            conn.close()
            
            # Сохраняем данные для последующего использования
            context.user_data['current_question'] = question_data
            
            # Предлагаем добавить вопрос в базу знаний
            await query.message.edit_text(
                f"📝 <b>Ответ на вопрос #{question_id}</b>\n\n"
                f"<b>Вопрос:</b> {question_data['question']}\n\n"
                f"Вопрос отмечен как отвеченный. Хотите добавить его в базу знаний?\n\n"
                f"Для этого используйте команду /teach и следуйте инструкциям.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_UNANSWERED)]]),
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Ошибка обработки ответа на вопрос: {e}")
            await query.message.edit_text(
                "❌ <b>Ошибка обработки ответа на вопрос</b>\n\n"
                f"Детали: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_UNANSWERED)]]),
                parse_mode=ParseMode.HTML
            )

async def handle_export_db(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает экспорт базы знаний"""
    query = update.callback_query
    
    # Формируем сообщение
    message_text = "📤 <b>Экспорт базы знаний</b>\n\n"
    message_text += "Начат процесс экспорта базы знаний..."
    
    await query.message.edit_text(
        message_text,
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Загружаем базу знаний
        knowledge = load_knowledge()
        
        # Создаем JSON-файл
        export_path = "knowledge_export.json"
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(knowledge, f, ensure_ascii=False, indent=2)
        
        # Отправляем файл пользователю
        with open(export_path, "rb") as f:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=f,
                filename=f"knowledge_export_{datetime.now().strftime('%Y%m%d')}.json",
                caption="✅ База знаний успешно экспортирована"
            )
        
        # Удаляем временный файл
        os.remove(export_path)
        
        # Обновляем сообщение
        await query.message.edit_text(
            "✅ <b>База знаний успешно экспортирована!</b>\n\n"
            "Файл с базой знаний отправлен.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_BACK)]]),
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Ошибка экспорта базы знаний: {e}")
        await query.message.edit_text(
            "❌ <b>Ошибка экспорта базы знаний</b>\n\n"
            f"Детали: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_BACK)]]),
            parse_mode=ParseMode.HTML
        )

async def handle_import_db(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает импорт базы знаний"""
    query = update.callback_query
    
    # Сообщаем о начале процесса импорта
    await query.message.edit_text(
        "📥 <b>Импорт базы знаний</b>\n\n"
        "Для импорта базы знаний отправьте JSON-файл с базой в ответ на это сообщение.\n\n"
        "<i>⚠️ Внимание! Импорт перезапишет существующую базу знаний!</i>",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Отмена", callback_data=DB_BACK)]]),
        parse_mode=ParseMode.HTML
    )
    
    # Устанавливаем режим ожидания файла
    context.user_data['awaiting_import'] = True
    
    # ID сообщения для последующего обновления
    context.user_data['import_message_id'] = query.message.message_id

async def handle_clear_cache(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает очистку кэша"""
    query = update.callback_query
    
    # Сообщаем о начале процесса очистки
    await query.message.edit_text(
        "🧹 <b>Очистка кэша</b>\n\n"
        "Начата очистка кэша...",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Очищаем кэш
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Получаем количество записей до очистки
        c.execute("SELECT COUNT(*) FROM cache")
        before_count = c.fetchone()[0]
        
        # Очищаем таблицу кэша
        c.execute("DELETE FROM cache")
        
        # Очищаем таблицу PDF-кэша
        c.execute("DELETE FROM pdf_cache")
        
        conn.commit()
        conn.close()
        
        # Обновляем сообщение
        await query.message.edit_text(
            f"✅ <b>Кэш успешно очищен!</b>\n\n"
            f"Удалено {before_count} записей из кэша ответов и записи из кэша PDF.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_BACK)]]),
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Ошибка очистки кэша: {e}")
        await query.message.edit_text(
            "❌ <b>Ошибка очистки кэша</b>\n\n"
            f"Детали: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=DB_BACK)]]),
            parse_mode=ParseMode.HTML
        )
