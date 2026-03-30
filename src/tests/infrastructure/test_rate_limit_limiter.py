"""
Extended Tests for Async Redis Rate Limiter.

Test Isolation Principle:
- Mock Redis client
- Test only rate limiting logic

Async: Async tests
"""

from unittest.mock import AsyncMock, patch

import pytest
from app.infrastructure.rate_limit.limiter import AsyncRedisRateLimitService


class TestAsyncRedisRateLimitServiceExtended:
    """Extended tests for AsyncRedisRateLimitService."""

    @pytest.mark.asyncio
    async def test_is_allowed_within_limit(self):
        """Test request within limit."""
        mock_redis = AsyncMock()
        mock_redis.zcard.return_value = 2  # Current counter
        mock_redis.zremrangebyscore.return_value = 0

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=5, window_seconds=60
            )

            result = await service.is_allowed("test_key")

            assert result is True
            mock_redis.zremrangebyscore.assert_called_once()
            mock_redis.zcard.assert_called_once()
            mock_redis.zadd.assert_called_once()
            mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_allowed_limit_exceeded(self):
        """Test limit exceeded."""
        mock_redis = AsyncMock()
        mock_redis.zcard.return_value = 5  # Limit reached
        mock_redis.zremrangebyscore.return_value = 0

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=5, window_seconds=60
            )

            result = await service.is_allowed("test_key")

            assert result is False
            mock_redis.zadd.assert_not_called()

    @pytest.mark.asyncio
    async def test_is_allowed_custom_limit(self):
        """Test custom limit."""
        mock_redis = AsyncMock()
        mock_redis.zcard.return_value = 3

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=10, window_seconds=60
            )

            # Override limit to 5
            result = await service.is_allowed("test_key", limit=5, window_seconds=30)

            # 3 < 5, so should pass
            assert result is True

    @pytest.mark.asyncio
    async def test_is_allowed_custom_window(self):
        """Test custom window."""
        mock_redis = AsyncMock()
        mock_redis.zcard.return_value = 0

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=10, window_seconds=60
            )

            result = await service.is_allowed("test_key", limit=5, window_seconds=30)

            assert result is True
            # Check that expire is set to custom window
            mock_redis.expire.assert_called_once()
            call_args = mock_redis.expire.call_args
            assert call_args[0][1] == 30

    @pytest.mark.asyncio
    async def test_get_remaining_full_limit(self):
        """Test getting full limit."""
        mock_redis = AsyncMock()
        mock_redis.zcard.return_value = 0
        mock_redis.zremrangebyscore.return_value = 0

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=10, window_seconds=60
            )

            remaining = await service.get_remaining("test_key")

            assert remaining == 10

    @pytest.mark.asyncio
    async def test_get_remaining_partial(self):
        """Test getting partial limit."""
        mock_redis = AsyncMock()
        mock_redis.zcard.return_value = 7
        mock_redis.zremrangebyscore.return_value = 0

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=10, window_seconds=60
            )

            remaining = await service.get_remaining("test_key")

            assert remaining == 3  # 10 - 7 = 3

    @pytest.mark.asyncio
    async def test_get_remaining_zero(self):
        """Test getting zero requests."""
        mock_redis = AsyncMock()
        mock_redis.zcard.return_value = 15  # More than limit
        mock_redis.zremrangebyscore.return_value = 0

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=10, window_seconds=60
            )

            remaining = await service.get_remaining("test_key")

            assert remaining == 0  # max(0, 10 - 15) = 0

    @pytest.mark.asyncio
    async def test_get_remaining_custom_limit(self):
        """Test getting with custom limit."""
        mock_redis = AsyncMock()
        mock_redis.zcard.return_value = 3

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=10, window_seconds=60
            )

            remaining = await service.get_remaining("test_key", limit=5)

            assert remaining == 2  # 5 - 3 = 2

    @pytest.mark.asyncio
    async def test_close_success(self):
        """Test successful connection close."""
        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=5, window_seconds=60
            )

            await service.close()

            mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_exception_handling(self):
        """Test exception handling during close."""
        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock(side_effect=Exception("Connection error"))

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=5, window_seconds=60
            )

            # Should not raise exception
            await service.close()

    @pytest.mark.asyncio
    async def test_is_allowed_removes_old_entries(self):
        """Test removing old entries."""
        mock_redis = AsyncMock()
        mock_redis.zcard.return_value = 0

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=5, window_seconds=60
            )

            await service.is_allowed("test_key")

            # Check that zremrangebyscore was called to remove old entries
            mock_redis.zremrangebyscore.assert_called_once()
            call_args = mock_redis.zremrangebyscore.call_args
            # First argument - key, second - min score (can be "-inf" or number)
            assert call_args[0][0].startswith("ratelimit:")
            # Second argument exists
            assert call_args[0][1] is not None

    @pytest.mark.asyncio
    async def test_is_allowed_sets_expiry(self):
        """Test expiry time setting."""
        mock_redis = AsyncMock()
        mock_redis.zcard.return_value = 0

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=5, window_seconds=120
            )

            await service.is_allowed("test_key")

            # Check that expire is set to window_seconds
            mock_redis.expire.assert_called_once()
            call_args = mock_redis.expire.call_args
            assert call_args[0][1] == 120

    @pytest.mark.asyncio
    async def test_different_keys_independent(self):
        """Test key independence."""
        mock_redis = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=5, window_seconds=60
            )

            # Key 1: 5 requests
            mock_redis.zcard.return_value = 0
            await service.is_allowed("key1")
            mock_redis.zcard.return_value = 1
            await service.is_allowed("key1")
            mock_redis.zcard.return_value = 2
            await service.is_allowed("key1")
            mock_redis.zcard.return_value = 3
            await service.is_allowed("key1")
            mock_redis.zcard.return_value = 4
            await service.is_allowed("key1")
            mock_redis.zcard.return_value = 5  # Limit reached

            # Key 2: should pass independently
            mock_redis.zcard.return_value = 0
            result = await service.is_allowed("key2")

            assert result is True

    @pytest.mark.asyncio
    async def test_key_prefix_used(self):
        """Test key prefix usage."""
        mock_redis = AsyncMock()
        mock_redis.zcard.return_value = 0

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=5, window_seconds=60
            )

            await service.is_allowed("test_key")

            # Check that key uses prefix
            call_args = mock_redis.zremrangebyscore.call_args
            redis_key = call_args[0][0]
            assert redis_key.startswith("ratelimit:")
            assert "test_key" in redis_key

    @pytest.mark.asyncio
    async def test_is_allowed_with_time_based_window(self):
        """Test time-based window."""
        mock_redis = AsyncMock()
        mock_redis.zcard.return_value = 0

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=5, window_seconds=1
            )

            # First request
            result1 = await service.is_allowed("test_key")
            assert result1 is True

            # Check that zremrangebyscore is called with correct time
            assert mock_redis.zremrangebyscore.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_remaining_after_requests(self):
        """Test getting remaining after requests."""
        mock_redis = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=10, window_seconds=60
            )

            # Initially 10
            mock_redis.zcard.return_value = 0
            assert await service.get_remaining("test_key") == 10

            # After 3 requests
            mock_redis.zcard.return_value = 3
            assert await service.get_remaining("test_key") == 7

            # After 7 requests
            mock_redis.zcard.return_value = 7
            assert await service.get_remaining("test_key") == 3

            # After 10 requests
            mock_redis.zcard.return_value = 10
            assert await service.get_remaining("test_key") == 0

    @pytest.mark.asyncio
    async def test_is_allowed_zadd_with_timestamp(self):
        """Test adding request with timestamp."""
        mock_redis = AsyncMock()
        mock_redis.zcard.return_value = 0

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            service = AsyncRedisRateLimitService(
                redis_url="redis://localhost:6379", limit=5, window_seconds=60
            )

            await service.is_allowed("test_key")

            # Check that zadd is called with timestamp
            mock_redis.zadd.assert_called_once()
            call_args = mock_redis.zadd.call_args
            assert len(call_args[0][1]) == 1  # One element added
