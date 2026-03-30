"""Error group domain entity for grouping similar errors."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.domain.entities.error_event import ErrorEvent


@dataclass
class ErrorGroup:
    """
    Domain entity representing a group of similar errors.

    Errors are grouped by fingerprint (SHA256 hash of normalized error data).
    This allows tracking error frequency and sending consolidated notifications.
    """

    fingerprint: str
    exception_type: str = "Error"
    message: str = ""
    count: int = 1
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_notified: bool = False
    last_notified_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)
    events: list[ErrorEvent] = field(default_factory=list)

    def __post_init__(self):
        """Validate entity fields."""
        if not self.fingerprint:
            raise ValueError("Fingerprint is required")
        if not self.exception_type:
            self.exception_type = "Error"

    def add_event(self, event: ErrorEvent, max_events: int = 100) -> None:
        """
        Add event to group and update statistics.

        Keeps only the last N events in memory to prevent memory leaks.
        The `count` field tracks total events (not limited).

        Args:
            event: Error event to add to the group
            max_events: Maximum events to keep in memory (default: 100)
        """
        self.events.append(event)
        self.count += 1
        self.last_seen = datetime.now(timezone.utc)

        # Trim old events if limit exceeded (FIFO)
        if len(self.events) > max_events:
            self.events = self.events[-max_events:]

    def mark_as_notified(self) -> None:
        """Mark group as notified and set timestamp."""
        self.is_notified = True
        self.last_notified_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Convert entity to dictionary."""
        return {
            "id": str(self.id),
            "fingerprint": self.fingerprint,
            "exception_type": self.exception_type,
            "message": self.message,
            "count": self.count,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "is_notified": self.is_notified,
            "last_notified_at": (
                self.last_notified_at.isoformat() if self.last_notified_at else None
            ),
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ErrorGroup":
        """Create entity from dictionary."""
        return cls(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            fingerprint=data["fingerprint"],
            exception_type=data.get("exception_type", "Error"),
            message=data.get("message", ""),
            count=data.get("count", 1),
            first_seen=(
                datetime.fromisoformat(data["first_seen"])
                if isinstance(data["first_seen"], str)
                else data["first_seen"]
            ),
            last_seen=(
                datetime.fromisoformat(data["last_seen"])
                if isinstance(data["last_seen"], str)
                else data["last_seen"]
            ),
            is_notified=data.get("is_notified", False),
            last_notified_at=(
                datetime.fromisoformat(data["last_notified_at"])
                if isinstance(data["last_notified_at"], str)
                else data.get("last_notified_at")
            ),
            events=[ErrorEvent.from_dict(e) for e in data.get("events", [])],
        )
