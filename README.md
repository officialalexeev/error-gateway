# Error Gateway

**Autonomous microservice for error tracking with notifications via Telegram/Email**

[🇷🇺 Полная русская документация](docs/README_ru.md) | [🇬🇧 Full English Documentation](docs/README_en.md)

---

## 🚀 Quick Start

### Mode 1: Lite (SQLite, no Redis)

**For:** Testing and development

```bash
cp .env.example .env
docker-compose up -d
curl http://localhost:8000/health
```

**Result:** 1 container, ~50MB RAM ✅

---

### Mode 2: Shared (PostgreSQL + Redis)

**For:** Production with existing infrastructure

```bash
# Edit .env
POSTGRES_USER=postgres
REDIS_HOST=redis

# Run
docker-compose up -d
```

**Result:** 1 container, ~150MB RAM ✅

---

### Mode 3: Full (isolated PostgreSQL + Redis)

**For:** Complete isolation

```bash
cp .env.example .env
docker-compose -f docker-compose.full.yml up -d
curl http://localhost:8000/health
```

**Result:** 3 containers, ~300MB RAM ✅

---

## ⚙️ Basic Setup

### Telegram Notifications

1. **Create a bot:** [@BotFather](https://t.me/BotFather) → `/newbot`
2. **Get Chat ID:** [@userinfobot](https://t.me/userinfobot) → `/start`
3. **Get Topic ID (optional, for forum groups):** Open topic → copy ID from URL
4. **Add to .env:**

```bash
TG_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TG_CHAT_ID=-1001234567890
TG_TOPIC_ID=123  # Optional: Topic ID for forum groups
```

**Note:** `TG_TOPIC_ID` is only required for Telegram forum groups (supergroups with topics enabled).

---

### Email Notifications

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=error-gateway@example.com
EMAIL_TO=admin@example.com,devops@example.com
```

**Important:** For Gmail, use [App Password](https://support.google.com/accounts/answer/185833)

---

## 📚 Full Documentation

| Document | Language | Description |
|----------|----------|----------|
| [docs/README_ru.md](docs/README_ru.md) | 🇷🇺 | Full Russian version (setup, API, integrations) |
| [docs/README_en.md](docs/README_en.md) | 🇬🇧 | Full English version (setup, API, integrations) |

---

## 🔗 Integrations

### Grafana Loki

Bidirectional integration with Grafana Loki:

- **Grafana → Error Gateway:** Webhook for alerts
- **Error Gateway → Loki:** Error log shipping

**Setup:**
```bash
LOKI_URL=http://loki:3100
```

**Full documentation:** [docs/integration/loki.md](docs/integration/loki.md)

---

### Code Examples

Ready-to-use clients for sending errors:

- **Python:** Async client + logging integration
- **JavaScript/Node.js:** Axios client
- **Go:** HTTP client
- **Java:** OkHttp client

**Full examples:** [docs/integration/examples.md](docs/integration/examples.md)

---

## 📊 Operating Modes

| Mode | Database | Rate Limiting | RAM | Containers | For |
|-------|----|---------------|-----|------------|-----|
| **Lite** | SQLite | In-Memory | 50MB | 1 | Testing ✅ |
| **Shared** | PostgreSQL | Redis | 150MB | 1 | Production ✅ |
| **Full** | PostgreSQL | Redis | 300MB | 3 | Isolation |

---

## 🔌 API

### Send an Error

```bash
curl -X POST http://localhost:8000/api/v1/error \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Database connection failed",
    "exception_type": "ConnectionError",
    "stack_trace": "File \"app/db.py\", line 42",
    "environment": "production",
    "release_version": "1.2.3",
    "context": {
      "user_id": 123,
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

**Full API documentation:** [docs/README_en.md#api](docs/README_ru.md#api)

---

## 🧪 Tests

```bash
cd src
uv run pytest
```

**Coverage:** 90% (264 tests) ✅

---

## 👤 Author

**Alexeev Alexandr**

- GitHub: [@officialalexeev](https://github.com/officialalexeev)
- Docker Hub: [officialalexeev/error-gateway](https://hub.docker.com/r/officialalexeev/error-gateway)

## 📝 License

MIT License
