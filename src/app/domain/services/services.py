"""Fingerprint, masking, and rate limiting domain services."""

import asyncio
import hashlib
import re
import time
from collections import defaultdict
from typing import Any, Protocol


class FingerprintService:
    """Service for generating fingerprints to group errors."""

    def generate(self, exception_type: str, message: str, stack_trace: str | None = None) -> str:
        """Generate unique SHA256 hash for error group."""
        normalized_message = self._normalize_message(message)
        normalized_stack = self._normalize_stack_trace(stack_trace or "")

        raw_string = f"{exception_type}:{normalized_message}:{normalized_stack}"
        return hashlib.sha256(raw_string.encode()).hexdigest()

    def _normalize_message(self, message: str) -> str:
        """Normalize message by removing variable values."""
        normalized = message
        normalized = re.sub(r"\b\d+\b", "<NUM>", normalized)
        normalized = re.sub(r"[A-Za-z]:\\[^\s'\"]+", "<PATH>", normalized)
        normalized = re.sub(r"/[^\s'\"]+", "<PATH>", normalized)
        normalized = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "<UUID>",
            normalized,
            flags=re.IGNORECASE,
        )
        return normalized

    def _normalize_stack_trace(self, stack_trace: str) -> str:
        """Normalize stack trace by removing line numbers and paths."""
        normalized = stack_trace
        normalized = re.sub(r"line \d+", "line <N>", normalized)
        normalized = re.sub(r":\d+", ":<N>", normalized)
        normalized = re.sub(r"[A-Za-z]:\\[^\s'\"]+", "<PATH>", normalized)
        normalized = re.sub(r"/[^\s'\"]+", "<PATH>", normalized)
        return normalized


