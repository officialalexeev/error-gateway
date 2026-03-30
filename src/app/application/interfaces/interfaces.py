"""Notification and logging service protocols for dependency inversion."""

from typing import Protocol, runtime_checkable

from app.domain.entities.error_group import ErrorGroup
from app.domain.entities.notification import Notification


@runtime_checkable
class NotificationChannel(Protocol):
    """Protocol for notification channels."""

    @property
    def is_available(self) -> bool:
        """Check if channel is configured and available."""
        ...

    async def send(self, notification: Notification) -> bool:
        """
        Send notification through this channel.

        Returns True if sent successfully, False otherwise.
        """
        ...

    async def close(self) -> None:
        """Close channel resources (HTTP clients, connections, etc.)."""
        ...


@runtime_checkable
class LokiService(Protocol):
    """Protocol for Loki log shipping service."""

    async def send_error(self, group: ErrorGroup) -> bool:
        """Ship error group data to Loki. Returns True on success, False on failure."""
        ...

    async def close(self) -> None:
        """Close underlying HTTP connections."""
        ...


@runtime_checkable
class NotificationService(Protocol):
    """Protocol for notification service."""

    def should_notify(self, group, throttle_minutes: int = 5) -> bool:
        """Check if notification should be sent based on throttling."""
        ...

    async def notify(self, group) -> None:
        """Send notification through all available channels."""
        ...

    async def close(self) -> None:
        """Close all notification channels."""
        ...
