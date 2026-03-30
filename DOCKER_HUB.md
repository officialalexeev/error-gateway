# Error Gateway - Docker Hub

[![Docker Pulls](https://img.shields.io/docker/pulls/officialalexeev/error-gateway.svg)](https://hub.docker.com/r/officialalexeev/error-gateway)
[![Docker Image](https://img.shields.io/docker/image-size/officialalexeev/error-gateway/latest)](https://hub.docker.com/r/officialalexeev/error-gateway)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/officialalexeev/error-gateway)

**Autonomous microservice for error tracking with Telegram/Email notifications**

---

## 🚀 Quick Start

### Pull Image

```bash
docker pull officialalexeev/error-gateway:latest
```

### Run with Docker Compose

```yaml
# docker-compose.yml
services:
  error-gateway:
    image: officialalexeev/error-gateway:latest
    container_name: error-gateway
    ports:
      - "8000:8000"
    environment:
      # Database (auto-detection)
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=your_password
      - POSTGRES_DB=error_gateway
      - POSTGRES_HOST=db
      
      # Redis
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      
      # Telegram
      - TG_BOT_TOKEN=your_bot_token
      - TG_CHAT_ID=your_chat_id
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
  
  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=error_gateway
      - POSTGRES_PASSWORD=error_gateway_pass
      - POSTGRES_DB=error_gateway
    volumes:
      - postgres_data:/var/lib/postgresql/data
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

```bash
docker-compose up -d
```

### Run with Docker

```bash
docker run -d \
  --name error-gateway \
  -p 8000:8000 \
  -e POSTGRES_USER=error_gateway \
  -e POSTGRES_PASSWORD=error_gateway_pass \
  -e POSTGRES_DB=error_gateway \
  -e POSTGRES_HOST=your-db-host \
  -e REDIS_HOST=your-redis-host \
  -e TG_BOT_TOKEN=your_token \
  -e TG_CHAT_ID=your_chat_id \
  officialalexeev/error-gateway:latest
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `POSTGRES_USER` | PostgreSQL username (empty = SQLite) | `""` | ❌ |
| `POSTGRES_PASSWORD` | PostgreSQL password | `error_gateway_pass` | ❌ |
| `POSTGRES_DB` | PostgreSQL database | `error_gateway` | ❌ |
| `POSTGRES_HOST` | PostgreSQL host | `db` | ❌ |
| `POSTGRES_PORT` | PostgreSQL port | `5432` | ❌ |
| `REDIS_HOST` | Redis host (empty = in-memory) | `""` | ❌ |
| `REDIS_PORT` | Redis port | `6379` | ❌ |
| `REDIS_DB` | Redis database | `1` | ❌ |
| `TG_BOT_TOKEN` | Telegram bot token | - | ❌ |
| `TG_CHAT_ID` | Telegram chat ID | - | ❌ |
| `SMTP_HOST` | SMTP server | - | ❌ |
| `SMTP_USER` | SMTP username | - | ❌ |
| `SMTP_PASSWORD` | SMTP password | - | ❌ |
| `EMAIL_FROM` | Sender email | - | ❌ |
| `EMAIL_TO` | Recipient email (comma-separated) | - | ❌ |
| `LOKI_URL` | Grafana Loki URL | - | ❌ |
| `LOG_LEVEL` | Log level | `INFO` | ❌ |
| `LOG_FORMAT` | Log format (`json` or `text`) | `json` | ❌ |
| `MASK_EMAIL` | Mask emails | `true` | ❌ |
| `MASK_PHONE` | Mask phone numbers | `true` | ❌ |
| `MASK_CREDIT_CARD` | Mask credit cards | `true` | ❌ |
| `MASK_TOKENS` | Mask tokens/passwords | `true` | ❌ |
| `RATE_LIMIT_PER_MINUTE` | Rate limit (requests per minute) | `100` | ❌ |
| `MAX_PAGINATION_LIMIT` | Max pagination limit | `100` | ❌ |

**Context Limits (DoS protection):**
- Max context size: 10KB
- Max context items: 100
- Max context depth: 5 levels

### SQLite Mode (Lite)

For testing without PostgreSQL:

```bash
docker run -d \
  --name error-gateway \
  -p 8000:8000 \
  -e POSTGRES_USER= \
  -v error_gateway_data:/app/data \
  officialalexeev/error-gateway:latest
```

---

## 🔌 API

### Send Error

**Endpoint:** `POST /api/v1/error`

**Request Body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `message` | string | ✅ Yes | - | Error message (1-1000 chars) |
| `exception_type` | string | ❌ No | `"Error"` | Exception type (e.g., `ConnectionError`) |
| `stack_trace` | string | ❌ No | `null` | Stack trace (max 10000 chars) |
| `environment` | string | ❌ No | `"unknown"` | Environment name (e.g., `production`, `staging`) |
| `release_version` | string | ❌ No | `null` | Application version (e.g., `1.2.3`) |
| `context` | object | ❌ No | `{}` | Additional context data (max 100 items, 10KB) |

**Example:**

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

### Get Errors

```bash
curl http://localhost:8000/api/v1/groups
```

**Response:**

```json
{
  "groups": [
    {
      "exception_type": "ConnectionError",
      "message": "Database connection failed",
      "count": 10,
      "first_seen": "2024-01-01T12:00:00Z",
      "last_seen": "2024-01-01T12:05:00Z"
    }
  ],
  "total": 1
}
```

### Health Check

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

## 📊 Architecture

```
┌─────────────────┐
│   Your App      │
│   (Send Errors) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Error Gateway  │
│  (Docker)       │
└────────┬────────┘
         │
         ├─► PostgreSQL (store)
         ├─► Redis (rate limit)
         ├─► Telegram (notify)
         └─► Email (notify)
```

---

## 🏷️ Image Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release |
| `1.0.0` | Current stable version |

---

## 📦 Build Your Own Image

```bash
# Clone repository
git clone https://github.com/officialalexeev/error-gateway.git
cd error-gateway/src

# Build image
docker build -t error-gateway:latest .

# Run
docker run -p 8000:8000 --env-file .env error-gateway:latest
```

---

## 🔒 Security

### Data Masking

Automatically masks:
- Email: `test@example.com` → `t***@example.com`
- Phones: `+79991234567` → `+7***1234567`
- Cards: `4111111111111111` → `****-****-****-1111`
- Tokens: `secret_token` → `***REDACTED***`

### Rate Limiting

- Default: 100 requests per minute per IP
- Redis-backed (PostgreSQL mode)
- In-Memory (SQLite mode)

---

## 📈 Grafana Loki Integration

Error Gateway supports bidirectional integration with Grafana Loki:

1. **Grafana → Error Gateway** — webhook for receiving alerts (`/api/v1/loki/webhook`)
2. **Error Gateway → Loki** — sending error logs to Loki

### Configure Loki

```bash
docker run -d \
  --name error-gateway \
  -p 8000:8000 \
  -e LOKI_URL=http://loki:3100 \
  officialalexeev/error-gateway:latest
```

### Query in Grafana

```logql
{app="error-gateway", exception="ConnectionError"}
```

**Full documentation:** [LOKI_INTEGRATION.md](https://github.com/officialalexeev/error-gateway/blob/main/docs/LOKI_INTEGRATION.md)

---

## 🧪 Testing

```bash
# Run tests
docker run --rm \
  -v $(pwd):/app \
  officialalexeev/error-gateway:latest \
  pytest
```

---

## 📝 License

MIT License - See [LICENSE](https://github.com/officialalexeev/error-gateway/blob/main/LICENSE)

---

## 👤 Author

**Alexeev Alexandr**

- GitHub: [@officialalexeev](https://github.com/officialalexeev)
- Docker Hub: [officialalexeev/error-gateway](https://hub.docker.com/r/officialalexeev/error-gateway)

---

## 🤝 Support

- **Issues:** [GitHub Issues](https://github.com/officialalexeev/error-gateway/issues)
- **Documentation:** [GitHub README](https://github.com/officialalexeev/error-gateway#readme)
- **Docker Hub:** [officialalexeev/error-gateway](https://hub.docker.com/r/officialalexeev/error-gateway)
