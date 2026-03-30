"""Extended tests for InMemoryRateLimitService - cleanup and eviction logic."""

import asyncio
import time

import pytest
from app.domain.services.services import InMemoryRateLimitService


class TestInMemoryRateLimitServiceCleanup:
    """Tests for cleanup() method and memory leak prevention."""

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_keys(self):
        """Test that cleanup removes keys older than max_age_seconds."""
        limiter = InMemoryRateLimitService(limit=100, window_seconds=60)

        # Add old key (1 hour ago)
        old_time = time.time() - 3600
        limiter._requests["old_key"] = [old_time]

        # Add recent key (1 minute ago)
        recent_time = time.time() - 60
        limiter._requests["recent_key"] = [recent_time]

        # Cleanup with max_age=30 minutes (1800 seconds)
        removed = await limiter.cleanup(max_age_seconds=1800)

        # Old key should be removed, recent key should remain
        assert removed == 1
        assert "old_key" not in limiter._requests
        assert "recent_key" in limiter._requests

    @pytest.mark.asyncio
    async def test_cleanup_default_max_age(self):
        """Test that cleanup uses default max_age when not specified."""
        limiter = InMemoryRateLimitService(limit=100, window_seconds=60)

        # Add old key (2 hours ago)
        old_time = time.time() - 7200
        limiter._requests["old_key"] = [old_time]

        # Cleanup with default max_age (should be max(3600, 60*10) = 3600)
        removed = await limiter.cleanup()

        # Old key should be removed (older than 1 hour)
        assert removed == 1
        assert "old_key" not in limiter._requests

    @pytest.mark.asyncio
    async def test_cleanup_no_old_keys(self):
        """Test cleanup when no keys are old."""
        limiter = InMemoryRateLimitService(limit=100, window_seconds=60)

        # Add recent keys
        now = time.time()
        limiter._requests["key1"] = [now - 10]
        limiter._requests["key2"] = [now - 20]
        limiter._requests["key3"] = [now - 30]

        # Cleanup with max_age=1 hour
        removed = await limiter.cleanup(max_age_seconds=3600)

        # No keys should be removed
        assert removed == 0
        assert len(limiter._requests) == 3

    @pytest.mark.asyncio
    async def test_cleanup_evicts_excess_keys(self):
        """Test that cleanup evicts keys when exceeding max_keys."""
        # Create limiter with small max_keys
        limiter = InMemoryRateLimitService(limit=100, window_seconds=60, max_keys=3)

        # Add 5 keys with different ages
        now = time.time()
        limiter._requests["oldest"] = [now - 500]
        limiter._requests["old"] = [now - 400]
        limiter._requests["middle"] = [now - 300]
        limiter._requests["new"] = [now - 200]
        limiter._requests["newest"] = [now - 100]

        # Cleanup with max_age=1 hour (no old keys to remove)
        # But should evict 2 keys to get back to max_keys=3
        removed = await limiter.cleanup(max_age_seconds=3600)

        # Should evict 2 oldest keys
        assert removed == 2
        assert len(limiter._requests) == 3
        # Oldest keys should be evicted
        assert "oldest" not in limiter._requests
        assert "old" not in limiter._requests
        # Newest keys should remain
        assert "middle" in limiter._requests
        assert "new" in limiter._requests
        assert "newest" in limiter._requests

    @pytest.mark.asyncio
    async def test_cleanup_empty_requests(self):
        """Test cleanup when no requests exist."""
        limiter = InMemoryRateLimitService(limit=100, window_seconds=60)

        # No requests added
        removed = await limiter.cleanup(max_age_seconds=3600)

        assert removed == 0
        assert len(limiter._requests) == 0

    @pytest.mark.asyncio
    async def test_cleanup_thread_safety_with_lock(self):
        """Test that cleanup uses lock for thread safety."""
        limiter = InMemoryRateLimitService(limit=100, window_seconds=60)

        # Add some keys
        now = time.time()
        limiter._requests["key1"] = [now - 100]
        limiter._requests["key2"] = [now - 200]

        # Run cleanup and is_allowed concurrently
        async def run_cleanup():
            return await limiter.cleanup(max_age_seconds=3600)

        async def run_is_allowed():
            return await limiter.is_allowed("test_key")

        # Both should complete without race conditions
        results = await asyncio.gather(
            run_cleanup(),
            run_is_allowed(),
            return_exceptions=True,
        )

        # No exceptions should occur
        for result in results:
            assert not isinstance(result, Exception)

    @pytest.mark.asyncio
    async def test_cleanup_combined_old_and_excess(self):
        """Test cleanup removes both old keys and evicts excess."""
        limiter = InMemoryRateLimitService(limit=100, window_seconds=60, max_keys=2)

        now = time.time()
        # Old keys (should be removed by age check)
        limiter._requests["old1"] = [now - 7200]  # 2 hours ago
        limiter._requests["old2"] = [now - 7300]  # 2+ hours ago

        # Recent keys (should be evicted by excess check)
        limiter._requests["recent1"] = [now - 100]
        limiter._requests["recent2"] = [now - 90]
        limiter._requests["recent3"] = [now - 80]

        # Cleanup with max_age=1 hour
        removed = await limiter.cleanup(max_age_seconds=3600)

        # Should remove 2 old keys + evict 1 excess = 3 total
        assert removed == 3
        assert len(limiter._requests) == 2

    @pytest.mark.asyncio
    async def test_clear_all_keys(self):
        """Test clear() method removes all keys."""
        limiter = InMemoryRateLimitService(limit=100, window_seconds=60)

        # Add some keys
        limiter._requests["key1"] = [1.0]
        limiter._requests["key2"] = [2.0]
        limiter._requests["key3"] = [3.0]

        # Clear all
        limiter.clear()

        assert len(limiter._requests) == 0

    @pytest.mark.asyncio
    async def test_clear_specific_key(self):
        """Test clear() method removes specific key."""
        limiter = InMemoryRateLimitService(limit=100, window_seconds=60)

        # Add some keys
        limiter._requests["key1"] = [1.0]
        limiter._requests["key2"] = [2.0]
        limiter._requests["key3"] = [3.0]

        # Clear specific key
        limiter.clear("key2")

        assert len(limiter._requests) == 2
        assert "key1" in limiter._requests
        assert "key2" not in limiter._requests
        assert "key3" in limiter._requests

    @pytest.mark.asyncio
    async def test_clear_nonexistent_key(self):
        """Test clear() method handles nonexistent key."""
        limiter = InMemoryRateLimitService(limit=100, window_seconds=60)

        limiter._requests["key1"] = [1.0]

        # Clear nonexistent key - should not raise
        limiter.clear("nonexistent")

        assert len(limiter._requests) == 1
        assert "key1" in limiter._requests

    @pytest.mark.asyncio
    async def test_cleanup_respects_max_keys_threshold(self):
        """Test that cleanup only evicts when exceeding max_keys."""
        limiter = InMemoryRateLimitService(limit=100, window_seconds=60, max_keys=10)

        # Add 5 keys (below max_keys)
        now = time.time()
        for i in range(5):
            limiter._requests[f"key{i}"] = [now - i * 10]

        # Cleanup should not evict (below threshold)
        removed = await limiter.cleanup(max_age_seconds=3600)

        assert removed == 0
        assert len(limiter._requests) == 5

    @pytest.mark.asyncio
    async def test_cleanup_memory_leak_prevention(self):
        """Test that cleanup effectively prevents memory leaks."""
        # Create limiter with reasonable limits
        limiter = InMemoryRateLimitService(limit=100, window_seconds=60, max_keys=1000)

        # Simulate many keys over time
        now = time.time()
        for i in range(1500):
            # Some old, some new
            age = 7200 if i % 2 == 0 else 100  # Half are 2 hours old
            limiter._requests[f"key_{i}"] = [now - age]

        # After cleanup, should have at most max_keys
        removed = await limiter.cleanup(max_age_seconds=3600)

        # Should remove at least 750 old keys
        assert removed >= 750
        assert len(limiter._requests) <= 1000
