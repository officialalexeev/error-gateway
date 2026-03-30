"""Async SQLAlchemy repository implementations."""

from uuid import UUID

from app.core.logger import log
from app.domain.entities.error_event import ErrorEvent
from app.domain.entities.error_group import ErrorGroup
from app.domain.repositories.interfaces import ErrorEventRepository, ErrorGroupRepository
from app.infrastructure.db.models import ErrorEventModel, ErrorGroupModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class AsyncSQLAlchemyErrorGroupRepository(ErrorGroupRepository):
    """Async SQLAlchemy repository for error groups."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def get_or_create_by_fingerprint(self, fingerprint: str, event: ErrorEvent) -> ErrorGroup:
        """
        Get existing group or create new one by fingerprint with retry on race condition.

        Uses optimistic locking with retry loop to handle concurrent inserts.
        Retries up to 3 times on IntegrityError (UNIQUE constraint violation).
        Works with both PostgreSQL and SQLite.

        Args:
            fingerprint: SHA256 fingerprint of the error
            event: Error event to process

        Returns:
            ErrorGroup entity (existing or newly created)

        Raises:
            RuntimeError: If failed to get/create group after 3 retries
        """
        for attempt in range(3):
            # Attempt 1: Try to find existing group
            query = select(ErrorGroupModel).where(ErrorGroupModel.fingerprint == fingerprint)
            model = await self.session.scalar(query)

            if model is not None:
                # Group exists - update counter
                model.count += 1
                model.last_seen = event.timestamp
                await self.session.flush()
                return self._to_entity(model)

            # Group not found - create new one
            try:
                model = ErrorGroupModel(
                    fingerprint=fingerprint,
                    exception_type=event.exception_type,
                    message=event.message,
                    first_seen=event.timestamp,
                    last_seen=event.timestamp,
                    count=1,
                )
                self.session.add(model)
                await self.session.flush()  # This will raise IntegrityError if constraint violated
                return self._to_entity(model)
            except IntegrityError:
                await self.session.rollback()
                if attempt == 2:  # Last attempt
                    log.error(
                        f"Failed to get/create error group after 3 retries (fingerprint={fingerprint})"
                    )
                    raise
                # Retry - another transaction created the group
                log.debug(
                    f"Race condition detected, retrying (attempt={attempt + 1}, fingerprint={fingerprint})"
                )
                continue

        raise RuntimeError("Failed to get/create error group after 3 retries")

    async def get_by_id(self, group_id: UUID) -> ErrorGroup | None:
        """
        Get group by ID with eager loading of events.

        Note: Uses selectinload to load events in single query.
        This is intentional — events are needed for group details.
        """
        query = (
            select(ErrorGroupModel)
            .options(selectinload(ErrorGroupModel.events))  # Load events for details
            .where(ErrorGroupModel.id == str(group_id))
        )
        model = await self.session.scalar(query)
        return self._to_entity(model) if model else None

    async def get_all(self, limit: int = 50, offset: int = 0) -> tuple[list[ErrorGroup], int]:
        """
        Get all groups with pagination.

        Note: Does NOT load events to prevent memory exhaustion.
        Events are loaded only in get_by_id() when needed for details.
        """
        count_query = select(func.count(ErrorGroupModel.id))
        total = await self.session.scalar(count_query) or 0

        # Do NOT use selectinload here — events are not needed for group list
        # This prevents memory exhaustion when listing many groups
        query = (
            select(ErrorGroupModel)
            .order_by(ErrorGroupModel.last_seen.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(query)
        groups = [self._to_entity(m) for m in result]

        return groups, total

    async def update(self, group: ErrorGroup) -> None:
        """Update group."""
        query = select(ErrorGroupModel).where(ErrorGroupModel.id == str(group.id))
        model = await self.session.scalar(query)
        if model:
            model.is_notified = group.is_notified
            model.last_notified_at = group.last_notified_at
            model.count = group.count
            model.last_seen = group.last_seen
            await self.session.flush()

    def _to_entity(self, model: ErrorGroupModel) -> ErrorGroup:
        """Convert model to entity."""
        return ErrorGroup(
            id=UUID(model.id),
            fingerprint=model.fingerprint,
            exception_type=model.exception_type,
            message=model.message,
            count=model.count,
            first_seen=model.first_seen,
            last_seen=model.last_seen,
            is_notified=model.is_notified,
            last_notified_at=model.last_notified_at,
        )


class AsyncSQLAlchemyErrorEventRepository(ErrorEventRepository):
    """Async SQLAlchemy repository for error events."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def save(self, event: ErrorEvent, group: ErrorGroup) -> None:
        """Save event."""
        model = ErrorEventModel(
            group_id=str(group.id),
            message=event.message,
            stack_trace=event.stack_trace,
            context=event.context,
            timestamp=event.timestamp,
        )
        self.session.add(model)
        await self.session.flush()

    async def get_by_group(self, group_id: UUID, limit: int = 100) -> list[ErrorEvent]:
        """Get events by group."""
        query = (
            select(ErrorEventModel)
            .where(ErrorEventModel.group_id == str(group_id))
            .order_by(ErrorEventModel.timestamp.desc())
            .limit(limit)
        )
        result = await self.session.scalars(query)
        return [self._to_entity(m) for m in result]

    def _to_entity(self, model: ErrorEventModel) -> ErrorEvent:
        """Convert model to entity."""
        return ErrorEvent(
            id=UUID(model.id),
            message=model.message,
            stack_trace=model.stack_trace,
            context=model.context or {},
            timestamp=model.timestamp,
        )
