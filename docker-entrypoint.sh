#!/bin/bash
set -e

# Применение миграций базы данных
echo "Применение миграций базы данных..."
python -m root.db_migration

# Если модель не существует, скачиваем её
if [ ! -f "$MISTRAL_MODEL_PATH" ]; then
    echo "Модель не найдена. Загрузка модели..."
    python -m root.download_model
fi

# Запуск мониторинга системных ресурсов в фоновом режиме
if [ "$ENABLE_MONITORING" = "true" ]; then
    echo "Запуск мониторинга системных ресурсов..."
    python -m root.system_monitor &
fi

# Дополнительные проверки перед запуском
python -m root.diagnostics

# Выполнение команды из CMD
echo "Запуск приложения: $@"
exec "$@"
