# Error Gateway — Integration Examples

[← Back to Documentation](../README_ru.md) | [🇬🇧 English](../README_en.md)

This file contains integration examples for Error Gateway in various programming languages.

---

## Table of Contents

- [Python](#python)
- [JavaScript/Node.js](#javascriptnodejs)
- [Go](#go)
- [Java](#java)
- [cURL](#curl)

---

## Python

### Installation

```bash
pip install httpx
```

### Basic Example

```python
import httpx
from typing import Any, Dict

class ErrorGatewayClient:
    """Client for Error Gateway API."""

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=timeout)

    async def send_error(
        self,
        message: str,
        exception_type: str = "Error",
        stack_trace: str | None = None,
        context: Dict[str, Any] | None = None,
        environment: str = "production",
        release_version: str | None = None,
    ) -> dict:
        """
        Send error to Error Gateway.

        Args:
            message: Error message
            exception_type: Exception type
            stack_trace: Stack trace string
            context: Additional context data
            environment: Environment name
            release_version: Application version

        Returns:
            Response data
        """
        payload = {
            "message": message,
            "exception_type": exception_type,
            "stack_trace": stack_trace,
            "context": context or {},
            "environment": environment,
            "release_version": release_version,
        }

        response = await self.client.post(
            f"{self.base_url}/api/v1/error",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Usage example
async def main():
    client = ErrorGatewayClient("http://localhost:8000")

    try:
        result = await client.send_error(
            message="Database connection failed",
            exception_type="ConnectionError",
            stack_trace="File 'app/db.py', line 42",
            context={"user_id": 123, "email": "test@example.com"},
            environment="production",
            release_version="1.0.0",
        )
        print(f"Error sent: {result}")
    finally:
        await client.close()
```

### Logging Integration

```python
import logging
import asyncio
from error_gateway import ErrorGatewayClient

class ErrorGatewayHandler(logging.Handler):
    """Logging handler for Error Gateway."""

    def __init__(self, base_url: str):
        super().__init__(level=logging.ERROR)
        self.client = ErrorGatewayClient(base_url)

    def emit(self, record: logging.LogRecord):
        """Send log record to Error Gateway."""
        try:
            asyncio.get_event_loop().run_until_complete(
                self.client.send_error(
                    message=record.getMessage(),
                    exception_type=record.levelname,
                    environment="production",
                )
            )
        except Exception:
            self.handleError(record)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

handler = ErrorGatewayHandler("http://localhost:8000")
logger.addHandler(handler)

# Now all ERROR logs will be sent to Error Gateway
logger.error("Something went wrong")
```

---

## JavaScript/Node.js

### Installation

```bash
npm install axios
```

### Basic Example

```javascript
const axios = require('axios');

class ErrorGatewayClient {
  constructor(baseUrl, timeout = 10000) {
    this.base_url = baseUrl;
    this.client = axios.create({
      baseURL: baseUrl,
      timeout: timeout,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  async sendError({
    message,
    exception_type = 'Error',
    stack_trace = null,
    context = {},
    environment = 'production',
    release_version = null,
  }) {
    const payload = {
      message,
      exception_type,
      stack_trace,
      context,
      environment,
      release_version,
    };

    const response = await this.client.post('/api/v1/error', payload);
    return response.data;
  }
}

// Usage example
async function main() {
  const client = new ErrorGatewayClient('http://localhost:8000');

  try {
    const result = await client.sendError({
      message: 'Database connection failed',
      exception_type: 'ConnectionError',
      stack_trace: 'File \'app/db.js\', line 42',
      context: { user_id: 123, email: 'test@example.com' },
      environment: 'production',
      release_version: '1.0.0',
    });
    console.log('Error sent:', result);
  } catch (error) {
    console.error('Failed to send error:', error);
  }
}

main();
```

### Process Integration

```javascript
// Catch unhandled promise rejections
process.on('unhandledRejection', async (reason, promise) => {
  const client = new ErrorGatewayClient('http://localhost:8000');

  await client.sendError({
    message: `Unhandled Rejection: ${reason}`,
    exception_type: 'UnhandledRejection',
    environment: 'production',
  });
});

// Catch uncaught exceptions
process.on('uncaughtException', async (error) => {
  const client = new ErrorGatewayClient('http://localhost:8000');

  await client.sendError({
    message: error.message,
    exception_type: error.name,
    stack_trace: error.stack,
    environment: 'production',
  });

  process.exit(1);
});
```

---

## Go

### Installation

```bash
go get github.com/go-resty/resty/v2
```

### Basic Example

```go
package main

import (
    "fmt"
    "github.com/go-resty/resty/v2"
)

type ErrorGatewayClient struct {
    client *resty.Client
}

func NewErrorGatewayClient(baseURL string) *ErrorGatewayClient {
    client := resty.New()
    client.SetBaseURL(baseURL)
    client.SetTimeout(10 * time.Second)

    return &ErrorGatewayClient{client: client}
}

type ErrorPayload struct {
    Message        string                 `json:"message"`
    ExceptionType  string                 `json:"exception_type"`
    StackTrace     *string                `json:"stack_trace,omitempty"`
    Context        map[string]interface{} `json:"context"`
    Environment    string                 `json:"environment"`
    ReleaseVersion *string                `json:"release_version,omitempty"`
}

func (c *ErrorGatewayClient) SendError(payload ErrorPayload) (map[string]interface{}, error) {
    resp, err := c.client.R().
        SetBody(payload).
        Post("/api/v1/error")

    if err != nil {
        return nil, err
    }

    var result map[string]interface{}
    err = resp.UnmarshalResult(&result)
    return result, err
}

// Usage example
func main() {
    client := NewErrorGatewayClient("http://localhost:8000")

    stackTrace := "File 'app/main.go', line 42"
    releaseVersion := "1.0.0"

    result, err := client.SendError(ErrorPayload{
        Message:       "Database connection failed",
        ExceptionType: "ConnectionError",
        StackTrace:    &stackTrace,
        Context: map[string]interface{}{
            "user_id": 123,
            "email":   "test@example.com",
        },
        Environment:    "production",
        ReleaseVersion: &releaseVersion,
    })

    if err != nil {
        fmt.Printf("Failed to send error: %v\n", err)
        return
    }

    fmt.Printf("Error sent: %v\n", result)
}
```

---

## Java

### Maven Dependencies

```xml
<dependencies>
    <dependency>
        <groupId>com.squareup.retrofit2</groupId>
        <artifactId>retrofit</artifactId>
        <version>2.9.0</version>
    </dependency>
    <dependency>
        <groupId>com.squareup.retrofit2</groupId>
        <artifactId>converter-gson</artifactId>
        <version>2.9.0</version>
    </dependency>
</dependencies>
```

### Basic Example

```java
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;
import retrofit2.http.Body;
import retrofit2.http.POST;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

public class ErrorGatewayClient {

    public interface ErrorGatewayService {
        @POST("/api/v1/error")
        CompletableFuture<Map<String, Object>> sendError(@Body ErrorPayload payload);
    }

    public static class ErrorPayload {
        public String message;
        public String exception_type;
        public String stack_trace;
        public Map<String, Object> context;
        public String environment;
        public String release_version;

        // Constructor, getters, setters
    }

    private final ErrorGatewayService service;

    public ErrorGatewayClient(String baseUrl) {
        Retrofit retrofit = new Retrofit.Builder()
            .baseUrl(baseUrl)
            .addConverterFactory(GsonConverterFactory.create())
            .build();

        service = retrofit.create(ErrorGatewayService.class);
    }

    public CompletableFuture<Map<String, Object>> sendError(ErrorPayload payload) {
        return service.sendError(payload);
    }

    // Usage example
    public static void main(String[] args) {
        ErrorGatewayClient client = new ErrorGatewayClient("http://localhost:8000");

        ErrorPayload payload = new ErrorPayload();
        payload.message = "Database connection failed";
        payload.exception_type = "ConnectionError";
        payload.environment = "production";

        client.sendError(payload)
            .thenAccept(result -> System.out.println("Error sent: " + result))
            .exceptionally(ex -> {
                System.err.println("Failed to send error: " + ex.getMessage());
                return null;
            });
    }
}
```

---

## cURL

### Send Error

```bash
curl -X POST http://localhost:8000/api/v1/error \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Database connection failed",
    "exception_type": "ConnectionError",
    "stack_trace": "File \"app/db.py\", line 42",
    "context": {
      "user_id": 123,
      "email": "test@example.com"
    },
    "environment": "production",
    "release_version": "1.0.0"
  }'
```

### Get Error Groups List

```bash
curl http://localhost:8000/api/v1/groups?limit=50&offset=0
```

### Get Group Details

```bash
curl http://localhost:8000/api/v1/groups/{group_id}
```

### Health Check

```bash
curl http://localhost:8000/health
```

### Prometheus Metrics

```bash
curl http://localhost:8000/api/v1/metrics
```

---

## Additional Resources

- [API Documentation](../README_ru.md#api)
- [Loki Integration](loki.md)
- [README_ru.md](../README_ru.md)
- [README_en.md](../README_en.md)

---

[← Back to Documentation](../README_ru.md) | [🇬🇧 English](../README_en.md) | [Loki Integration](loki.md)
