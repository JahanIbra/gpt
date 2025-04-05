#!/bin/bash

# Определяем директорию для хранения модели
MODEL_DIR="/home/codespace/hetzner/models"
MODEL_NAME="Mistral-7B-Instruct-v0.3-Q4_K_M.ggu"
MODEL_URL="https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/mistral-7b-instruct-v0.3.Q4_K_M.gguf"

# Директория конфигурации бота
BOT_CONFIG_DIR="/home/codespace/hetzner/bot_config"

# Создаем директории, если они не существуют
mkdir -p "$MODEL_DIR"
mkdir -p "$BOT_CONFIG_DIR"

echo "Проверка наличия модели $MODEL_NAME..."

# Проверяем, есть ли уже модель
if [ -f "$MODEL_DIR/$MODEL_NAME" ]; then
    echo "Найдена существующая модель. Создание резервной копии..."
    cp "$MODEL_DIR/$MODEL_NAME" "$MODEL_DIR/${MODEL_NAME}.backup"
else
    echo "Модель не найдена. Будет выполнено первоначальное скачивание."
fi

# Скачиваем последнюю версию модели
echo "Скачивание модели $MODEL_NAME..."
wget -O "$MODEL_DIR/$MODEL_NAME" "$MODEL_URL"

# Проверяем успешность скачивания
if [ $? -eq 0 ]; then
    echo "Модель успешно скачана!"
    
    # Настройка модели для бота
    echo "Настройка модели для вашего бота..."
    
    # Создаем файл конфигурации для бота, чтобы он знал, где находится модель
    cat > "$BOT_CONFIG_DIR/model_config.json" << EOF
{
    "model_path": "$MODEL_DIR/$MODEL_NAME",
    "model_type": "mistral",
    "model_parameters": {
        "temperature": 0.7,
        "top_p": 0.95,
        "max_length": 2048
    }
}
EOF
    
    echo "Модель готова к использованию вашим ботом!"
    echo "Путь к модели: $MODEL_DIR/$MODEL_NAME"
    echo "Файл конфигурации создан в: $BOT_CONFIG_DIR/model_config.json"
else
    echo "Ошибка при скачивании модели."
    if [ -f "$MODEL_DIR/${MODEL_NAME}.backup" ]; then
        echo "Восстановление из резервной копии..."
        mv "$MODEL_DIR/${MODEL_NAME}.backup" "$MODEL_DIR/$MODEL_NAME"
    fi
fi
