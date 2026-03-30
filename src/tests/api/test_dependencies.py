"""
Tests for API Dependencies.

Testing Pattern: dependency_overrides (FastAPI best practice)
"""

from unittest.mock import AsyncMock, Mock

import pytest
from app.api.v1.rate_limit_deps import check_rate_limit, get_rate_limiter_service


class TestCheckRateLimit:
    """Tests for check_rate_limit dependency."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self):
        """Test that rate limit allows request."""
        # Mock rate limiter
        mock_rate_limiter = Mock()
        mock_rate_limiter.is_allowed = AsyncMock(return_value=True)
        mock_rate_limiter.get_remaining = AsyncMock(return_value=99)
        mock_rate_limiter.limit = 100

        # Mock request with headers dict (for get_client_ip)
        mock_request = Mock()
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {}

        # Call dependency
        result = await check_rate_limit(mock_request, mock_rate_limiter)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self):
        """Test that rate limit is exceeded."""
        from fastapi import HTTPException

        # Mock rate limiter
        mock_rate_limiter = Mock()
        mock_rate_limiter.is_allowed = AsyncMock(return_value=False)
        mock_rate_limiter.get_remaining = AsyncMock(return_value=0)
        mock_rate_limiter.limit = 100

        # Mock request with headers dict (for get_client_ip)
        mock_request = Mock()
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {}

        # Call dependency - should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit(mock_request, mock_rate_limiter)

        assert exc_info.value.status_code == 429


class TestGetRateLimiterService:
    """Tests for get_rate_limiter_service dependency."""

    def test_get_rate_limiter_returns_in_memory(self):
        """Test that InMemoryRateLimitService is returned when Redis is not configured.

        The container is built at startup with the current settings.  In the test
        environment REDIS_URL is empty, so InMemoryRateLimitService is expected.
        """
        from app.domain.services.services import InMemoryRateLimitService

        service = get_rate_limiter_service()
        assert isinstance(service, InMemoryRateLimitService)
