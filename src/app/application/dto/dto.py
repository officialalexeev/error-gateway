"""Error event DTO for data transfer between layers."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


@dataclass
class ErrorEventDTO:
    """
    Data Transfer Object for error events.

    Used to transfer error data between API and Application layers.
    Contains all information needed to process an error event.
    """

    message: str
    exception_type: str = "Error"
    stack_trace: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    environment: str | None = None
    release_version: str | None = None
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Validate and normalize DTO fields."""
        if not self.message:
            raise ValueError("Message is required")
        if not self.exception_type:
            self.exception_type = "Error"
        if self.context is None:
            self.context = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert DTO to dictionary."""
        return {
            "id": str(self.id),
            "message": self.message,
            "exception_type": self.exception_type,
            "stack_trace": self.stack_trace,
            "context": self.context,
            "environment": self.environment,
            "release_version": self.release_version,
            "timestamp": self.timestamp.isoformat(),
        }
