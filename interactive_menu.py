import asyncio
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
import json
import os
import re

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import ADMIN_IDS, logger
from localization import _
from error_handler import catch_exceptions
from database import load_knowledge, save_knowledge
from vector_search import update_faiss_index
from pdf_handler import update_all_pdf_index

class MenuBuilder:
    """Класс для создания интерактивных меню"""
    
    def __init__(self, title: str = "", description: str = "", back_button_text: str = "◀️ Назад"):
        """
        Инициализирует построитель меню
        
        Args:
            title: Заголовок меню
            description: Описание меню
            back_button_text: Текст кнопки "Назад"
        """
        self.title = title
        self.description = description
        self.buttons = []
        self.back_button_text = back_button_text
        self.back_callback = None
    
    def add_button(self, text: str, callback_data: str):
        """
        Добавляет кнопку в меню
        
        Args:
            text: Текст кнопки
            callback_data: Данные обратного вызова
        """
        self.buttons.append(InlineKeyboardButton(text, callback_data=callback_data))
        return self
    
    def add_url_button(self, text: str, url: str):
        """
        Добавляет кнопку со ссылкой
        
        Args:
            text: Текст кнопки
            url: URL ссылки
        """
        self.buttons.append(InlineKeyboardButton(text, url=url))
        return self
    
    def add_row(self, buttons: List[InlineKeyboardButton]):
        """
        Добавляет ряд кнопок
        
        Args:
            buttons: Список кнопок в ряду
        """
        self.buttons.append(buttons)
        return self
    
    def set_back_button(self, text: str = None, callback_data: str = None):
        """
        Устанавливает кнопку "Назад"
        
        Args:
            text: Текст кнопки (если None, используется значение по умолчанию)
            callback_data: Данные обратного вызова
        """
        if text is None:
            text = self.back_button_text
        
        self.back_callback = callback_data
        return self
    
    def build(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Создает меню с заданными параметрами
        
        Returns:
            Кортеж (текст сообщения, клавиатура)
        """
        # Формируем текст сообщения
        message_text = ""
        if self.title:
            message_text += f"<b>{self.title}</b>\n\n"
        
        if self.description:
            message_text += f"{self.description}\n\n"
        
        # Формируем клавиатуру
        keyboard = []
        
        # Если buttons - плоский список, создаем клавиатуру с одной кнопкой в ряду
        if all(isinstance(btn, InlineKeyboardButton) for btn in self.buttons):
            for button in self.buttons:
                keyboard.append([button])
        else:
            # Иначе, используем вложенную структуру
            for item in self.buttons:
                if isinstance(item, list):
                    keyboard.append(item)
                else:
                    keyboard.append([item])
        
        # Добавляем кнопку "Назад", если задана
        if self.back_callback:
            keyboard.append([InlineKeyboardButton(self.back_button_text, callback_data=self.back_callback)])
        
        return message_text, InlineKeyboardMarkup(keyboard)

@catch_exceptions()
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, menu_id: str) -> None:
    """
    Обрабатывает выбор пункта меню
    
    Args:
        update: Объект обновления
        context: Контекст бота
        menu_id: Идентификатор меню
    """
    query = update.callback_query
    
    # Определяем, какое меню отобразить
    menu_handlers = {
        "main_menu": show_main_menu,
        "admin_menu": show_admin_menu,
        "knowledge_menu": show_knowledge_menu,
        "pdf_menu": show_pdf_menu,
        "backup_menu": show_backup_menu,
        "settings_menu": show_settings_menu,
        "stats_menu": show_stats_menu
    }
    
    # Вызываем соответствующий обработчик
    if menu_id in menu_handlers:
        await menu_handlers[menu_id](update, context)
    else:
        logger.warning(f"Неизвестный идентификатор меню: {menu_id}")
        await query.answer("Меню недоступно")

@catch_exceptions()
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает главное меню"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Создаем меню в зависимости от того, админ ли пользователь
    menu = MenuBuilder(
        title="🤖 Главное меню",
        description="Выберите действие:"
    )
    
    menu.add_button("❓ Задать вопрос", callback_data="action:ask_question")
    menu.add_button("📚 О боте", callback_data="action:about_bot")
    
    if user_id in ADMIN_IDS:
        menu.add_button("🔧 Панель администратора", callback_data="menu:admin_menu")
    
    message_text, reply_markup = menu.build()
    
    if query:
        await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        # Если это не колбэк, а прямой вызов функции
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

@catch_exceptions()
async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает административное меню"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await query.answer(_("admin_required"))
        return
    
    menu = MenuBuilder(
        title="🔧 Панель администратора",
        description="Выберите раздел для управления:"
    )
    
    menu.add_button("📚 База знаний", callback_data="menu:knowledge_menu")
    menu.add_button("📄 PDF-документы", callback_data="menu:pdf_menu")
    menu.add_button("📊 Статистика", callback_data="menu:stats_menu")
    menu.add_button("💾 Резервное копирование", callback_data="menu:backup_menu")
    menu.add_button("⚙️ Настройки", callback_data="menu:settings_menu")
    menu.set_back_button(callback_data="menu:main_menu")
    
    message_text, reply_markup = menu.build()
    
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

@catch_exceptions()
async def show_knowledge_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню управления базой знаний"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await query.answer(_("admin_required"))
        return
    
    # Получаем статистику базы знаний
    knowledge = load_knowledge()
    
    menu = MenuBuilder(
        title="📚 Управление базой знаний",
        description=f"Всего записей: {len(knowledge)}\n\nВыберите действие:"
    )
    
    menu.add_button("➕ Добавить запись", callback_data="action:add_knowledge")
    menu.add_button("👁️ Просмотр базы знаний", callback_data="action:view_knowledge")
    menu.add_button("📤 Экспорт базы", callback_data="action:export_knowledge")
    menu.add_button("📥 Импорт базы", callback_data="action:import_knowledge")
    menu.add_button("🔄 Обновить индекс", callback_data="action:update_knowledge_index")
    menu.set_back_button(callback_data="menu:admin_menu")
    
    message_text, reply_markup = menu.build()
    
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

@catch_exceptions()
async def show_pdf_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню управления PDF-документами"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await query.answer(_("admin_required"))
        return
    
    # Получаем количество PDF-файлов
    pdf_dir = os.path.join(os.path.dirname(__file__), 'data', 'pdf_docs')
    pdf_count = 0
    
    if os.path.exists(pdf_dir):
        pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
        pdf_count = len(pdf_files)
    
    menu = MenuBuilder(
        title="📄 Управление PDF-документами",
        description=f"Всего документов: {pdf_count}\n\nВыберите действие:"
    )
    
    menu.add_button("➕ Добавить PDF", callback_data="action:add_pdf")
    menu.add_button("👁️ Просмотр документов", callback_data="action:view_pdf")
    menu.add_button("🔄 Обновить индекс PDF", callback_data="action:update_pdf_index")
    menu.set_back_button(callback_data="menu:admin_menu")
    
    message_text, reply_markup = menu.build()
    
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

@catch_exceptions()
async def show_backup_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню управления резервными копиями"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await query.answer(_("admin_required"))
        return
    
    # Получаем количество резервных копий
    from backup_manager import backup_manager
    backups = await backup_manager.list_backups()
    
    menu = MenuBuilder(
        title="💾 Управление резервными копиями",
        description=f"Всего резервных копий: {len(backups)}\n\nВыберите действие:"
    )
    
    menu.add_button("📦 Создать резервную копию", callback_data="action:create_backup")
    menu.add_button("📋 Список резервных копий", callback_data="action:list_backups")
    menu.add_button("📥 Восстановить из копии", callback_data="action:restore_backup")
    menu.set_back_button(callback_data="menu:admin_menu")
    
    message_text, reply_markup = menu.build()
    
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

@catch_exceptions()
async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню настроек"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await query.answer(_("admin_required"))
        return
    
    menu = MenuBuilder(
        title="⚙️ Настройки",
        description="Выберите раздел настроек:"
    )
    
    menu.add_button("🤖 Параметры бота", callback_data="action:bot_settings")
    menu.add_button("🔒 Безопасность", callback_data="action:security_settings")
    menu.add_button("🌐 Локализация", callback_data="action:localization_settings")
    menu.add_button("📊 Мониторинг", callback_data="action:monitoring_settings")
    menu.set_back_button(callback_data="menu:admin_menu")
    
    message_text, reply_markup = menu.build()
    
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

@catch_exceptions()
async def show_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню статистики"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await query.answer(_("admin_required"))
        return
    
    menu = MenuBuilder(
        title="📊 Статистика",
        description="Выберите тип статистики:"
    )
    
    menu.add_button("👥 Пользователи", callback_data="action:user_stats")
    menu.add_button("🔍 Запросы", callback_data="action:query_stats")
    menu.add_button("📈 Использование", callback_data="action:usage_stats")
    menu.add_button("💻 Система", callback_data="action:system_stats")
    menu.set_back_button(callback_data="menu:admin_menu")
    
    message_text, reply_markup = menu.build()
    
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

@catch_exceptions()
async def handle_menu_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str) -> None:
    """
    Обрабатывает действие из меню
    
    Args:
        update: Объект обновления
        context: Контекст бота
        action: Идентификатор действия
    """
    query = update.callback_query
    
    # Определяем обработчик для действия
    action_handlers = {
        "ask_question": handle_ask_question,
        "about_bot": handle_about_bot,
        "add_knowledge": handle_add_knowledge,
        "view_knowledge": handle_view_knowledge,
        "export_knowledge": handle_export_knowledge,
        "import_knowledge": handle_import_knowledge,
        "update_knowledge_index": handle_update_knowledge_index,
        "add_pdf": handle_add_pdf,
        "view_pdf": handle_view_pdf,
        "update_pdf_index": handle_update_pdf_index,
        "create_backup": handle_create_backup,
        "list_backups": handle_list_backups,
        "restore_backup": handle_restore_backup,
        "bot_settings": handle_bot_settings,
        "security_settings": handle_security_settings,
        "localization_settings": handle_localization_settings,
        "monitoring_settings": handle_monitoring_settings,
        "user_stats": handle_user_stats,
        "query_stats": handle_query_stats,
        "usage_stats": handle_usage_stats,
        "system_stats": handle_system_stats
    }
    
    # Вызываем соответствующий обработчик
    if action in action_handlers:
        await action_handlers[action](update, context)
    else:
        logger.warning(f"Неизвестное действие меню: {action}")
        await query.answer("Действие недоступно")

@catch_exceptions()
async def handle_ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает действие 'Задать вопрос'"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔍 Пожалуйста, напишите ваш вопрос в следующем сообщении."
    )

@catch_exceptions()
async def handle_about_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает действие 'О боте'"""
    query = update.callback_query
    
    about_text = (
        "🤖 <b>О боте</b>\n\n"
        "Я - бот на основе искусственного интеллекта, созданный для ответов на вопросы об исламе.\n\n"
        "🔍 Я использую:\n"
        "• Базу знаний с проверенной информацией\n"
        "• Индексированные PDF-документы от надежных источников\n"
        "• Языковую модель для формирования ответов\n\n"
        "📚 Вы можете задать любой вопрос об исламе, и я постараюсь найти на него ответ.\n\n"
        "<i>Помните, что я лишь инструмент и могу ошибаться. "
        "По важным религиозным вопросам всегда консультируйтесь с имамом или учёным.</i>"
    )
    
    menu = MenuBuilder()
    menu.set_back_button(callback_data="menu:main_menu")
    
    _, reply_markup = menu.build()
    
    await query.edit_message_text(
        about_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

@catch_exceptions()
async def handle_add_knowledge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает действие 'Добавить запись' в базу знаний"""
    query = update.callback_query
    
    # Устанавливаем состояние пользователя для последующего обработчика
    context.user_data["state"] = "awaiting_knowledge_question"
    
    await query.edit_message_text(
        "📝 <b>Добавление записи в базу знаний</b>\n\n"
        "Введите вопрос для добавления в базу знаний:",
        parse_mode=ParseMode.HTML
    )

@catch_exceptions()
async def handle_update_knowledge_index(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает действие 'Обновить индекс базы знаний'"""
    query = update.callback_query
    
    # Показываем сообщение о процессе
    await query.edit_message_text(
        "🔄 <b>Обновление индекса</b>\n\n"
        "Выполняется обновление индекса базы знаний...",
        parse_mode=ParseMode.HTML
    )
    
    # Обновляем индекс
    success = await update_faiss_index()
    
    if success:
        menu = MenuBuilder()
        menu.set_back_button(callback_data="menu:knowledge_menu")
        _, reply_markup = menu.build()
        
        await query.edit_message_text(
            "✅ <b>Индекс успешно обновлен</b>\n\n"
            "Индекс базы знаний обновлен и готов к использованию.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    else:
        menu = MenuBuilder()
        menu.set_back_button(callback_data="menu:knowledge_menu")
        _, reply_markup = menu.build()
        
        await query.edit_message_text(
            "❌ <b>Ошибка обновления индекса</b>\n\n"
            "Произошла ошибка при обновлении индекса. Проверьте логи для подробностей.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

@catch_exceptions()
async def handle_update_pdf_index(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает действие 'Обновить индекс PDF'"""
    query = update.callback_query
    
    # Показываем сообщение о процессе
    await query.edit_message_text(
        "🔄 <b>Обновление индекса PDF</b>\n\n"
        "Выполняется обновление индекса PDF-документов...",
        parse_mode=ParseMode.HTML
    )
    
    # Обновляем индекс
    success = await update_all_pdf_index()
    
    if success:
        menu = MenuBuilder()
        menu.set_back_button(callback_data="menu:pdf_menu")
        _, reply_markup = menu.build()
        
        await query.edit_message_text(
            "✅ <b>Индекс PDF успешно обновлен</b>\n\n"
            "Индекс PDF-документов обновлен и готов к использованию.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    else:
        menu = MenuBuilder()
        menu.set_back_button(callback_data="menu:pdf_menu")
        _, reply_markup = menu.build()
        
        await query.edit_message_text(
            "❌ <b>Ошибка обновления индекса PDF</b>\n\n"
            "Произошла ошибка при обновлении индекса. Проверьте логи для подробностей.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
