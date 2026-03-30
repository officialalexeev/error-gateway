"""Async Redis rate limiter with sliding window algorithm.

Uses redis.asyncio module from redis-py (tested with 7.4.0).
All Redis commands are async coroutines requiring await.
"""

import time

import redis.asyncio as redis
from app.core.logger import log
from app.domain.services.services import InMemoryRateLimitService, RateLimitService


def create_rate_limiter(
    redis_url: str | None,
    limit: int = 100,
    window_seconds: int = 60,
) -> RateLimitService:
    """
    Create rate limiter service based on configuration.

    Args:
        redis_url: Redis connection URL. If None, uses in-memory limiter.
        limit: Maximum requests per window.
        window_seconds: Window size in seconds.

    Returns:
        RateLimitService instance (Redis or In-Memory).
    """
    if redis_url:
        return AsyncRedisRateLimitService(
            redis_url=redis_url,
            limit=limit,
            window_seconds=window_seconds,
        )
    return InMemoryRateLimitService(
        limit=limit,
        window_seconds=window_seconds,
    )


class AsyncRedisRateLimitService(RateLimitService):
    """Async Redis rate limiter with sliding window algorithm."""

    def __init__(
        self,
        redis_url: str,
        limit: int = 100,
        window_seconds: int = 60,
    ):
        """Initialize Redis rate limiter with connection URL."""
        self.limit = limit
        self.window_seconds = window_seconds
        self.key_prefix = "ratelimit:"
        self.redis_client = redis.from_url(redis_url)

    async def close(self):
        """Close Redis connection."""
        try:
            # Use aclose() for redis-py >= 5.0, fallback to close() for older versions
            if hasattr(self.redis_client, "aclose"):
                await self.redis_client.aclose()
            else:
                await self.redis_client.close()
        except Exception as e:
            log.error(f"Error closing Redis connection: {e}")

    async def is_allowed(
        self,
        key: str,
        limit: int | None = None,
        window_seconds: int | None = None,
    ) -> bool:
        """Check if request is allowed."""
        limit = limit or self.limit
        window_seconds = window_seconds or self.window_seconds

        now = time.time()
        window_start = now - window_seconds

        redis_key = f"{self.key_prefix}{key}"

        # Remove old entries
        await self.redis_client.zremrangebyscore(redis_key, "-inf", window_start)

        # Count current requests
        current_count = await self.redis_client.zcard(redis_key)

        if current_count >= limit:
            return False

        # Add current request
        await self.redis_client.zadd(redis_key, {str(now): now})
        await self.redis_client.expire(redis_key, window_seconds)

        return True

    async def get_remaining(
        self,
        key: str,
        limit: int | None = None,
        window_seconds: int | None = None,
    ) -> int:
        """Get remaining requests count."""
        limit = limit or self.limit
        window_seconds = window_seconds or self.window_seconds

        now = time.time()
        window_start = now - window_seconds

        redis_key = f"{self.key_prefix}{key}"

        # Count current requests
        await self.redis_client.zremrangebyscore(redis_key, "-inf", window_start)
        current_count = await self.redis_client.zcard(redis_key)

        return max(0, limit - current_count)
