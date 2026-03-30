# Error Gateway — Полная документация

**Автономный микросервис для трекинга ошибок с уведомлениями через Telegram/Email**

[← На главную](../README.md) | [🇬🇧 English version](README_en.md)

---

## 📋 Содержание

1. [О проекте](#о-проекта)
2. [Установка](#установка)
   - [Требования](#требования)
   - [Docker (рекомендуется)](#docker-рекомендуется)
   - [Локальная разработка](#локальная-разработка)
3. [Настройка](#настройка)
   - [Переменные окружения](#переменные-окружения)
   - [Режимы работы](#режимы-работы)
   - [Примеры .env](#примеры-env)
4. [API](#api)
   - [Отправить ошибку](#отправить-ошибку)
   - [Получить ошибки](#получить-ошибки)
   - [Health check](#health-check)
   - [Metrics](#metrics)
5. [Уведомления](#уведомления)
   - [Telegram](#telegram)
   - [Email](#email)
   - [Настройка троттлинга](#настройка-троттлинга)
6. [Интеграции](#интеграции)
   - [Grafana Loki](#grafana-loki)
   - [Примеры кода](#примеры-кода)
7. [Production](#production)
   - [Развёртывание](#развёртывание)
   - [Масштабирование](#масштабирование)
   - [Мониторинг](#мониторинг)
8. [Troubleshooting](#troubleshooting)
   - [Частые проблемы](#частые-проблемы)
   - [FAQ](#faq)

---

## 🎯 О проекте

**Error Gateway** — автономный микросервис для централизованного сбора и обработки ошибок с автоматическими уведомлениями.

### Ключевые возможности

- ✅ **Группировка ошибок** по fingerprint (SHA256 хэш)
- ✅ **Маскировка чувствительных данных** (email, телефоны, карты, токены)
- ✅ **Rate limiting** (In-Memory или Redis)
- ✅ **Уведомления с троттлингом** (Telegram, Email)
- ✅ **Grafana Loki webhook** поддержка
- ✅ **3 режима развёртывания** (Lite, Shared, Full)

### Архитектура

```
┌─────────────────┐
│   Ваше App      │
│   (ошибки)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Error Gateway  │
│  (микросервис)  │
└────────┬────────┘
         │
         ├─► БД (PostgreSQL/SQLite) — хранение
         ├─► Redis (опционально) — rate limiting
         ├─► Telegram — уведомления
         └─► Email — уведомления
```

---

## 📦 Установка

### Требования

| Компонент | Версия | Обязательно |
|-----------|--------|-------------|
| Docker | 20.10+ | ✅ Да |
| Docker Compose | 2.0+ | ✅ Да |
| PostgreSQL | 14+ | ❌ Нет (авто-SQLite) |
| Redis | 6+ | ❌ Нет (авто-In-Memory) |

---

### Docker (рекомендуется)

#### Шаг 1: Клонирование

```bash
git clone https://github.com/officialalexeev/error-gateway.git
cd error-gateway/latest
```

#### Шаг 2: Настройка

```bash
cp .env.example .env
```

#### Шаг 3: Выбор режима

**Lite (SQLite, без Redis):**
```bash
# .env — оставить пустым
POSTGRES_USER=
REDIS_HOST=
```

**Shared (PostgreSQL + Redis):**
```bash
# .env — заполнить
POSTGRES_USER=postgres
POSTGRES_PASSWORD=error_gateway_pass
POSTGRES_DB=error_gateway
REDIS_HOST=redis
```

**Full (изолированный):**
```bash
# Использовать docker-compose.full.yml
```

#### Шаг 4: Запуск

```bash
docker-compose up -d
```

#### Шаг 5: Проверка

```bash
curl http://localhost:8000/health
```

**Ожидаемый ответ:**
```json
{
  "status": "healthy"
}
```

---

### Локальная разработка

#### Требования

- Python 3.13+
- uv (менеджер пакетов)

#### Установка зависимостей

```bash
cd latest/src
uv install
```

#### Запуск сервера

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Тесты

```bash
uv run pytest
uv run pytest --cov=app --cov-report=term-missing
```

#### Линтеры

```bash
uv run ruff check app/
uv run black --check app/
uv run mypy --ignore-missing-imports app/
```

---

## ⚙️ Настройка

### Переменные окружения

#### База данных (авто-определение)

| Переменная | Описание | По умолчанию | Режим |
|------------|----------|--------------|-------|
| `POSTGRES_USER` | Пользователь PostgreSQL | (пусто) | Пусто = SQLite ✅ |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL | `error_gateway_pass` | Требуется для PostgreSQL |
| `POSTGRES_DB` | Имя БД | `error_gateway` | Требуется для PostgreSQL |
| `POSTGRES_HOST` | Хост PostgreSQL | `db` | Требуется для PostgreSQL |
| `POSTGRES_PORT` | Порт PostgreSQL | `5432` | Требуется для PostgreSQL |
| `DATABASE_STATEMENT_TIMEOUT` | Таймаут запросов (мс) | `30000` | Опционально |

**Пример SQLite (по умолчанию):**
```bash
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
POSTGRES_HOST=
POSTGRES_PORT=
```

**Пример PostgreSQL:**
```bash
POSTGRES_USER=error_gateway
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=error_gateway
POSTGRES_HOST=db.example.com
POSTGRES_PORT=5432
```

---

#### Redis (Rate Limiting)

| Переменная | Описание | По умолчанию | Режим |
|------------|----------|--------------|-------|
| `REDIS_HOST` | Хост Redis | (пусто) | Пусто = In-Memory ✅ |
| `REDIS_PORT` | Порт Redis | `6379` | Требуется для Redis |
| `REDIS_DB` | Номер БД Redis | `1` | 0-15 |
| `REDIS_PASSWORD` | Пароль Redis | (пусто) | Опционально |

**Пример In-Memory (по умолчанию):**
```bash
REDIS_HOST=
REDIS_PORT=6379
REDIS_DB=1
```

**Пример Redis:**
```bash
REDIS_HOST=redis.example.com
REDIS_PORT=6379
REDIS_DB=1
REDIS_PASSWORD=secure_password
```

---

#### Telegram уведомления

| Переменная | Описание | Обязательно |
|------------|----------|-------------|
| `TG_BOT_TOKEN` | Токен бота от @BotFather | ❌ Нет |
| `TG_CHAT_ID` | ID чата от @userinfobot | ❌ Нет |
| `TG_TOPIC_ID` | ID топика (для групп) | ❌ Нет |

**Как получить:**

1. **Бот:** Откройте [@BotFather](https://t.me/BotFather) → `/newbot` → получите токен
2. **Chat ID:** Откройте [@userinfobot](https://t.me/userinfobot) → `/start` → получите ID

**Пример:**
```bash
TG_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TG_CHAT_ID=-1001234567890
```

---

#### Email уведомления (SMTP)

| Переменная | Описание | Обязательно |
|------------|----------|-------------|
| `SMTP_HOST` | SMTP сервер | ❌ Нет |
| `SMTP_PORT` | SMTP порт | `587` |
| `SMTP_USER` | SMTP пользователь | ❌ Нет |
| `SMTP_PASSWORD` | SMTP пароль | ❌ Нет |
| `EMAIL_FROM` | Отправитель | ❌ Нет |
| `EMAIL_TO` | Получатели (через запятую) | ❌ Нет |

**Пример Gmail:**
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # App Password, не основной пароль!
EMAIL_FROM=error-gateway@gmail.com
EMAIL_TO=admin@example.com,devops@example.com
```

**Важно:** Для Gmail используйте [App Password](https://support.google.com/accounts/answer/185833)

---

#### Grafana Loki

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `LOKI_URL` | URL Grafana Loki | (пусто) |

**Пример:**
```bash
LOKI_URL=http://loki:3100
```

---

#### Логирование

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `LOG_LEVEL` | Уровень логов | `INFO` |
| `LOG_FORMAT` | Формат логов | `json` |

**Варианты:**
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- `LOG_FORMAT`: `json` (для production), `text` (для разработки)

---

#### Маскировка данных

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `MASK_EMAIL` | Маскировать email | `true` |
| `MASK_PHONE` | Маскировать телефоны | `true` |
| `MASK_CREDIT_CARD` | Маскировать карты | `true` |
| `MASK_TOKENS` | Маскировать токены | `true` |

---

#### Приложение

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `ERROR_RETENTION_DAYS` | Дней хранения ошибок | `30` |
| `RATE_LIMIT_PER_MINUTE` | Лимит запросов в минуту | `100` |
| `NOTIFICATION_THROTTLE_MINUTES` | Интервал уведомлений (мин) | `5` |
| `MAX_PAGINATION_LIMIT` | Макс. лимит пагинации | `100` |

---

#### CORS

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `CORS_ORIGINS` | Разрешённые origin | (пусто) |

**Пример:**
```bash
CORS_ORIGINS=https://admin.example.com,https://dashboard.example.com
```

---

### Режимы работы

| Режим | БД | Rate Limiting | RAM | Контейнеры | Для |
|-------|----|---------------|-----|------------|-----|
| **Lite** | SQLite | In-Memory | 50MB | 1 | Тестирование ✅ |
| **Shared** | PostgreSQL | Redis | 150MB | 1 | Production ✅ |
| **Full** | PostgreSQL | Redis | 300MB | 3 | Изоляция |

---

### Примеры .env

#### Lite (тестирование)

```bash
# Database (SQLite)
POSTGRES_USER=

# Rate Limiting (In-Memory)
REDIS_HOST=

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Telegram (опционально)
TG_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TG_CHAT_ID=-1001234567890
```

#### Shared (production)

```bash
# Database (PostgreSQL)
POSTGRES_USER=error_gateway
POSTGRES_PASSWORD=secure_password_123
POSTGRES_DB=error_gateway
POSTGRES_HOST=db.example.com
POSTGRES_PORT=5432

# Rate Limiting (Redis)
REDIS_HOST=redis.example.com
REDIS_PORT=6379
REDIS_DB=1
REDIS_PASSWORD=redis_password_456

# Telegram
TG_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TG_CHAT_ID=-1001234567890

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@gmail.com
SMTP_PASSWORD=app_password_xyz
EMAIL_FROM=error-gateway@gmail.com
EMAIL_TO=admin@example.com

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## 🔌 API

### Отправить ошибку

**Endpoint:** `POST /api/v1/error`

**Параметры:**

| Поле | Тип | Обязательно | По умолчанию | Описание |
|------|-----|-------------|--------------|----------|
| `message` | string | ✅ Да | - | Сообщение (1-1000 символов) |
| `exception_type` | string | ❌ Нет | `"Error"` | Тип исключения |
| `stack_trace` | string | ❌ Нет | `null` | Stack trace (макс. 10000) |
| `environment` | string | ❌ Нет | `"unknown"` | Окружение |
| `release_version` | string | ❌ Нет | `null` | Версия приложения |
| `context` | object | ❌ Нет | `{}` | Контекст (макс. 100 элементов, 10KB) |

**Пример запроса:**
```bash
curl -X POST http://localhost:8000/api/v1/error \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Database connection failed",
    "exception_type": "ConnectionError",
    "stack_trace": "File \"app/db.py\", line 42, in connect\nraise ConnectionError()",
    "environment": "production",
    "release_version": "1.2.3",
    "context": {
      "user_id": 123,
      "email": "test@example.com",
      "request_id": "req-abc-123"
    }
  }'
```

**Ответ:**
```json
{
  "status": "accepted",
  "message": "Error received and processed"
}
```

**Коды ответов:**
- `200` — Успешно
- `400` — Ошибка валидации
- `429` — Rate limit превышен

---

### Получить ошибки

**Endpoint:** `GET /api/v1/groups`

**Параметры query:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `limit` | integer | `50` | Количество (макс. 100) |
| `offset` | integer | `0` | Смещение |

**Пример:**
```bash
curl "http://localhost:8000/api/v1/groups?limit=20&offset=0"
```

**Ответ:**
```json
{
  "groups": [
    {
      "id": "uuid-string",
      "exception_type": "ConnectionError",
      "message": "Database connection failed",
      "count": 10,
      "first_seen": "2024-01-01T12:00:00Z",
      "last_seen": "2024-01-01T12:05:00Z",
      "is_notified": true
    }
  ],
  "total": 1
}
```

---

### Получить детали группы

**Endpoint:** `GET /api/v1/groups/{group_id}`

**Пример:**
```bash
curl http://localhost:8000/api/v1/groups/550e8400-e29b-41d4-a716-446655440000
```

**Ответ:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "exception_type": "ConnectionError",
  "message": "Database connection failed",
  "count": 10,
  "first_seen": "2024-01-01T12:00:00Z",
  "last_seen": "2024-01-01T12:05:00Z",
  "is_notified": true,
  "events": [
    {
      "id": "event-uuid",
      "message": "Database connection failed",
      "stack_trace": "File \"app/db.py\"...",
      "context": {...},
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ]
}
```

---

### Health check

**Endpoint:** `GET /health`

**Пример:**
```bash
curl http://localhost:8000/health
```

**Ответ:**
```json
{
  "status": "healthy"
}
```

---

### Metrics

**Endpoint:** `GET /metrics`

**Пример:**
```bash
curl http://localhost:8000/metrics
```

**Ответ (Prometheus format):**
```
# HELP error_gateway_errors_total Total number of errors
# TYPE error_gateway_errors_total counter
error_gateway_errors_total{exception_type="ConnectionError",environment="production"} 10
```

---

### Loki webhook

**Endpoint:** `POST /api/v1/loki/webhook`

**Пример:**
```bash
curl -X POST http://localhost:8000/api/v1/loki/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [
      {
        "labels": {
          "exception_type": "ConnectionError",
          "severity": "critical"
        },
        "annotations": {
          "message": "Database connection failed"
        }
      }
    ]
  }'
```

---

## 🔔 Уведомления

### Telegram

#### Настройка

1. **Создайте бота:**
   - Откройте [@BotFather](https://t.me/BotFather)
   - Отправьте `/newbot`
   - Введите имя и username бота
   - Сохраните токен

2. **Узнайте Chat ID:**
   - Откройте [@userinfobot](https://t.me/userinfobot)
   - Отправьте `/start`
   - Сохраните Chat ID

3. **Добавьте бота в чат** (опционально):
   - Добавьте бота в группу/канал
   - Дайте права на отправку сообщений

4. **Настройте .env:**
```bash
TG_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TG_CHAT_ID=-1001234567890
```

#### Формат уведомления

```
🚨 Ошибка: ConnectionError

Database connection failed

📊 Количество: 10
⏰ Первое появление: 2024-01-01 12:00:00 UTC
⏰ Последнее: 2024-01-01 12:05:00 UTC

📝 Stack trace:
File "app/db.py", line 42
  raise ConnectionError()

🔖 Контекст:
• user_id: 123
• environment: production
```

---

### Email

#### Настройка

**Gmail:**
1. Включите 2FA в аккаунте Google
2. Создайте [App Password](https://support.google.com/accounts/answer/185833)
3. Используйте App Password вместо основного пароля

**Пример .env:**
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop  # 16-символьный App Password
EMAIL_FROM=error-gateway@gmail.com
EMAIL_TO=admin@example.com,devops@example.com
```

#### Формат уведомления

**Тема:** `🚨 Error Gateway: ConnectionError — Database connection failed`

**Тело письма:**
```
Ошибка: ConnectionError

Database connection failed

Количество: 10
Первое появление: 2024-01-01 12:00:00 UTC
Последнее: 2024-01-01 12:05:00 UTC

Stack trace:
File "app/db.py", line 42
  raise ConnectionError()

Контекст:
• user_id: 123
• environment: production
• release_version: 1.2.3
```

---

### Настройка троттлинга

**Параметр:** `NOTIFICATION_THROTTLE_MINUTES` (по умолчанию 5 минут)

**Как работает:**
1. При первой ошибке отправляется уведомление
2. Следующие уведомления для той же ошибки блокируются на `NOTIFICATION_THROTTLE_MINUTES`
3. После истечения времени — уведомление отправляется снова

**Пример:**
```bash
# Уведомлять не чаще раза в 15 минут
NOTIFICATION_THROTTLE_MINUTES=15
```

---

## 🔗 Интеграции

### Grafana Loki

Error Gateway поддерживает **двустороннюю интеграцию** с Grafana Loki:

1. **Grafana → Error Gateway:** Webhook для алертов
2. **Error Gateway → Loki:** Отправка логов

#### Настройка Loki

**docker-compose.yml:**
```yaml
services:
  error-gateway:
    image: officialalexeev/error-gateway:latest
    environment:
      - LOKI_URL=http://loki:3100
    depends_on:
      - loki

  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
```

**.env:**
```bash
LOKI_URL=http://loki:3100
```

#### Настройка Grafana

1. Откройте Grafana → Alerting → Notification policies
2. Добавьте webhook:
   ```
   URL: http://error-gateway:8000/api/v1/loki/webhook
   HTTP Method: POST
   ```

#### Запрос в Grafana

```logql
{app="error-gateway", exception="ConnectionError"}
```

**Полная документация:** [integration/loki.md](integration/loki.md)

---

### Примеры кода

#### Python

```python
import httpx

async def send_error(message: str, **kwargs):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/error",
            json={
                "message": message,
                **kwargs
            }
        )
        return response.json()

# Использование
await send_error(
    message="Database connection failed",
    exception_type="ConnectionError",
    environment="production"
)
```

#### JavaScript/Node.js

```javascript
const axios = require('axios');

async function sendError(message, options = {}) {
  const response = await axios.post(
    'http://localhost:8000/api/v1/error',
    { message, ...options }
  );
  return response.data;
}

// Использование
await sendError('Database connection failed', {
  exception_type: 'ConnectionError',
  environment: 'production'
});
```

**Полные примеры:** [integration/examples.md](integration/examples.md)

---

## 🚀 Production

### Развёртывание

#### Подготовка БД

```bash
# Подключитесь к PostgreSQL
docker exec -it main-db psql -U postgres

# Создайте БД и пользователя
CREATE DATABASE error_gateway;
CREATE USER error_gateway WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE error_gateway TO error_gateway;
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  error-gateway:
    image: officialalexeev/error-gateway:latest
    container_name: error-gateway
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_USER=error_gateway
      - POSTGRES_PASSWORD=secure_password
      - POSTGRES_DB=error_gateway
      - POSTGRES_HOST=db
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_DB=1
      - TG_BOT_TOKEN=${TG_BOT_TOKEN}
      - TG_CHAT_ID=${TG_CHAT_ID}
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=error_gateway
      - POSTGRES_PASSWORD=secure_password
      - POSTGRES_DB=error_gateway
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U error_gateway"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

#### Запуск

```bash
docker-compose up -d
```

---

### Масштабирование

#### Репликация

Error Gateway поддерживает работу в режиме stateless — можно запускать несколько инстансов:

```yaml
services:
  error-gateway:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
```

**Важно:**
- Используйте Redis для rate limiting
- PostgreSQL для хранения данных
- Балансировщик нагрузки перед инстансами

#### Resource limits

```yaml
services:
  error-gateway:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
        reservations:
          cpus: '0.25'
          memory: 128M
```

---

### Мониторинг

#### Prometheus метрики

Error Gateway экспортирует метрики в формате Prometheus:

- `error_gateway_errors_total` — общее количество ошибок
- `error_gateway_groups_total` — количество групп ошибок
- `error_gateway_notifications_total` — количество уведомлений

#### Health check

```bash
curl http://localhost:8000/health
```

#### Логи

**JSON формат (production):**
```json
{"level": "INFO", "message": "Error processed", "timestamp": "2024-01-01T12:00:00Z"}
```

**Text формат (development):**
```
2024-01-01 12:00:00 | INFO | app.main:process_error:42 - Error processed
```

---

## 🛠️ Troubleshooting

### Частые проблемы

#### Ошибка: "Cannot connect to database"

**Причина:** PostgreSQL не запущен или неверные учётные данные

**Решение:**
```bash
# Проверьте статус БД
docker-compose ps db

# Проверьте логи
docker-compose logs db

# Пересоздайте БД
docker-compose down
docker-compose up -d db
```

---

#### Ошибка: "Rate limit exceeded"

**Причина:** Превышен лимит запросов в минуту

**Решение:**
```bash
# Увеличьте лимит
RATE_LIMIT_PER_MINUTE=200

# Или используйте Redis
REDIS_HOST=redis
```

---

#### Уведомления не отправляются

**Причина:** Неверные учётные данные Telegram/Email

**Решение:**
1. Проверьте токен бота: `curl https://api.telegram.org/bot<TOKEN>/getMe`
2. Проверьте Chat ID через @userinfobot
3. Для Gmail используйте App Password

---

#### Ошибка: "Table doesn't exist"

**Причина:** БД не инициализирована

**Решение:**
```bash
# Перезапустите сервис (таблицы создаются автоматически)
docker-compose restart error-gateway

# Проверьте логи
docker-compose logs error-gateway
```

---

### FAQ

**Q: Можно ли использовать SQLite в production?**

A: Да, для небольших нагрузок. Для высоких нагрузок рекомендуется PostgreSQL.

**Q: Как изменить интервал между уведомлениями?**

A: Измените `NOTIFICATION_THROTTLE_MINUTES` в .env (по умолчанию 5 минут).

**Q: Можно ли отключить маскировку данных?**

A: Да, установите соответствующие переменные в `false`:
```bash
MASK_EMAIL=false
MASK_TOKENS=false
```

**Q: Как экспортировать ошибки?**

A: Используйте API `/api/v1/groups` для получения всех ошибок в JSON формате.

**Q: Сколько ошибок хранится в БД?**

A: По умолчанию 30 дней. Измените `ERROR_RETENTION_DAYS` для настройки.

---

## 📊 Режимы работы

### Lite (SQLite)

**Плюсы:**
- ✅ Простота развёртывания
- ✅ Минимальное потребление RAM (50MB)
- ✅ Не требует внешних зависимостей

**Минусы:**
- ❌ Не подходит для высоких нагрузок
- ❌ Нет distributed rate limiting

**Для:** Тестирования, пет-проектов, маленьких команд

---

### Shared (PostgreSQL + Redis)

**Плюсы:**
- ✅ Production готовность
- ✅ Distributed rate limiting
- ✅ Интеграция с существующей инфраструктурой

**Минусы:**
- ❌ Требует PostgreSQL и Redis

**Для:** Production с существующей инфраструктурой

---

### Full (изолированный)

**Плюсы:**
- ✅ Полная изоляция
- ✅ Собственные БД и Redis
- ✅ Максимальная надёжность

**Минусы:**
- ❌ Больше ресурсов (300MB RAM)
- ❌ Больше контейнеров

**Для:** Отдельных развёртываний, максимальной изоляции

---

[← На главную](../README.md) | [🇬🇧 English version](README_en.md)
