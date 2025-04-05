FROM python:3.10-slim

# Установка зависимостей для сборки и работы
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    sqlite3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование зависимостей и установка
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Создание пользователя с ограниченными правами
RUN useradd -m botuser && \
    mkdir -p /app/data /app/models /app/logs /app/backups && \
    chown -R botuser:botuser /app

# Копирование кода приложения
COPY root/ /app/root/
COPY tests/ /app/tests/
COPY docker-entrypoint.sh /app/

# Установка прав на entrypoint
RUN chmod +x /app/docker-entrypoint.sh

# Переключение на пользователя с ограниченными правами
USER botuser

# Объявление томов для данных и конфигурации
VOLUME ["/app/data", "/app/models", "/app/logs", "/app/backups"]

# Переменные окружения по умолчанию
ENV APP_ENV=production \
    LOG_LEVEL=INFO \
    DB_PATH=/app/data/bot.db \
    MISTRAL_MODEL_PATH=/app/models/mistral-7b-instruct-v0.3.Q4_K_M.gguf

# Entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Запуск бота по умолчанию
CMD ["python", "-m", "root.main"]
