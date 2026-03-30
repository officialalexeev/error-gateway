# Error Gateway — Full Documentation

**Autonomous microservice for error tracking with Telegram/Email notifications**

[← Back to Main](../README.md) | [🇷🇺 Русская версия](README_ru.md)

---

## 📋 Table of Contents

1. [About](#about)
2. [Installation](#installation)
   - [Requirements](#requirements)
   - [Docker (Recommended)](#docker-recommended)
   - [Local Development](#local-development)
3. [Configuration](#configuration)
   - [Environment Variables](#environment-variables)
   - [Deployment Modes](#deployment-modes)
   - [.env Examples](#env-examples)
4. [API](#api)
   - [Send Error](#send-error)
   - [Get Errors](#get-errors)
   - [Health Check](#health-check)
   - [Metrics](#metrics)
5. [Notifications](#notifications)
   - [Telegram](#telegram)
   - [Email](#email)
   - [Throttling Setup](#throttling-setup)
6. [Integrations](#integrations)
   - [Grafana Loki](#grafana-loki)
   - [Code Examples](#code-examples)
7. [Production](#production)
   - [Deployment](#deployment)
   - [Scaling](#scaling)
   - [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)
   - [Common Issues](#common-issues)
   - [FAQ](#faq)

---

## 🎯 About

**Error Gateway** is an autonomous microservice for centralized error collection and processing with automatic notifications.

### Key Features

- ✅ **Error grouping** by fingerprint (SHA256 hash)
- ✅ **Sensitive data masking** (emails, phones, cards, tokens)
- ✅ **Rate limiting** (In-Memory or Redis)
- ✅ **Throttled notifications** (Telegram, Email)
- ✅ **Grafana Loki webhook** support
- ✅ **3 deployment modes** (Lite, Shared, Full)

### Architecture

```
┌─────────────────┐
│   Your App      │
│   (errors)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Error Gateway  │
│  (microservice) │
└────────┬────────┘
         │
         ├─► DB (PostgreSQL/SQLite) — storage
         ├─► Redis (optional) — rate limiting
         ├─► Telegram — notifications
         └─► Email — notifications
```

---

## 📦 Installation

### Requirements

| Component | Version | Required |
|-----------|---------|----------|
| Docker | 20.10+ | ✅ Yes |
| Docker Compose | 2.0+ | ✅ Yes |
| PostgreSQL | 14+ | ❌ No (auto-SQLite) |
| Redis | 6+ | ❌ No (auto-In-Memory) |

---

### Docker (Recommended)

#### Step 1: Clone

```bash
git clone https://github.com/officialalexeev/error-gateway.git
cd error-gateway/latest
```

#### Step 2: Configure

```bash
cp .env.example .env
```

#### Step 3: Choose Mode

**Lite (SQLite, no Redis):**
```bash
# .env — leave empty
POSTGRES_USER=
REDIS_HOST=
```

**Shared (PostgreSQL + Redis):**
```bash
# .env — fill in
POSTGRES_USER=postgres
POSTGRES_PASSWORD=error_gateway_pass
POSTGRES_DB=error_gateway
REDIS_HOST=redis
```

**Full (isolated):**
```bash
# Use docker-compose.full.yml
```

#### Step 4: Start

```bash
docker-compose up -d
```

#### Step 5: Verify

```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy"
}
```

---

### Local Development

#### Requirements

- Python 3.13+
- uv (package manager)

#### Install Dependencies

```bash
cd latest/src
uv install
```

#### Start Server

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Tests

```bash
uv run pytest
uv run pytest --cov=app --cov-report=term-missing
```

#### Linters

```bash
uv run ruff check app/
uv run black --check app/
uv run mypy --ignore-missing-imports app/
```

---

## ⚙️ Configuration

### Environment Variables

#### Database (Auto-Detection)

| Variable | Description | Default | Mode |
|----------|-------------|---------|------|
| `POSTGRES_USER` | PostgreSQL username | (empty) | Empty = SQLite ✅ |
| `POSTGRES_PASSWORD` | PostgreSQL password | `error_gateway_pass` | Required for PostgreSQL |
| `POSTGRES_DB` | Database name | `error_gateway` | Required for PostgreSQL |
| `POSTGRES_HOST` | PostgreSQL host | `db` | Required for PostgreSQL |
| `POSTGRES_PORT` | PostgreSQL port | `5432` | Required for PostgreSQL |
| `DATABASE_STATEMENT_TIMEOUT` | Query timeout (ms) | `30000` | Optional |

**SQLite Example (Default):**
```bash
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
POSTGRES_HOST=
POSTGRES_PORT=
```

**PostgreSQL Example:**
```bash
POSTGRES_USER=error_gateway
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=error_gateway
POSTGRES_HOST=db.example.com
POSTGRES_PORT=5432
```

---

#### Redis (Rate Limiting)

| Variable | Description | Default | Mode |
|----------|-------------|---------|------|
| `REDIS_HOST` | Redis host | (empty) | Empty = In-Memory ✅ |
| `REDIS_PORT` | Redis port | `6379` | Required for Redis |
| `REDIS_DB` | Redis database number | `1` | 0-15 |
| `REDIS_PASSWORD` | Redis password | (empty) | Optional |

**In-Memory Example (Default):**
```bash
REDIS_HOST=
REDIS_PORT=6379
REDIS_DB=1
```

**Redis Example:**
```bash
REDIS_HOST=redis.example.com
REDIS_PORT=6379
REDIS_DB=1
REDIS_PASSWORD=secure_password
```

---

#### Telegram Notifications

| Variable | Description | Required |
|----------|-------------|----------|
| `TG_BOT_TOKEN` | Bot token from @BotFather | ❌ No |
| `TG_CHAT_ID` | Chat ID from @userinfobot | ❌ No |
| `TG_TOPIC_ID` | Topic ID (for groups) | ❌ No |

**How to Get:**

1. **Bot:** Open [@BotFather](https://t.me/BotFather) → `/newbot` → get token
2. **Chat ID:** Open [@userinfobot](https://t.me/userinfobot) → `/start` → get ID

**Example:**
```bash
TG_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TG_CHAT_ID=-1001234567890
```

---

#### Email Notifications (SMTP)

| Variable | Description | Required |
|----------|-------------|----------|
| `SMTP_HOST` | SMTP server | ❌ No |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USER` | SMTP username | ❌ No |
| `SMTP_PASSWORD` | SMTP password | ❌ No |
| `EMAIL_FROM` | Sender email | ❌ No |
| `EMAIL_TO` | Recipients (comma-separated) | ❌ No |

**Gmail Example:**
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=error-gateway@gmail.com
EMAIL_TO=admin@example.com,devops@example.com
```

**Important:** For Gmail, use [App Password](https://support.google.com/accounts/answer/185833)

---

#### Grafana Loki

| Variable | Description | Default |
|----------|-------------|---------|
| `LOKI_URL` | Grafana Loki URL | (empty) |

**Example:**
```bash
LOKI_URL=http://loki:3100
```

---

#### Logging

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Log level | `INFO` |
| `LOG_FORMAT` | Log format | `json` |

**Options:**
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- `LOG_FORMAT`: `json` (production), `text` (development)

---

#### Data Masking

| Variable | Description | Default |
|----------|-------------|---------|
| `MASK_EMAIL` | Mask emails | `true` |
| `MASK_PHONE` | Mask phone numbers | `true` |
| `MASK_CREDIT_CARD` | Mask credit cards | `true` |
| `MASK_TOKENS` | Mask tokens/passwords | `true` |

---

#### Application

| Variable | Description | Default |
|----------|-------------|---------|
| `ERROR_RETENTION_DAYS` | Days to store errors | `30` |
| `RATE_LIMIT_PER_MINUTE` | Requests per minute limit | `100` |
| `NOTIFICATION_THROTTLE_MINUTES` | Notification interval (min) | `5` |
| `MAX_PAGINATION_LIMIT` | Max pagination limit | `100` |

---

#### CORS

| Variable | Description | Default |
|----------|-------------|---------|
| `CORS_ORIGINS` | Allowed origins | (empty) |

**Example:**
```bash
CORS_ORIGINS=https://admin.example.com,https://dashboard.example.com
```

---

### Deployment Modes

| Mode | Database | Rate Limiting | RAM | Containers | For |
|------|----------|---------------|-----|------------|-----|
| **Lite** | SQLite | In-Memory | 50MB | 1 | Testing ✅ |
| **Shared** | PostgreSQL | Redis | 150MB | 1 | Production ✅ |
| **Full** | PostgreSQL | Redis | 300MB | 3 | Isolation |

---

### .env Examples

#### Lite (Testing)

```bash
# Database (SQLite)
POSTGRES_USER=

# Rate Limiting (In-Memory)
REDIS_HOST=

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Telegram (optional)
TG_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TG_CHAT_ID=-1001234567890
```

#### Shared (Production)

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

### Send Error

**Endpoint:** `POST /api/v1/error`

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `message` | string | ✅ Yes | - | Error message (1-1000 chars) |
| `exception_type` | string | ❌ No | `"Error"` | Exception type |
| `stack_trace` | string | ❌ No | `null` | Stack trace (max 10000) |
| `environment` | string | ❌ No | `"unknown"` | Environment |
| `release_version` | string | ❌ No | `null` | Application version |
| `context` | object | ❌ No | `{}` | Context (max 100 items, 10KB) |

**Request Example:**
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

**Response:**
```json
{
  "status": "accepted",
  "message": "Error received and processed"
}
```

**Response Codes:**
- `200` — Success
- `400` — Validation error
- `429` — Rate limit exceeded

---

### Get Errors

**Endpoint:** `GET /api/v1/groups`

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | `50` | Count (max 100) |
| `offset` | integer | `0` | Offset |

**Example:**
```bash
curl "http://localhost:8000/api/v1/groups?limit=20&offset=0"
```

**Response:**
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

### Get Group Details

**Endpoint:** `GET /api/v1/groups/{group_id}`

**Example:**
```bash
curl http://localhost:8000/api/v1/groups/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
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

### Health Check

**Endpoint:** `GET /health`

**Example:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy"
}
```

---

### Metrics

**Endpoint:** `GET /metrics`

**Example:**
```bash
curl http://localhost:8000/metrics
```

**Response (Prometheus format):**
```
# HELP error_gateway_errors_total Total number of errors
# TYPE error_gateway_errors_total counter
error_gateway_errors_total{exception_type="ConnectionError",environment="production"} 10
```

---

### Loki Webhook

**Endpoint:** `POST /api/v1/loki/webhook`

**Example:**
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

## 🔔 Notifications

### Telegram

#### Setup

1. **Create a bot:**
   - Open [@BotFather](https://t.me/BotFather)
   - Send `/newbot`
   - Enter bot name and username
   - Save the token

2. **Get Chat ID:**
   - Open [@userinfobot](https://t.me/userinfobot)
   - Send `/start`
   - Save the Chat ID

3. **Add bot to chat** (optional):
   - Add bot to group/channel
   - Grant send message permissions

4. **Configure .env:**
```bash
TG_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TG_CHAT_ID=-1001234567890
```

#### Notification Format

```
🚨 Error: ConnectionError

Database connection failed

📊 Count: 10
⏰ First seen: 2024-01-01 12:00:00 UTC
⏰ Last seen: 2024-01-01 12:05:00 UTC

📝 Stack trace:
File "app/db.py", line 42
  raise ConnectionError()

🔖 Context:
• user_id: 123
• environment: production
```

---

### Email

#### Setup

**Gmail:**
1. Enable 2FA in Google Account
2. Create [App Password](https://support.google.com/accounts/answer/185833)
3. Use App Password instead of main password

**.env Example:**
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop  # 16-character App Password
EMAIL_FROM=error-gateway@gmail.com
EMAIL_TO=admin@example.com,devops@example.com
```

#### Notification Format

**Subject:** `🚨 Error Gateway: ConnectionError — Database connection failed`

**Body:**
```
Error: ConnectionError

Database connection failed

Count: 10
First seen: 2024-01-01 12:00:00 UTC
Last seen: 2024-01-01 12:05:00 UTC

Stack trace:
File "app/db.py", line 42
  raise ConnectionError()

Context:
• user_id: 123
• environment: production
• release_version: 1.2.3
```

---

### Throttling Setup

**Parameter:** `NOTIFICATION_THROTTLE_MINUTES` (default 5 minutes)

**How it works:**
1. First error triggers notification
2. Subsequent notifications for same error blocked for `NOTIFICATION_THROTTLE_MINUTES`
3. After timeout — notification sent again

**Example:**
```bash
# Notify no more than once per 15 minutes
NOTIFICATION_THROTTLE_MINUTES=15
```

---

## 🔗 Integrations

### Grafana Loki

Error Gateway supports **bidirectional integration** with Grafana Loki:

1. **Grafana → Error Gateway:** Webhook for alerts
2. **Error Gateway → Loki:** Error log shipping

#### Loki Setup

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

#### Grafana Setup

1. Open Grafana → Alerting → Notification policies
2. Add webhook:
   ```
   URL: http://error-gateway:8000/api/v1/loki/webhook
   HTTP Method: POST
   ```

#### Query in Grafana

```logql
{app="error-gateway", exception="ConnectionError"}
```

**Full documentation:** [integration/loki.md](integration/loki.md)

---

### Code Examples

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

# Usage
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

// Usage
await sendError('Database connection failed', {
  exception_type: 'ConnectionError',
  environment: 'production'
});
```

**Full examples:** [integration/examples.md](integration/examples.md)

---

## 🚀 Production

### Deployment

#### Prepare Database

```bash
# Connect to PostgreSQL
docker exec -it main-db psql -U postgres

# Create database and user
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

#### Start

```bash
docker-compose up -d
```

---

### Scaling

#### Replication

Error Gateway supports stateless mode — multiple instances can run:

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

**Important:**
- Use Redis for rate limiting
- PostgreSQL for data storage
- Load balancer in front of instances

#### Resource Limits

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

### Monitoring

#### Prometheus Metrics

Error Gateway exports metrics in Prometheus format:

- `error_gateway_errors_total` — total errors
- `error_gateway_groups_total` — error groups count
- `error_gateway_notifications_total` — notifications sent

#### Health Check

```bash
curl http://localhost:8000/health
```

#### Logs

**JSON format (production):**
```json
{"level": "INFO", "message": "Error processed", "timestamp": "2024-01-01T12:00:00Z"}
```

**Text format (development):**
```
2024-01-01 12:00:00 | INFO | app.main:process_error:42 - Error processed
```

---

## 🛠️ Troubleshooting

### Common Issues

#### Error: "Cannot connect to database"

**Cause:** PostgreSQL not running or wrong credentials

**Solution:**
```bash
# Check DB status
docker-compose ps db

# Check logs
docker-compose logs db

# Recreate DB
docker-compose down
docker-compose up -d db
```

---

#### Error: "Rate limit exceeded"

**Cause:** Requests per minute limit exceeded

**Solution:**
```bash
# Increase limit
RATE_LIMIT_PER_MINUTE=200

# Or use Redis
REDIS_HOST=redis
```

---

#### Notifications not sending

**Cause:** Wrong Telegram/Email credentials

**Solution:**
1. Check bot token: `curl https://api.telegram.org/bot<TOKEN>/getMe`
2. Check Chat ID via @userinfobot
3. For Gmail, use App Password

---

#### Error: "Table doesn't exist"

**Cause:** Database not initialized

**Solution:**
```bash
# Restart service (tables created automatically)
docker-compose restart error-gateway

# Check logs
docker-compose logs error-gateway
```

---

### FAQ

**Q: Can I use SQLite in production?**

A: Yes, for low workloads. PostgreSQL recommended for high workloads.

**Q: How to change notification interval?**

A: Change `NOTIFICATION_THROTTLE_MINUTES` in .env (default 5 minutes).

**Q: Can I disable data masking?**

A: Yes, set corresponding variables to `false`:
```bash
MASK_EMAIL=false
MASK_TOKENS=false
```

**Q: How to export errors?**

A: Use `/api/v1/groups` API to get all errors in JSON format.

**Q: How long are errors stored in DB?**

A: Default 30 days. Change `ERROR_RETENTION_DAYS` to configure.

---

## 📊 Deployment Modes

### Lite (SQLite)

**Pros:**
- ✅ Simple deployment
- ✅ Minimal RAM usage (50MB)
- ✅ No external dependencies

**Cons:**
- ❌ Not suitable for high workloads
- ❌ No distributed rate limiting

**For:** Testing, pet projects, small teams

---

### Shared (PostgreSQL + Redis)

**Pros:**
- ✅ Production ready
- ✅ Distributed rate limiting
- ✅ Integration with existing infrastructure

**Cons:**
- ❌ Requires PostgreSQL and Redis

**For:** Production with existing infrastructure

---

### Full (Isolated)

**Pros:**
- ✅ Full isolation
- ✅ Dedicated DB and Redis
- ✅ Maximum reliability

**Cons:**
- ❌ More resources (300MB RAM)
- ❌ More containers

**For:** Separate deployments, maximum isolation

---

[← Back to Main](../README.md) | [🇷🇺 Русская версия](README_ru.md)
