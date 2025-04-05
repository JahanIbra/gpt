# Исламский бот-ассистент (Islamic Bot Assistant)

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=hetzner-bot&metric=alert_status)](https://sonarcloud.io/dashboard?id=hetzner-bot)

Telegram-бот, который отвечает на вопросы об исламе с использованием локальной языковой модели (LLM), базы знаний и PDF-документов.

## Особенности

- 🤖 Автономная работа на базе локальной языковой модели Mistral 7B
- 📚 Встроенная база знаний с возможностью пополнения
- 📄 Поиск информации в PDF-документах
- 🔍 Векторный поиск для точного сопоставления запросов
- 🔒 Работа без подключения к внешним API
- 🛠️ Административная панель для управления ботом
- 💾 Система резервного копирования данных
- 📊 Мониторинг системных ресурсов

## Требования

- Python 3.9+
- Не менее 8 ГБ оперативной памяти
- Не менее 10 ГБ свободного места на диске
- Telegram API ключ от @BotFather

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/islamic-bot-assistant.git
cd islamic-bot-assistant
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` и настройте конфигурацию:
```bash
cp .env.example .env
# Отредактируйте .env файл, добавив свой TELEGRAM_TOKEN и другие параметры
```

4. Загрузите модель (будет выполнено автоматически при первом запуске или вручную):
```bash
python download_model.py
```

5. Запустите бота:
```bash
python main.py
```

## Структура проекта

```
/
├── main.py                  # Основной файл запуска
├── config.py                # Конфигурационные параметры
├── models.py                # Взаимодействие с языковой моделью
├── telegram_handlers.py     # Обработчики команд Telegram
├── answer_generator.py      # Генерация ответов на вопросы
├── vector_search.py         # Векторный поиск по базе знаний
├── pdf_handler.py           # Обработка и индексация PDF
├── database.py              # Взаимодействие с базой данных
├── backup_manager.py        # Управление резервными копиями
├── system_monitor.py        # Мониторинг системных ресурсов
├── security.py              # Безопасность и ограничения доступа
├── localization.py          # Локализация сообщений
├── error_handler.py         # Обработка ошибок
└── download_model.py        # Скрипт загрузки модели
```

## Использование

1. **Пользователь**: Просто отправьте боту вопрос об исламе, и он попытается дать на него ответ.

2. **Администратор**: Используйте командную панель администратора для управления:
   - `/admin` - Доступ к панели администратора
   - `/teach` - Добавить новую запись в базу знаний
   - `/add_pdf` - Загрузить PDF-документ для индексации
   - `/update_index` - Обновить индекс базы знаний
   - `/backup` - Создать резервную копию данных
   - `/stats` - Просмотреть статистику использования

## Административный доступ

Для получения прав администратора добавьте свой Telegram ID в переменную `ADMIN_IDS` в файле `.env`:

```
ADMIN_IDS=123456789,987654321
```

## Резервное копирование

Система автоматически создает резервные копии данных. Для ручного создания резервной копии:

```bash
python -c "import asyncio; from backup_manager import backup_manager; asyncio.run(backup_manager.create_full_backup())"
```

## Анализ качества кода

Этот проект использует SonarCloud для непрерывного анализа качества кода. Результаты анализа доступны на [странице проекта в SonarCloud](https://sonarcloud.io/dashboard?id=hetzner-bot).

Для получения информации о настройке SonarCloud, обратитесь к [руководству по настройке](./docs/sonarcloud-setup.md).

## Вклад в проект

Вклады в проект приветствуются! Пожалуйста, следуйте этим шагам:

1. Форкните репозиторий
2. Создайте ветку для своей функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add some amazing feature'`)
4. Отправьте ветку в свой форк (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для получения подробной информации.
