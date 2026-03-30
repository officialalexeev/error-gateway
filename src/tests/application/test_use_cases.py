"""
Tests for Application Use Cases.

Test Isolation Principle:
- Mock repositories
- Only Use Case logic is tested

Async: Async tests
"""

from unittest.mock import AsyncMock, Mock

import pytest
from app.application.dto.dto import ErrorEventDTO
from app.application.use_cases.use_cases import ProcessErrorUseCase
from app.domain.entities.error_group import ErrorGroup


class TestProcessErrorUseCase:
    """Tests for error processing Use Case."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self, fingerprint_service, masking_service, mock_notification_service
    ):
        """Test successful error processing."""
        # Mock repositories
        event_repo = Mock()
        event_repo.save = AsyncMock()

        group = ErrorGroup(
            fingerprint="abc123",
            exception_type="ConnectionError",
            message="Test error",
        )

        group_repo = Mock()
        group_repo.get_or_create_by_fingerprint = AsyncMock(return_value=group)
        group_repo.update = AsyncMock()

        # Create Use Case
        use_case = ProcessErrorUseCase(
            event_repo=event_repo,
            group_repo=group_repo,
            notification_service=mock_notification_service,
            fingerprint_service=fingerprint_service,
            masking_service=masking_service,
        )

        # DTO
        dto = ErrorEventDTO(
            message="Test error",
            exception_type="ConnectionError",
            context={"user_id": 123},
        )

        # Execute
        result = await use_case.execute(dto)

        # Assertions
        assert isinstance(result, ErrorGroup)
        assert result.fingerprint == "abc123"
        event_repo.save.assert_called_once()
        group_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_masks_sensitive_data(
        self, fingerprint_service, masking_service, mock_notification_service
    ):
        """Test masking of sensitive data."""
        event_repo = Mock()
        event_repo.save = AsyncMock()

        group = ErrorGroup(
            fingerprint="abc123",
            exception_type="ConnectionError",
            message="Test error",
        )

        group_repo = Mock()
        group_repo.get_or_create_by_fingerprint = AsyncMock(return_value=group)
        group_repo.update = AsyncMock()

        use_case = ProcessErrorUseCase(
            event_repo=event_repo,
            group_repo=group_repo,
            notification_service=mock_notification_service,
            fingerprint_service=fingerprint_service,
            masking_service=masking_service,
        )

        dto = ErrorEventDTO(
            message="Test error",
            exception_type="ConnectionError",
            context={"token": "secret123", "email": "test@example.com"},
        )

        await use_case.execute(dto)

        # Assert that save was called with masked data
        assert event_repo.save.called
        call_args = event_repo.save.call_args
        event = call_args[0][0]
        assert event.context["token"] == "***REDACTED***"

    @pytest.mark.asyncio
    async def test_execute_no_notification_if_throttled(self, fingerprint_service, masking_service):
        """Test no notification when throttled."""
        event_repo = Mock()
        event_repo.save = AsyncMock()

        group = ErrorGroup(
            fingerprint="abc123",
            exception_type="ConnectionError",
            message="Test error",
        )

        group_repo = Mock()
        group_repo.get_or_create_by_fingerprint = AsyncMock(return_value=group)
        group_repo.update = AsyncMock()

        notification_service = Mock()
        notification_service.should_notify = Mock(return_value=False)
        notification_service.notify = AsyncMock()

        use_case = ProcessErrorUseCase(
            event_repo=event_repo,
            group_repo=group_repo,
            notification_service=notification_service,
            fingerprint_service=fingerprint_service,
            masking_service=masking_service,
        )

        dto = ErrorEventDTO(message="Test error")
        await use_case.execute(dto)

        notification_service.notify.assert_not_called()
        group_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_masks_message_and_stack_trace(
        self, fingerprint_service, masking_service, mock_notification_service
    ):
        """Test that message and stack_trace are also masked."""
        event_repo = Mock()
        event_repo.save = AsyncMock()

        group = ErrorGroup(
            fingerprint="abc123",
            exception_type="ConnectionError",
            message="Test error",
        )

        group_repo = Mock()
        group_repo.get_or_create_by_fingerprint = AsyncMock(return_value=group)
        group_repo.update = AsyncMock()

        use_case = ProcessErrorUseCase(
            event_repo=event_repo,
            group_repo=group_repo,
            notification_service=mock_notification_service,
            fingerprint_service=fingerprint_service,
            masking_service=masking_service,
        )

        dto = ErrorEventDTO(
            message="Error for user test@example.com",
            exception_type="ValueError",
            stack_trace="Failed at token=supersecret in line 5",
        )

        await use_case.execute(dto)

        call_args = event_repo.save.call_args
        event = call_args[0][0]
        # Email in message should be masked
        assert "test@example.com" not in event.message
        # Stack trace should be stored (masked)
        assert event.stack_trace is not None
        assert "supersecret" not in event.stack_trace

    @pytest.mark.asyncio
    async def test_execute_with_loki_client(
        self, fingerprint_service, masking_service, mock_notification_service
    ):
        """Test that loki_client.send_error is called when configured."""
        event_repo = Mock()
        event_repo.save = AsyncMock()

        group = ErrorGroup(
            fingerprint="abc123",
            exception_type="ConnectionError",
            message="Test error",
        )

        group_repo = Mock()
        group_repo.get_or_create_by_fingerprint = AsyncMock(return_value=group)
        group_repo.update = AsyncMock()

        mock_loki = Mock()
        mock_loki.send_error = AsyncMock(return_value=True)

        use_case = ProcessErrorUseCase(
            event_repo=event_repo,
            group_repo=group_repo,
            notification_service=mock_notification_service,
            fingerprint_service=fingerprint_service,
            masking_service=masking_service,
            loki_client=mock_loki,
        )

        dto = ErrorEventDTO(message="Test error", exception_type="ConnectionError")
        await use_case.execute(dto)

        mock_loki.send_error.assert_called_once_with(group)

    @pytest.mark.asyncio
    async def test_execute_without_loki_client(
        self, fingerprint_service, masking_service, mock_notification_service
    ):
        """Test that execution succeeds without loki_client (default None)."""
        event_repo = Mock()
        event_repo.save = AsyncMock()

        group = ErrorGroup(
            fingerprint="abc123",
            exception_type="ConnectionError",
            message="Test error",
        )

        group_repo = Mock()
        group_repo.get_or_create_by_fingerprint = AsyncMock(return_value=group)
        group_repo.update = AsyncMock()

        use_case = ProcessErrorUseCase(
            event_repo=event_repo,
            group_repo=group_repo,
            notification_service=mock_notification_service,
            fingerprint_service=fingerprint_service,
            masking_service=masking_service,
            # loki_client not set — defaults to None
        )

        dto = ErrorEventDTO(message="Test error")
        result = await use_case.execute(dto)

        assert isinstance(result, ErrorGroup)
