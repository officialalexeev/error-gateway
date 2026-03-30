"""
Tests for Grafana Loki Client.

Test Isolation Principle:
- Mock HTTP requests
- Test only client logic

Async: Async tests
"""

from unittest.mock import AsyncMock, patch

import pytest
from app.domain.entities.error_group import ErrorGroup
from app.infrastructure.loki.client import LokiClient


class TestLokiClient:
    """Tests for Grafana Loki client."""

    def test_init_default_labels(self):
        """Test initialization with default labels."""
        client = LokiClient(url="http://loki:3100")

        assert client.url == "http://loki:3100"
        assert client.labels == {"app": "error-gateway"}

    def test_init_custom_labels(self):
        """Test initialization with custom labels."""
        custom_labels = {"app": "custom-app", "env": "production"}
        client = LokiClient(url="http://loki:3100", labels=custom_labels)

        assert client.url == "http://loki:3100"
        assert client.labels == {"app": "custom-app", "env": "production"}

    @pytest.mark.asyncio
    async def test_send_error_no_url(self, sample_error_group):
        """Test send without URL (should return False)."""
        client = LokiClient(url="")

        result = await client.send_error(sample_error_group)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_error_success(self, sample_error_group):
        """Test successful send to Loki."""
        client = LokiClient(url="http://loki:3100")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 204

            result = await client.send_error(sample_error_group)

            assert result is True
            mock_post.assert_called_once()

            # Check call URL
            call_args = mock_post.call_args
            assert call_args[0][0] == "http://loki:3100/loki/api/v1/push"

            # Check headers
            assert call_args[1]["headers"] == {"Content-Type": "application/json"}

            # Check payload structure
            payload = call_args[1]["json"]
            assert "streams" in payload
            assert len(payload["streams"]) == 1

            stream = payload["streams"][0]
            assert stream["stream"]["level"] == "error"
            assert stream["stream"]["exception"] == sample_error_group.exception_type
            assert stream["stream"]["app"] == "error-gateway"

            # Check values
            assert len(stream["values"]) == 1
            log_entry = stream["values"][0][1]
            assert sample_error_group.exception_type in log_entry
            assert sample_error_group.message in log_entry

    @pytest.mark.asyncio
    async def test_send_error_failure_status_code(self, sample_error_group):
        """Test failed send (non-204 status)."""
        client = LokiClient(url="http://loki:3100")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 500

            result = await client.send_error(sample_error_group)

            assert result is False

    @pytest.mark.asyncio
    async def test_send_error_exception_handling(self, sample_error_group):
        """Test exception handling during send."""
        client = LokiClient(url="http://loki:3100")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Connection error")

            result = await client.send_error(sample_error_group)

            assert result is False

    @pytest.mark.asyncio
    async def test_send_error_with_custom_labels(self, sample_error_group):
        """Test send with custom labels."""
        custom_labels = {"app": "my-app", "env": "staging", "team": "backend"}
        client = LokiClient(url="http://loki:3100", labels=custom_labels)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 204

            await client.send_error(sample_error_group)

            payload = mock_post.call_args[1]["json"]
            stream = payload["streams"][0]["stream"]

            assert stream["app"] == "my-app"
            assert stream["env"] == "staging"
            assert stream["team"] == "backend"
            assert stream["level"] == "error"
            assert stream["exception"] == sample_error_group.exception_type

    @pytest.mark.asyncio
    async def test_format_log(self, sample_error_group):
        """Test log formatting."""
        client = LokiClient(url="http://loki:3100")

        log_str = client._format_log(sample_error_group)

        import json

        log_data = json.loads(log_str)

        assert log_data["level"] == "error"
        assert log_data["exception"] == sample_error_group.exception_type
        assert log_data["message"] == sample_error_group.message
        assert log_data["count"] == sample_error_group.count
        assert log_data["fingerprint"] == sample_error_group.fingerprint
        assert "first_seen" in log_data
        assert "last_seen" in log_data

    @pytest.mark.asyncio
    async def test_close(self):
        """Test HTTP client close."""
        client = LokiClient(url="http://loki:3100")

        # Should not raise
        await client.close()

    @pytest.mark.asyncio
    async def test_send_error_preserves_error_group_data(self, sample_error_group):
        """Test error group data preservation in log."""
        client = LokiClient(url="http://loki:3100")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 204

            await client.send_error(sample_error_group)

            payload = mock_post.call_args[1]["json"]
            log_entry_str = payload["streams"][0]["values"][0][1]

            import json

            log_entry = json.loads(log_entry_str)

            # Check all key fields
            assert log_entry["exception"] == sample_error_group.exception_type
            assert log_entry["message"] == sample_error_group.message
            assert log_entry["count"] == sample_error_group.count
            assert log_entry["fingerprint"] == sample_error_group.fingerprint


class TestLokiClientIntegration:
    """Integration tests for Loki client."""

    @pytest.mark.asyncio
    async def test_multiple_send_errors(self, sample_error_group):
        """Test multiple error sends."""
        client = LokiClient(url="http://loki:3100")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 204

            # Send 3 errors
            for i in range(3):
                sample_error_group.count = i + 1
                result = await client.send_error(sample_error_group)
                assert result is True

            assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_send_error_with_empty_group(self):
        """Test send with empty group."""
        client = LokiClient(url="http://loki:3100")

        empty_group = ErrorGroup(
            fingerprint="empty-fingerprint",
            exception_type="EmptyError",
            message="",
            count=0,
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 204

            result = await client.send_error(empty_group)

            assert result is True
            mock_post.assert_called_once()
