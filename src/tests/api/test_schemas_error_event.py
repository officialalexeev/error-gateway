"""Tests for ErrorEvent schemas validation."""

import pytest
from pydantic import ValidationError
from app.api.v1.schemas.error_event import ErrorEventCreateSchemaV1


class TestStackTraceValidation:
    """Tests for stack_trace field validation."""

    def test_stack_trace_none(self):
        """Test None stack_trace is allowed."""
        schema = ErrorEventCreateSchemaV1(
            message="Test error",
            stack_trace=None,
        )
        assert schema.stack_trace is None

    def test_stack_trace_valid(self):
        """Test valid stack_trace."""
        stack = 'File "app.py", line 10\n  raise ValueError()'
        schema = ErrorEventCreateSchemaV1(
            message="Test error",
            stack_trace=stack,
        )
        assert schema.stack_trace == stack

    def test_stack_trace_empty_string(self):
        """Test empty string becomes None."""
        schema = ErrorEventCreateSchemaV1(
            message="Test error",
            stack_trace="",
        )
        assert schema.stack_trace is None

    def test_stack_trace_whitespace_only(self):
        """Test whitespace-only string becomes None."""
        schema = ErrorEventCreateSchemaV1(
            message="Test error",
            stack_trace="   ",
        )
        assert schema.stack_trace is None

    def test_stack_trace_trimmed(self):
        """Test leading/trailing whitespace is trimmed."""
        schema = ErrorEventCreateSchemaV1(
            message="Test error",
            stack_trace='  File "app.py", line 10\n  ',
        )
        assert schema.stack_trace == 'File "app.py", line 10'
        assert schema.stack_trace[0] != " "
        assert schema.stack_trace[-1] != " "

    def test_stack_trace_max_length(self):
        """Test stack_trace exceeding max_length raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorEventCreateSchemaV1(
                message="Test error",
                stack_trace="x" * 10001,
            )
        assert "stack_trace" in str(exc_info.value)

    def test_stack_trace_exactly_max_length(self):
        """Test stack_trace at exactly max_length is allowed."""
        stack = "x" * 10000
        schema = ErrorEventCreateSchemaV1(
            message="Test error",
            stack_trace=stack,
        )
        assert len(schema.stack_trace) == 10000

    def test_stack_trace_with_newlines(self):
        """Test stack_trace with newlines is preserved."""
        stack = "Line 1\nLine 2\nLine 3"
        schema = ErrorEventCreateSchemaV1(
            message="Test error",
            stack_trace=stack,
        )
        assert schema.stack_trace == stack
        assert "\n" in schema.stack_trace

    def test_stack_trace_tabs_and_newlines(self):
        """Test stack_trace with tabs and newlines is preserved."""
        stack = 'File "app.py", line 10\n\traise ValueError()'
        schema = ErrorEventCreateSchemaV1(
            message="Test error",
            stack_trace=stack,
        )
        assert schema.stack_trace == stack


class TestMessageValidation:
    """Tests for message field validation."""

    def test_message_required(self):
        """Test message is required."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorEventCreateSchemaV1()
        assert "message" in str(exc_info.value)

    def test_message_empty_string(self):
        """Test empty message raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorEventCreateSchemaV1(message="")
        assert "message" in str(exc_info.value)

    def test_message_valid(self):
        """Test valid message."""
        schema = ErrorEventCreateSchemaV1(message="Test error")
        assert schema.message == "Test error"

    def test_message_max_length(self):
        """Test message at max length."""
        msg = "x" * 1000
        schema = ErrorEventCreateSchemaV1(message=msg)
        assert len(schema.message) == 1000

    def test_message_exceeds_max_length(self):
        """Test message exceeding max length raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorEventCreateSchemaV1(message="x" * 1001)
        assert "message" in str(exc_info.value)


class TestEnvironmentValidation:
    """Tests for environment field validation."""

    def test_environment_default(self):
        """Test default environment."""
        schema = ErrorEventCreateSchemaV1(message="Test error")
        assert schema.environment == "unknown"

    def test_environment_custom(self):
        """Test custom environment."""
        schema = ErrorEventCreateSchemaV1(
            message="Test error",
            environment="production",
        )
        assert schema.environment == "production"

    def test_environment_max_length(self):
        """Test environment at max length."""
        env = "x" * 50
        schema = ErrorEventCreateSchemaV1(
            message="Test error",
            environment=env,
        )
        assert len(schema.environment) == 50

    def test_environment_exceeds_max_length(self):
        """Test environment exceeding max length raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorEventCreateSchemaV1(
                message="Test error",
                environment="x" * 51,
            )
        assert "environment" in str(exc_info.value)


class TestReleaseVersionValidation:
    """Tests for release_version field validation."""

    def test_release_version_none(self):
        """Test None release_version."""
        schema = ErrorEventCreateSchemaV1(message="Test error")
        assert schema.release_version is None

    def test_release_version_valid(self):
        """Test valid release_version."""
        schema = ErrorEventCreateSchemaV1(
            message="Test error",
            release_version="1.2.3",
        )
        assert schema.release_version == "1.2.3"

    def test_release_version_max_length(self):
        """Test release_version at max length."""
        version = "x" * 50
        schema = ErrorEventCreateSchemaV1(
            message="Test error",
            release_version=version,
        )
        assert len(schema.release_version) == 50

    def test_release_version_exceeds_max_length(self):
        """Test release_version exceeding max length raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorEventCreateSchemaV1(
                message="Test error",
                release_version="x" * 51,
            )
        assert "release_version" in str(exc_info.value)
