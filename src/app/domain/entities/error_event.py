"""Error event entity."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


@dataclass
class ErrorEvent:
    """Error event entity representing a single error occurrence."""

    message: str
    exception_type: str = "Error"
    stack_trace: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    fingerprint: str = ""

    def __post_init__(self):
        """Validate entity fields."""
        if not self.message:
            raise ValueError("Error message cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        """Convert entity to dictionary."""
        return {
            "id": str(self.id),
            "message": self.message,
            "exception_type": self.exception_type,
            "stack_trace": self.stack_trace,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ErrorEvent":
        """Create entity from dictionary."""
        return cls(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            message=data["message"],
            exception_type=data.get("exception_type", "Error"),
            stack_trace=data.get("stack_trace"),
            context=data.get("context", {}),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if isinstance(data["timestamp"], str)
                else data["timestamp"]
            ),
            fingerprint=data.get("fingerprint", ""),
        )
