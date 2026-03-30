"""Repository protocols for dependency inversion."""

from typing import Protocol, runtime_checkable
from uuid import UUID

from app.domain.entities.error_event import ErrorEvent
from app.domain.entities.error_group import ErrorGroup


@runtime_checkable
class ErrorGroupRepository(Protocol):
    """Protocol for error group repository."""

    async def get_or_create_by_fingerprint(self, fingerprint: str, event: ErrorEvent) -> ErrorGroup:
        """
        Get existing group or create new one by fingerprint.

        Args:
            fingerprint: SHA256 fingerprint for grouping
            event: Error event that triggered group creation

        Returns:
            ErrorGroup entity (existing or newly created)
        """
        ...

    async def get_by_id(self, group_id: UUID) -> ErrorGroup | None:
        """
        Get group by ID.

        Args:
            group_id: Unique identifier of the group

        Returns:
            ErrorGroup entity or None if not found
        """
        ...

    async def get_all(self, limit: int = 50, offset: int = 0) -> tuple[list[ErrorGroup], int]:
        """
        Get all groups with pagination.

        Args:
            limit: Maximum number of groups to return
            offset: Number of groups to skip

        Returns:
            Tuple of (groups list, total count)
        """
        ...

    async def update(self, group: ErrorGroup) -> None:
        """
        Update existing group.

        Args:
            group: ErrorGroup entity to update
        """
        ...


@runtime_checkable
class ErrorEventRepository(Protocol):
    """Protocol for error event repository."""

    async def save(self, event: ErrorEvent, group: ErrorGroup) -> None:
        """
        Save error event to database.

        Args:
            event: ErrorEvent entity to save
            group: Parent ErrorGroup entity
        """
        ...

    async def get_by_group(self, group_id: UUID, limit: int = 100) -> list[ErrorEvent]:
        """
        Get events by group ID.

        Args:
            group_id: Unique identifier of the group
            limit: Maximum number of events to return

        Returns:
            List of ErrorEvent entities
        """
        ...
