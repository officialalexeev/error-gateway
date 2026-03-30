"""Notification entity."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from .error_group import ErrorGroup


@dataclass
class Notification:
    """Notification entity for sending alerts."""

    error_group: ErrorGroup
    channel: str = ""
    recipient: str = ""
    subject: str = ""
    body: str = ""
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: datetime | None = None

    @property
    def is_sent(self) -> bool:
        """Check if notification was sent."""
        return self.sent_at is not None

    def mark_as_sent(self) -> None:
        """Mark notification as sent."""
        self.sent_at = datetime.now(timezone.utc)
