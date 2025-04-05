#!/bin/bash

# Определяем директорию проекта
PROJECT_DIR="/home/codespace/hetzner"

# Проверяем наличие токена
if [ -z "$SONAR_TOKEN" ]; then
    # Пытаемся загрузить токен из файла .env, если он существует
    if [ -f "$PROJECT_DIR/.env" ]; then
        source "$PROJECT_DIR/.env"
    fi
    
    # Если токен всё ещё не установлен, запрашиваем его
    if [ -z "$SONAR_TOKEN" ]; then
        echo "Пожалуйста, введите ваш SONAR_TOKEN (токен не будет отображаться):"
        read -s SONAR_TOKEN
        echo "Токен получен."
    fi
fi

# Установка SonarScanner, если его нет
if [ ! -d "$PROJECT_DIR/sonar-scanner" ]; then
    echo "Устанавливаем SonarScanner..."
    wget https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-4.8.0.2856-linux.zip
    unzip sonar-scanner-cli-4.8.0.2856-linux.zip
    mv sonar-scanner-4.8.0.2856-linux sonar-scanner
    rm sonar-scanner-cli-4.8.0.2856-linux.zip
fi

# Запускаем сканирование
echo "Запускаем анализ кода..."
$PROJECT_DIR/sonar-scanner/bin/sonar-scanner \
  -Dsonar.projectBaseDir=$PROJECT_DIR \
  -Dsonar.token=$SONAR_TOKEN

echo "Анализ завершен. Результаты доступны на https://sonarcloud.io/organizations/jahanibra/projects"
