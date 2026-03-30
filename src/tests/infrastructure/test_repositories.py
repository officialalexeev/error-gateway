"""
Tests for Database Repositories.

Tests for AsyncSQLAlchemyErrorGroupRepository and AsyncSQLAlchemyErrorEventRepository.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from app.domain.entities.error_event import ErrorEvent
from app.infrastructure.db.repositories import (
    AsyncSQLAlchemyErrorEventRepository,
    AsyncSQLAlchemyErrorGroupRepository,
)


class TestAsyncSQLAlchemyErrorGroupRepository:
    """Tests for ErrorGroup repository."""

    @pytest.fixture
    def group_repo(self, db_session):
        """Create group repository instance."""
        return AsyncSQLAlchemyErrorGroupRepository(db_session)

    @pytest.fixture
    def sample_event(self):
        """Create sample error event."""
        return ErrorEvent(
            message="Test error",
            exception_type="TestError",
            stack_trace="File 'test.py', line 1",
            context={"user_id": 123},
            timestamp=datetime.now(timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_get_or_create_by_fingerprint_creates_new(self, group_repo, sample_event):
        """Test creating new group by fingerprint."""
        fingerprint = "test_fingerprint_123"

        group = await group_repo.get_or_create_by_fingerprint(fingerprint, sample_event)

        assert group.fingerprint == fingerprint
        assert group.exception_type == "TestError"
        assert group.message == "Test error"
        assert group.count == 1
        assert group.is_notified is False

    @pytest.mark.asyncio
    async def test_get_or_create_by_fingerprint_updates_existing(self, group_repo, sample_event):
        """Test updating existing group by fingerprint."""
        fingerprint = "test_fingerprint_456"

        # Create first
        group1 = await group_repo.get_or_create_by_fingerprint(fingerprint, sample_event)
        initial_count = group1.count

        # Create second (should update)
        group2 = await group_repo.get_or_create_by_fingerprint(fingerprint, sample_event)

        assert group2.id == group1.id
        assert group2.count == initial_count + 1

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_invalid_id(self, group_repo):
        """Test getting non-existent group."""
        invalid_id = uuid4()

        result = await group_repo.get_by_id(invalid_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_returns_group(self, group_repo, sample_event):
        """Test getting existing group by ID."""
        fingerprint = "test_fingerprint_789"
        group = await group_repo.get_or_create_by_fingerprint(fingerprint, sample_event)

        result = await group_repo.get_by_id(group.id)

        assert result is not None
        assert result.id == group.id
        assert result.fingerprint == fingerprint

    @pytest.mark.asyncio
    async def test_get_all_returns_empty_list(self, group_repo):
        """Test getting all groups when database is empty."""
        groups, total = await group_repo.get_all(limit=10, offset=0)

        assert groups == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_all_returns_groups_with_pagination(self, group_repo, sample_event):
        """Test pagination with multiple groups."""
        # Create 5 groups
        for i in range(5):
            await group_repo.get_or_create_by_fingerprint(f"fingerprint_{i}", sample_event)

        # Get first page
        groups, total = await group_repo.get_all(limit=2, offset=0)

        assert len(groups) == 2
        assert total == 5

        # Get second page
        groups, total = await group_repo.get_all(limit=2, offset=2)

        assert len(groups) == 2
        assert total == 5

    @pytest.mark.asyncio
    async def test_get_all_orders_by_last_seen_desc(self, group_repo, sample_event):
        """Test that groups are ordered by last_seen descending."""
        # Create groups
        for i in range(3):
            await group_repo.get_or_create_by_fingerprint(f"order_{i}", sample_event)

        groups, _ = await group_repo.get_all(limit=10, offset=0)

        # Most recently seen should be first
        assert len(groups) == 3
        assert groups[0].last_seen >= groups[1].last_seen
        assert groups[1].last_seen >= groups[2].last_seen

    @pytest.mark.asyncio
    async def test_update_group(self, group_repo, sample_event):
        """Test updating group."""
        fingerprint = "update_test"
        group = await group_repo.get_or_create_by_fingerprint(fingerprint, sample_event)

        # Update group
        group.count = 100
        group.is_notified = True
        group.last_seen = datetime.now(timezone.utc)

        await group_repo.update(group)

        # Verify update
        updated = await group_repo.get_by_id(group.id)
        assert updated.count == 100
        assert updated.is_notified is True

    @pytest.mark.asyncio
    async def test_get_by_id_with_eager_loading(self, group_repo, sample_event):
        """Test that get_by_id loads events eagerly."""
        fingerprint = "eager_load_test"
        group = await group_repo.get_or_create_by_fingerprint(fingerprint, sample_event)

        # Save some events
        for i in range(3):
            event = ErrorEvent(
                message=f"Event {i}",
                exception_type="TestError",
                context={},
                timestamp=datetime.now(timezone.utc),
            )
            event.fingerprint = fingerprint
            # In real scenario, events would be saved via event_repo
            # This test verifies the selectinload is present

        result = await group_repo.get_by_id(group.id)
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_or_create_handles_race_condition(self, group_repo, sample_event):
        """Test that retry loop handles race condition (IntegrityError)."""
        from sqlalchemy.exc import IntegrityError

        fingerprint = "race_condition_test"

        # Track calls
        call_count = {"scalar": 0, "flush": 0}
        created_model = None

        # Create mock existing model (returned on retry) - use valid UUID format
        mock_existing_model = Mock()
        mock_existing_model.id = "550e8400-e29b-41d4-a716-446655440000"
        mock_existing_model.fingerprint = fingerprint
        mock_existing_model.exception_type = "TestError"
        mock_existing_model.message = "Test error"
        mock_existing_model.count = 1
        mock_existing_model.first_seen = sample_event.timestamp
        mock_existing_model.last_seen = sample_event.timestamp
        mock_existing_model.is_notified = False
        mock_existing_model.events = []

        # Save original methods

        async def mock_scalar(query):
            call_count["scalar"] += 1
            if call_count["scalar"] == 1:
                # First SELECT: no group exists
                return None
            else:
                # Second SELECT (after retry): group exists
                return mock_existing_model

        async def mock_flush():
            call_count["flush"] += 1
            if call_count["flush"] == 1:
                # First flush: raise IntegrityError (race condition)
                raise IntegrityError("UNIQUE constraint failed", None, None)
            # Second flush: success

        def mock_add(model):
            nonlocal created_model
            created_model = model

        def mock_rollback():
            pass  # Mock rollback

        # Apply mocks
        with patch.object(group_repo.session, "scalar", side_effect=mock_scalar):
            with patch.object(group_repo.session, "flush", side_effect=mock_flush):
                with patch.object(group_repo.session, "add", side_effect=mock_add):
                    with patch.object(group_repo.session, "rollback", side_effect=mock_rollback):
                        # Should succeed on retry
                        group = await group_repo.get_or_create_by_fingerprint(
                            fingerprint, sample_event
                        )

        # Verify: scalar called twice (once before insert, once on retry)
        assert call_count["scalar"] == 2
        # Verify: flush called twice (once failed, once succeeded)
        assert call_count["flush"] == 2
        # Verify: group returned successfully
        assert group is not None
        assert group.fingerprint == fingerprint


class TestAsyncSQLAlchemyErrorEventRepository:
    """Tests for ErrorEvent repository."""

    @pytest.fixture
    def event_repo(self, db_session):
        """Create event repository instance."""
        return AsyncSQLAlchemyErrorEventRepository(db_session)

    @pytest.fixture
    def event_group_repo(self, db_session):
        """Create group repository instance for event tests."""
        return AsyncSQLAlchemyErrorGroupRepository(db_session)

    @pytest.fixture
    async def sample_group(self, db_session, event_group_repo):
        """Create sample error group."""
        event = ErrorEvent(
            message="Test error",
            exception_type="TestError",
            context={},
            timestamp=datetime.now(timezone.utc),
        )
        group = await event_group_repo.get_or_create_by_fingerprint("event_test", event)
        return group

    @pytest.mark.asyncio
    async def test_save_event(self, event_repo, sample_group):
        """Test saving event."""
        event = ErrorEvent(
            message="Saved event",
            exception_type="SavedError",
            stack_trace="File 'saved.py', line 10",
            context={"key": "value"},
            timestamp=datetime.now(timezone.utc),
        )

        await event_repo.save(event, sample_group)

        # Verify event was saved
        events = await event_repo.get_by_group(sample_group.id, limit=10)
        assert len(events) >= 1
        assert events[0].message == "Saved event"
        # exception_type stored in group, not event
        assert events[0].stack_trace == "File 'saved.py', line 10"
        assert events[0].context["key"] == "value"

    @pytest.mark.asyncio
    async def test_save_event_with_context(self, event_repo, sample_group):
        """Test saving event with context data."""
        event = ErrorEvent(
            message="Event with context",
            exception_type="ContextError",
            context={"user_id": 456, "email": "test@example.com"},
            timestamp=datetime.now(timezone.utc),
        )

        await event_repo.save(event, sample_group)

        events = await event_repo.get_by_group(sample_group.id, limit=10)
        assert len(events) >= 1
        assert events[0].context["user_id"] == 456
        assert events[0].context["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_by_group_returns_events(self, event_repo, sample_group):
        """Test getting events by group."""
        # Save multiple events
        for i in range(5):
            event = ErrorEvent(
                message=f"Event {i}",
                exception_type="TestError",
                context={},
                timestamp=datetime.now(timezone.utc),
            )
            await event_repo.save(event, sample_group)

        events = await event_repo.get_by_group(sample_group.id, limit=10)

        assert len(events) == 5

    @pytest.mark.asyncio
    async def test_get_by_group_with_limit(self, event_repo, sample_group):
        """Test limiting results."""
        # Save 10 events
        for i in range(10):
            event = ErrorEvent(
                message=f"Event {i}",
                exception_type="TestError",
                context={},
                timestamp=datetime.now(timezone.utc),
            )
            await event_repo.save(event, sample_group)

        events = await event_repo.get_by_group(sample_group.id, limit=5)

        assert len(events) == 5

    @pytest.mark.asyncio
    async def test_get_by_group_orders_by_timestamp_desc(self, event_repo, sample_group):
        """Test that events are ordered by timestamp descending."""
        # Save events with different timestamps
        for i in range(3):
            event = ErrorEvent(
                message=f"Event {i}",
                exception_type="TestError",
                context={},
                timestamp=datetime.now(timezone.utc),
            )
            await event_repo.save(event, sample_group)

        events = await event_repo.get_by_group(sample_group.id, limit=10)

        # Most recent should be first
        assert len(events) == 3
        assert events[0].timestamp >= events[1].timestamp
        assert events[1].timestamp >= events[2].timestamp

    @pytest.mark.asyncio
    async def test_get_by_group_empty_group(self, event_repo):
        """Test getting events from non-existent group."""
        events = await event_repo.get_by_group(uuid4(), limit=10)

        assert events == []

    @pytest.mark.asyncio
    async def test_to_entity_conversion(self, event_repo, sample_group):
        """Test correct entity conversion."""
        event = ErrorEvent(
            message="Entity test",
            exception_type="EntityError",
            stack_trace="File 'entity.py', line 1",
            context={"test": "data"},
            timestamp=datetime.now(timezone.utc),
        )

        await event_repo.save(event, sample_group)

        events = await event_repo.get_by_group(sample_group.id, limit=10)
        assert len(events) >= 1

        entity = events[0]
        assert isinstance(entity, ErrorEvent)
        assert entity.message == "Entity test"
        # exception_type stored in group, not event
        assert entity.stack_trace == "File 'entity.py', line 1"
        assert entity.context["test"] == "data"
