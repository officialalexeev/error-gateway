"""
Tests for Rate Limiting.

Async: Async tests
"""

import asyncio

import pytest


class TestInMemoryRateLimitService:
    """Tests for InMemoryRateLimitService."""

    @pytest.mark.asyncio
    async def test_is_allowed_first_request(self):
        """Test first request."""
        from app.domain.services.services import InMemoryRateLimitService

        service = InMemoryRateLimitService(limit=5, window_seconds=60)
        result = await service.is_allowed("test_key")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_allowed_within_limit(self):
        """Test requests within limit."""
        from app.domain.services.services import InMemoryRateLimitService

        service = InMemoryRateLimitService(limit=3, window_seconds=60)

        # First 3 requests should pass
        assert await service.is_allowed("test_key") is True
        assert await service.is_allowed("test_key") is True
        assert await service.is_allowed("test_key") is True

        # 4th should be rejected
        assert await service.is_allowed("test_key") is False

    @pytest.mark.asyncio
    async def test_is_allowed_window_expired(self):
        """Test window expiration."""
        from app.domain.services.services import InMemoryRateLimitService

        service = InMemoryRateLimitService(limit=2, window_seconds=1)

        # Exhaust limit
        assert await service.is_allowed("test_key") is True
        assert await service.is_allowed("test_key") is True
        assert await service.is_allowed("test_key") is False

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Now should pass
        assert await service.is_allowed("test_key") is True

    @pytest.mark.asyncio
    async def test_get_remaining(self):
        """Test getting remaining count."""
        from app.domain.services.services import InMemoryRateLimitService

        service = InMemoryRateLimitService(limit=5, window_seconds=60)

        # Initially 5
        remaining = await service.get_remaining("test_key")
        assert remaining == 5

        # One request
        await service.is_allowed("test_key")
        remaining = await service.get_remaining("test_key")
        assert remaining == 4

        # Three more
        await service.is_allowed("test_key")
        await service.is_allowed("test_key")
        await service.is_allowed("test_key")
        remaining = await service.get_remaining("test_key")
        assert remaining == 1

    @pytest.mark.asyncio
    async def test_different_keys(self):
        """Test different keys."""
        from app.domain.services.services import InMemoryRateLimitService

        service = InMemoryRateLimitService(limit=2, window_seconds=60)

        # Key 1
        await service.is_allowed("key1")
        await service.is_allowed("key1")
        assert await service.is_allowed("key1") is False

        # Key 2 (independent)
        assert await service.is_allowed("key2") is True
        assert await service.is_allowed("key2") is True
        assert await service.is_allowed("key2") is False

    @pytest.mark.asyncio
    async def test_custom_limit(self):
        """Test custom limit."""
        from app.domain.services.services import InMemoryRateLimitService

        service = InMemoryRateLimitService(limit=10, window_seconds=60)

        # Override limit
        for _i in range(5):
            assert await service.is_allowed("test_key", limit=5) is True

        assert await service.is_allowed("test_key", limit=5) is False


class TestAsyncRedisRateLimitService:
    """Tests for AsyncRedisRateLimitService."""

    @pytest.mark.asyncio
    async def test_init(self):
        """Test service initialization."""
        from app.infrastructure.rate_limit.limiter import AsyncRedisRateLimitService

        service = AsyncRedisRateLimitService(
            redis_url="redis://localhost:6379", limit=5, window_seconds=60
        )

        assert service.limit == 5
        assert service.window_seconds == 60
        assert service.key_prefix == "ratelimit:"
        assert service.redis_client is not None

        # Cleanup
        await service.redis_client.aclose()

    @pytest.mark.asyncio
    async def test_close(self):
        """Test connection close."""
        from app.infrastructure.rate_limit.limiter import AsyncRedisRateLimitService

        service = AsyncRedisRateLimitService(
            redis_url="redis://localhost:6379", limit=5, window_seconds=60
        )

        # Should not raise
        await service.close()
