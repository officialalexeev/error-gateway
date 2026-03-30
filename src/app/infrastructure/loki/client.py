"""Grafana Loki HTTP client for sending error logs."""

import json
from datetime import datetime, timezone

import httpx
from app.core.logger import log
from app.domain.entities.error_group import ErrorGroup
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class LokiClient:
    """Grafana Loki HTTP client for sending error logs."""

    def __init__(self, url: str, labels: dict[str, str] | None = None):
        """Initialize Loki client with URL and optional labels."""
        self.url = url
        self.labels = labels or {"app": "error-gateway"}
        self._client = httpx.AsyncClient(timeout=10.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def _send_with_retry(self, log_entry: dict) -> bool:
        """Send log with retry logic."""
        response = await self._client.post(
            f"{self.url}/loki/api/v1/push",
            json=log_entry,
            headers={"Content-Type": "application/json"},
        )
        return response.status_code == 204

    async def send_error(self, error_group: ErrorGroup) -> bool:
        """Send error log to Loki."""
        if not self.url:
            return False

        try:
            log_entry = {
                "streams": [
                    {
                        "stream": {
                            **self.labels,
                            "level": "error",
                            "exception": error_group.exception_type,
                        },
                        "values": [
                            [
                                str(int(datetime.now(timezone.utc).timestamp() * 1e9)),
                                self._format_log(error_group),
                            ]
                        ],
                    }
                ]
            }

            return await self._send_with_retry(log_entry)

        except Exception as e:
            log.error(f"Loki notification error (after retries): {e}")
            return False

    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()

    def _format_log(self, error_group: ErrorGroup) -> str:
        """Format log for Loki."""
        return json.dumps(
            {
                "level": "error",
                "exception": error_group.exception_type,
                "message": error_group.message,
                "count": error_group.count,
                "fingerprint": error_group.fingerprint,
                "first_seen": str(error_group.first_seen),
                "last_seen": str(error_group.last_seen),
            }
        )