class MaskingService:
    """Service for masking sensitive data in error context."""

    SENSITIVE_KEYS = {
        "token",
        "tokens",
        "password",
        "passwd",
        "secret",
        "api_key",
        "apikey",
        "api_secret",
        "access_token",
        "refresh_token",
        "auth_token",
        "bearer_token",
        "private_key",
        "secret_key",
        "client_secret",
    }

    # Email: standard RFC 5322 (simplified)
    EMAIL_PATTERN = re.compile(r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")

    # Phone: strict E.164 + formats with separators
    # Avoids false positives for user IDs, order numbers, etc.
    # - E.164: +12345678901 (10-15 digits after +)
    # - With separators: +1 (234) 567-8901, +1-234-567-8901
    # - Without +: (123) 456-7890, 123-456-7890 (parentheses or separators required)
    PHONE_PATTERN = re.compile(
        r"(?:"
        r"\+[1-9]\d{9,14}|"  # E.164 (10-15 digits after +)
        r"\+\d[\d\s\-()]{8,14}|"  # With separators after +
        r"(?:\(\d+\)\s*[\d\s\-]{6,14}|[\d]{2,}[\s\-][\d\s\-]{5,14})"  # Without + (parentheses or separator)
        r")"
    )

    # Credit cards: only known payment system prefixes
    # Avoids masking user_id, order_id and other numeric identifiers
    # - Visa: 4xxx (13-16 digits)
    # - Mastercard: 51-55xx (16 digits)
    # - American Express: 34/37xx (15 digits)
    # - Discover: 6011/65xx (16 digits)
    CREDIT_CARD_PATTERN = re.compile(
        r"\b(?:"
        r"4\d{12}(?:\d{3})?|"  # Visa (13-16)
        r"5[1-5]\d{14}|"  # Mastercard (16)
        r"3[47]\d{13}|"  # American Express (15)
        r"6(?:011|5\d{2})\d{12}"  # Discover (16)
        r")\b"
    )

    # Matches key=value / key:value patterns in plain strings (stack traces, messages).
    # Sorted longest-first so "access_token" matches before "token".
    _SENSITIVE_KV_PATTERN = re.compile(
        r"(?i)((?:"
        + "|".join(
            re.escape(k)
            for k in sorted(
                SENSITIVE_KEYS,
                key=len,
                reverse=True,
            )
        )
        + r")\s*[:=]\s*)\S+",
    )

    def __init__(
        self,
        mask_email: bool = True,
        mask_phone: bool = True,
        mask_credit_card: bool = True,
        mask_tokens: bool = True,
    ):
        """Initialize masking service with configuration."""
        self.mask_email = mask_email
        self.mask_phone = mask_phone
        self.mask_credit_card = mask_credit_card
        self.mask_tokens = mask_tokens

    def mask(self, data: dict[str, Any]) -> dict[str, Any]:
        """Mask sensitive data in dictionary."""
        return self._mask_dict(data)

    def mask_string(self, value: str) -> str:
        """Mask sensitive data in a plain string (message, stack trace, etc.)."""
        return self._mask_string(value)

    def _mask_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Mask dictionary with sensitive key detection."""
        result: dict[str, Any] = {}
        for key, value in data.items():
            if self._is_sensitive_key(key):
                result[key] = "***REDACTED***"
            elif isinstance(value, dict):
                result[key] = self._mask_dict(value)
            elif isinstance(value, list):
                result[key] = self._mask_list(value)
            elif isinstance(value, str):
                result[key] = self._mask_string(value)
            else:
                result[key] = value
        return result

    def _mask_list(self, items: list) -> list:
        """Mask list of items."""
        return [
            (
                self._mask_dict(item)
                if isinstance(item, dict)
                else self._mask_string(item) if isinstance(item, str) else item
            )
            for item in items
        ]

    def _mask_string(self, value: str) -> str:
        """Mask sensitive data patterns in a plain string."""
        if self.mask_tokens:
            value = self._SENSITIVE_KV_PATTERN.sub(r"\1***REDACTED***", value)
        if self.mask_email:
            value = self.EMAIL_PATTERN.sub(self._mask_email_match, value)
        if self.mask_phone:
            value = self.PHONE_PATTERN.sub(self._mask_phone_match, value)
        if self.mask_credit_card:
            value = self.CREDIT_CARD_PATTERN.sub(self._mask_credit_card_match, value)
        return value

    def _mask_email_match(self, match: re.Match) -> str:
        """Mask email preserving domain."""
        local, domain = match.groups()
        masked_local = local[0] + "***" + local[-1] if len(local) > 1 else "***"
        return f"{masked_local}@{domain}"

    def _mask_phone_match(self, match: re.Match) -> str:
        """Mask phone number preserving last 4 digits."""
        phone = match.group(0)
        digits = re.sub(r"\D", "", phone)
        if len(digits) >= 4:
            masked_digits = "*" * (len(digits) - 4) + digits[-4:]
            return phone[: phone.find(digits[0])] + masked_digits
        return "***" + phone[-4:]

    def _mask_credit_card_match(self, match: re.Match) -> str:
        """Mask credit card preserving last 4 digits."""
        card = match.group(0)
        return "****" + card[-4:]

    def _is_sensitive_key(self, key: str) -> bool:
        """Check if key name indicates sensitive data."""
        if not self.mask_tokens:
            return False
        key_lower = key.lower()
        return any(sensitive in key_lower for sensitive in self.SENSITIVE_KEYS)


class RateLimitService(Protocol):
    """Protocol for rate limiting services."""

    limit: int

    async def is_allowed(
        self,
        key: str,
        limit: int | None = None,
        window_seconds: int | None = None,
    ) -> bool:
        """Check if request is allowed."""
        ...

    async def get_remaining(
        self,
        key: str,
        limit: int | None = None,
        window_seconds: int | None = None,
    ) -> int:
        """Get remaining requests count."""
        ...


class InMemoryRateLimitService(RateLimitService):
    """In-memory rate limiting service using sliding window algorithm.

    Thread-safe: uses asyncio.Lock to ensure atomic read-modify-write operations
    and prevent race conditions between concurrent coroutines.
    """

    def __init__(self, limit: int = 100, window_seconds: int = 60, max_keys: int = 10000):
        """Initialize in-memory rate limiter."""
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._requests: defaultdict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(
        self,
        key: str,
        limit: int | None = None,
        window_seconds: int | None = None,
    ) -> bool:
        """
        Check if request is allowed.

        Thread-safe: uses asyncio.Lock to prevent race conditions between
        concurrent coroutines accessing the same or different keys.
        """
        effective_limit = limit if limit is not None else self.limit
        effective_window = window_seconds if window_seconds is not None else self.window_seconds

        # Use lock to ensure atomic read-modify-write operation
        async with self._lock:
            now = time.time()
            window_start = now - effective_window

            # Build filtered list
            timestamps = [ts for ts in self._requests[key] if ts > window_start]

            if len(timestamps) >= effective_limit:
                # Store the trimmed list (or evict empty key) to bound memory
                if timestamps:
                    self._requests[key] = timestamps
                elif key in self._requests:
                    del self._requests[key]
                return False

            timestamps.append(now)
            self._requests[key] = timestamps
            return True

    async def get_remaining(
        self,
        key: str,
        limit: int | None = None,
        window_seconds: int | None = None,
    ) -> int:
        """
        Get remaining requests count.

        Thread-safe: uses asyncio.Lock to prevent race conditions.
        """
        effective_limit = limit if limit is not None else self.limit
        effective_window = window_seconds if window_seconds is not None else self.window_seconds

        async with self._lock:
            now = time.time()
            window_start = now - effective_window

            current_count = sum(1 for ts in self._requests[key] if ts > window_start)

            return max(0, effective_limit - current_count)

    def clear(self, key: str | None = None) -> None:
        """Clear rate limit data."""
        if key is None:
            self._requests.clear()
        elif key in self._requests:
            del self._requests[key]

    async def cleanup(self, max_age_seconds: int | None = None) -> int:
        """
        Clean up old keys to prevent memory leaks.

        Thread-safe: uses asyncio.Lock to prevent race conditions.

        Optimization: Pre-compute minimum timestamps to avoid redundant min() calls
        during heapq.nsmallest() key function evaluation.
        Complexity: O(n) for computation + O(n log n) for sorting,
        instead of O(n log k * m) where m is the number of key function calls.
        """
        if max_age_seconds is None:
            max_age_seconds = max(3600, self.window_seconds * 10)

        async with self._lock:
            now = time.time()
            cutoff = now - max_age_seconds
            removed = 0

            # Step 1: Remove keys where all timestamps are older than cutoff
            keys_to_remove = [
                key
                for key, timestamps in self._requests.items()
                if not any(ts > cutoff for ts in timestamps)
            ]

            for key in keys_to_remove:
                del self._requests[key]
                removed += 1

            # Step 2: If key limit exceeded, remove oldest keys
            excess = len(self._requests) - self.max_keys
            if excess > 0:
                # Optimization: pre-compute min-timestamp for each key
                # Complexity: O(n) for computation + O(n log n) for sorting
                # Instead of: O(n log k * m) where m is the number of key function calls
                keys_with_min = [
                    (min(timestamps) if timestamps else 0, key)
                    for key, timestamps in self._requests.items()
                ]
                keys_with_min.sort()  # Sort by min-timestamp (first element of tuple)

                # Remove excess oldest keys
                for _, key in keys_with_min[:excess]:
                    del self._requests[key]
                    removed += 1

            return removed
