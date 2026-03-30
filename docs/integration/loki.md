# Grafana Loki Integration

[← Back to Documentation](../README_ru.md) | [🇬🇧 English](../README_en.md)

## Overview

Error Gateway supports **bidirectional integration** with Grafana Loki:

1. **Grafana → Error Gateway** (incoming alerts)
2. **Error Gateway → Loki** (outgoing logs)

---

## Setup

### 1. Enable Loki Logging

Add to `.env`:

```bash
LOKI_URL=http://loki:3100
```

**URL Examples:**
- Local: `http://localhost:3100`
- Docker: `http://loki:3100`
- Production: `https://loki.example.com`

### 2. Docker Compose (Full Mode)

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
    command: -config.file=/etc/loki/local-config.yaml
```

---

## How It Works

### Incoming Alerts (Grafana → Error Gateway)

```
Grafana/Loki
    ↓ POST /api/v1/loki/webhook
Error Gateway
    ↓
- LokiAlertProcessor
- ErrorProcessingService
    ↓
- Save to DB
- Notifications (Telegram/Email)
```

**Setup in Grafana:**

1. Open Grafana → Alerting → Notification policies
2. Add webhook:
   ```
   URL: http://error-gateway:8000/api/v1/loki/webhook
   HTTP Method: POST
   ```

### Outgoing Logs (Error Gateway → Loki)

Activated automatically when `LOKI_URL` is set. Every processed error group is shipped to Loki.

```
POST /api/v1/error
    ↓
ProcessErrorUseCase.execute()
    ↓
LokiClient.send_error(group)   ← automatic, fire-and-forget
    ↓
POST /loki/api/v1/push
    ↓
Grafana Loki
```

**Log Format:**

```json
{
  "streams": [
    {
      "stream": {
        "app": "error-gateway",
        "level": "error",
        "exception": "ConnectionError"
      },
      "values": [
        [
          "1774766953984156000",
          "{\"level\":\"error\",\"exception\":\"ConnectionError\",\"message\":\"Database connection failed\",\"count\":1,\"fingerprint\":\"abc123\",\"first_seen\":\"2026-03-29T09:47:33.984156+03:00\",\"last_seen\":\"2026-03-29T09:47:33.984156+03:00\"}"
        ]
      ]
    }
  ]
}
```

---

## Grafana Queries

### Search Errors by Exception Type

```logql
{app="error-gateway", exception="ConnectionError"}
```

### Search by Fingerprint

```logql
{app="error-gateway"} | json | fingerprint = "abc123"
```

### Aggregation by Level

```logql
sum by (level) (count_over_time({app="error-gateway"}[1h]))
```

### Top Exceptions per Hour

```logql
topk(10, sum by (exception) (count_over_time({app="error-gateway"}[1h])))
```

---

## Dashboard Examples

### 1. Overview

```logql
// Total errors in the last hour
sum(count_over_time({app="error-gateway"}[1h]))

// Errors by type
sum by (exception) (count_over_time({app="error-gateway"}[1h]))

// Errors by level
sum by (level) (count_over_time({app="error-gateway"}[1h]))
```

### 2. Error Group Details

```logql
// Find group by fingerprint
{app="error-gateway"} | json | fingerprint = "<fingerprint>"

// Show error context
{app="error-gateway"} | json | message =~ ".*Database.*"
```

---

## Labels

### Default Labels

```python
{
    "app": "error-gateway",
    "level": "error",
    "exception": "<exception_type>"
}
```

### Custom Labels

Configurable in `config.py` (future):

```python
# Future
LOKI_LABELS: dict = {
    "app": "error-gateway",
    "environment": "production",
    "team": "backend"
}
```

---

## Disable Loki

Loki is **disabled** by default. To enable log shipping, explicitly set `LOKI_URL`.

**Check:**

```python
from app.core.config import settings

if settings.use_loki:
    # Loki enabled
    print(f"Loki URL: {settings.LOKI_URL}")
else:
    # Loki disabled
    print("Loki logging disabled")
```

---

## Lifecycle Management

`LokiClient` is created as a singleton on startup (if `LOKI_URL` is set) and closed gracefully on shutdown. No manual configuration needed.

```python
# app/main.py — handled automatically
loki_client = get_loki_client()
if loki_client is not None:
    shutdown_manager.register(loki_client.close)
```

---

## Error Handling

If Loki is unavailable:
- ❌ Error processing is **not interrupted**
- ✅ Error is logged to console
- ✅ Notifications (Telegram/Email) are sent

`LokiClient.send_error()` catches all exceptions internally and returns `False` on failure — it never raises to the caller.

---

## Testing

### Locally

```bash
# 1. Start Loki
docker run -p 3100:3100 grafana/loki:latest

# 2. Configure .env
LOKI_URL=http://localhost:3100

# 3. Start Error Gateway
uv run uvicorn app.main:app --reload

# 4. Send an error
curl -X POST http://localhost:8000/api/v1/error \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test error",
    "exception_type": "TestError"
  }'

# 5. Check in Loki
curl "http://localhost:3100/loki/api/v1/query_range?query={app=\"error-gateway\"}"
```

### Tests

```bash
cd src
uv run pytest tests/infrastructure/test_loki_client.py -v
```

---

## Troubleshooting

### Loki Not Receiving Logs

**Check 1:** Is Loki enabled?

```python
from app.core.config import settings
print(f"LOKI_URL: {settings.LOKI_URL}")
print(f"use_loki: {settings.use_loki}")
```

**Check 2:** Is Loki accessible?

```bash
curl http://loki:3100/ready
# Should return "ready"
```

**Check 3:** Error Gateway logs

```json
{"text": "Loki logging enabled: http://loki:3100\n", ...}
{"text": "Failed to send error to Loki: ...\n", ...}
```

### Send Errors

**Problem:** `ConnectionError: Connection refused`

**Solution:** Check that Loki is running and accessible.

**Problem:** `HTTP 400 Bad Request`

**Solution:** Check log format. Loki requires specific JSON format.

---

## Best Practices

### 1. Don't Enable Without Need

Loki is needed only if:
- ✅ Using Grafana for monitoring
- ✅ Need long-term log storage
- ✅ Need complex queries for analysis

### 2. Use Labels

Add labels for filtering:
- `environment: production/staging`
- `service: error-gateway`
- `team: backend`

### 3. Configure Retention

Loki stores logs for 31 days by default. Configure for your needs:

```yaml
# loki-config.yaml
limits_config:
  retention_period: 2160h  # 90 days
```

### 4. Monitor Loki

Monitor:
- Storage size
- Request count
- Response time

---

## Alternatives

If Loki doesn't fit:

1. **ELK Stack** (Elasticsearch, Logstash, Kibana)
   - More powerful search
   - More complex setup

2. **Datadog**
   - SaaS solution
   - Paid

3. **Splunk**
   - Enterprise solution
   - Expensive

---

## Links

- [Grafana Loki Documentation](https://grafana.com/docs/loki/latest/)
- [LogQL Documentation](https://grafana.com/docs/loki/latest/logql/)
- [Error Gateway GitHub](https://github.com/officialalexeev/Error_Gateway)

---

[← Back to Documentation](../README_ru.md) | [🇬🇧 English](../README_en.md) | [Code Examples](examples.md)
