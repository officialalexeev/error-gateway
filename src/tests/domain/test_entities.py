"""
Tests for Domain Entities.

Test Isolation Principle:
- Entity tests are database-independent
- Only business logic is tested
"""

from uuid import UUID

import pytest
from app.domain.entities.error_event import ErrorEvent
from app.domain.entities.error_group import ErrorGroup
from app.domain.entities.notification import Notification


class TestErrorEvent:
    """Tests for ErrorEvent entity."""

    def test_create_valid_event(self):
        """Test creating valid event."""
        event = ErrorEvent(
            message="Test error",
            exception_type="ValueError",
        )

        assert event.message == "Test error"
        assert event.exception_type == "ValueError"
        assert isinstance(event.id, UUID)
        assert event.timestamp is not None

    def test_create_event_with_context(self):
        """Test creating event with context."""
        event = ErrorEvent(
            message="Test error",
            context={"user_id": 123, "email": "test@example.com"},
        )

        assert event.context["user_id"] == 123
        assert event.context["email"] == "test@example.com"

    def test_create_event_empty_message_raises(self):
        """Test that empty message raises."""
        with pytest.raises(ValueError, match="Error message cannot be empty"):
            ErrorEvent(message="")

    def test_event_auto_generates_id(self):
        """Test automatic ID generation."""
        event1 = ErrorEvent(message="Error 1")
        event2 = ErrorEvent(message="Error 2")

        assert event1.id != event2.id
        assert isinstance(event1.id, UUID)


class TestErrorGroup:
    """Tests for ErrorGroup entity."""

    def test_create_group(self):
        """Test creating group."""
        group = ErrorGroup(
            fingerprint="abc123",
            exception_type="ValueError",
            message="Test error",
        )

        assert group.fingerprint == "abc123"
        assert group.count == 1
        assert group.is_notified is False

    def test_add_event_to_group(self):
        """Test adding event to group."""
        group = ErrorGroup(
            fingerprint="abc123",
            exception_type="ValueError",
            message="Test error",
        )
        event = ErrorEvent(message="Test error")

        group.add_event(event)

        assert group.count == 2
        assert len(group.events) == 1
        assert group.events[0] == event

    def test_mark_group_as_notified(self):
        """Test marking group as notified."""
        group = ErrorGroup(
            fingerprint="abc123",
            exception_type="ValueError",
            message="Test error",
        )

        group.mark_as_notified()

        assert group.is_notified is True

    def test_add_event_limits_events_list(self):
        """Test that events list is limited to max_events (default 100)."""
        group = ErrorGroup(
            fingerprint="abc123",
            exception_type="ValueError",
            message="Test error",
        )

        # Add 150 events
        for i in range(150):
            event = ErrorEvent(message=f"Error {i}")
            group.add_event(event)

        # count should track total events
        assert group.count == 151  # initial 1 + 150 added
        # events list should be limited to default 100
        assert len(group.events) == 100
        # Should keep the last 100 events (FIFO): indices 50-149
        assert group.events[0].message == "Error 50"
        assert group.events[-1].message == "Error 149"

    def test_add_event_custom_max_events(self):
        """Test custom max_events limit."""
        group = ErrorGroup(
            fingerprint="abc123",
            exception_type="ValueError",
            message="Test error",
        )

        # Add 50 events with custom limit of 20
        for i in range(50):
            event = ErrorEvent(message=f"Error {i}")
            group.add_event(event, max_events=20)

        assert group.count == 51  # initial 1 + 50 added
        assert len(group.events) == 20
        # Should keep the last 20 events (FIFO): indices 30-49
        assert group.events[0].message == "Error 30"
        assert group.events[-1].message == "Error 49"

    def test_add_event_preserves_count_after_trim(self):
        """Test that count is preserved even after trimming events."""
        group = ErrorGroup(
            fingerprint="abc123",
            exception_type="ValueError",
            message="Test error",
            count=5,  # Start with existing count
        )

        # Add 10 events with limit 5
        for i in range(10):
            event = ErrorEvent(message=f"Error {i}")
            group.add_event(event, max_events=5)

        # Count should be 5 (initial) + 10 (added) = 15
        assert group.count == 15
        # Events should be limited to 5
        assert len(group.events) == 5


class TestNotification:
    """Tests for Notification entity."""

    def test_create_notification(self):
        """Test creating notification."""
        group = ErrorGroup(
            fingerprint="abc123",
            exception_type="ValueError",
            message="Test error",
        )
        notification = Notification(
            channel="telegram",
            recipient="-1001234567",
            subject="Error",
            body="Test error",
            error_group=group,
        )

        assert notification.channel == "telegram"
        assert notification.is_sent is False

    def test_mark_notification_sent(self):
        """Test marking notification as sent."""
        group = ErrorGroup(
            fingerprint="abc123",
            exception_type="ValueError",
            message="Test error",
        )
        notification = Notification(
            channel="telegram",
            recipient="-1001234567",
            subject="Error",
            body="Test error",
            error_group=group,
        )

        notification.mark_as_sent()

        assert notification.is_sent is True
        assert notification.sent_at is not None
