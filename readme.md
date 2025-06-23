# Notifications API

Этот проект реализует сервис уведомлений для курсовой работы (HSE Coursework). Сервис предоставляет REST API для отправки уведомлений

![](https://github.com/HSE-COURSEWORK-2025/hse-coursework-notifications-api/blob/master/swagger_demo.png)

## Основные возможности
- Отправка email-уведомлений
- Хранение уведомлений в PostgreSQL
- Выдача уведомлений непрочитанных/всех уведомлений
- трансляция статуса наличия уведомлений


## Быстрый старт (локально)
1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Запустите сервис:
   ```bash
   python launcher.py
   ```

## Docker
Сборка и запуск контейнера:
```bash
docker build -t awesomecosmonaut/notifications-api-app .
docker run -p 8080:8080 --env-file .env awesomecosmonaut/notifications-api-app
```

## Деплой в Kubernetes
1. Скрипт запуска:
   ```bash
   ./deploy.sh
   ```
2. Скрипт остановки:
   ```bash
   ./stop.sh
   ```

## Переменные окружения
См. файлы `.env` и `.env.development` для настройки подключения к БД, Kafka, Redis и email.

### Пример .env
```env
ROOT_PATH=/notifications-api
PORT=8080
DB_HOST=your_db_host
REDIS_HOST=your_redis_host
AUTH_API_URL=http://auth-api:8081
KAFKA_BOOTSTRAP_SERVERS=your_kafka_bootstrap_servers
EMAIL_USERNAME=your_email@example.com
EMAIL_PASSWORD=your_email_password
```

### Пример .env.development
```env
ROOT_PATH=/notifications-api
PORT=8083
DB_HOST=localhost
AUTH_API_URL=http://localhost:8081
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
EMAIL_USERNAME=your_email@example.com
EMAIL_PASSWORD=your_email_password
```

## Структура репозитория
- `app/` — исходный код FastAPI-приложения
- `deployment/` — манифесты Kubernetes
- `requirements.txt` — зависимости Python
- `Dockerfile` — сборка контейнера
- `deploy.sh`, `stop.sh` — скрипты деплоя
