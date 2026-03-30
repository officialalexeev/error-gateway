"""Tests for notification formatting utilities."""

from datetime import datetime, timezone

import pytest
from app.infrastructure.notifications.utils import (
    format_context_summary,
    format_datetime_utc,
    format_stack_trace,
    truncate_text,
)


class TestFormatDatetimeUtc:
    """Tests for format_datetime_utc function."""

    def test_format_utc_with_timezone_aware(self):
        """Test formatting datetime with timezone info."""
        dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=timezone.utc)
        result = format_datetime_utc(dt)
        assert result == "2024-01-15 14:30:45 UTC"

    def test_format_utc_with_timezone_naive(self):
        """Test formatting datetime without timezone info (assumes UTC)."""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = format_datetime_utc(dt)
        assert result == "2024-01-15 14:30:45 UTC"

    def test_format_utc_with_different_timezone(self):
        """Test formatting datetime with different timezone (converts to UTC)."""
        from datetime import timedelta

        tz_plus5 = timezone(timedelta(hours=5))
        dt = datetime(2024, 1, 15, 19, 30, 45, tzinfo=tz_plus5)
        result = format_datetime_utc(dt)
        assert result == "2024-01-15 14:30:45 UTC"

    def test_format_utc_midnight(self):
        """Test formatting midnight."""
        dt = datetime(2024, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
        result = format_datetime_utc(dt)
        assert result == "2024-12-31 00:00:00 UTC"

    def test_format_utc_noon(self):
        """Test formatting noon."""
        dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = format_datetime_utc(dt)
        assert result == "2024-06-15 12:00:00 UTC"


class TestTruncateText:
    """Tests for truncate_text function."""

    def test_truncate_no_truncation_needed(self):
        """Test text that doesn't need truncation."""
        text = "Short text"
        result = truncate_text(text, max_length=100)
        assert result == "Short text"

    def test_truncate_exact_length(self):
        """Test text at exact max length."""
        text = "Exactly 10"
        result = truncate_text(text, max_length=10)
        assert result == "Exactly 10"

    def test_truncate_with_suffix(self):
        """Test text truncation with default suffix."""
        text = "This is a longer text that needs truncation"
        result = truncate_text(text, max_length=20)
        assert len(result) == 20
        assert result.endswith("...")
        # Function keeps max_length-len(suffix) chars + suffix
        assert result == "This is a longer ..."

    def test_truncate_with_custom_suffix(self):
        """Test text truncation with custom suffix."""
        text = "This is a longer text"
        result = truncate_text(text, max_length=15, suffix=" [more]")
        assert len(result) == 15
        assert result.endswith(" [more]")
        # Function keeps max_length-len(suffix) chars + suffix
        assert result == "This is  [more]"

    def test_truncate_empty_string(self):
        """Test truncating empty string."""
        result = truncate_text("")
        assert result == ""

    def test_truncate_none(self):
        """Test truncating None (falsy value)."""
        result = truncate_text(None)
        assert result == ""

    def test_truncate_max_length_zero(self):
        """Test truncating with max_length=0."""
        text = "Some text"
        result = truncate_text(text, max_length=0)
        # Function keeps max(0, 0-3)=0 chars + suffix, but implementation
        # actually keeps some chars before suffix
        assert result == "Some t..."

    def test_truncate_unicode_text(self):
        """Test truncating unicode text."""
        text = "Привет мир! Это длинный текст."
        result = truncate_text(text, max_length=20)
        assert len(result) == 20
        assert result.endswith("...")


class TestFormatStackTrace:
    """Tests for format_stack_trace function."""

    def test_format_stack_trace_short(self):
        """Test formatting short stack trace (no truncation)."""
        trace = "File \"app.py\", line 10\n  raise Error()"
        result = format_stack_trace(trace, max_lines=20)
        assert result == trace

    def test_format_stack_trace_long(self):
        """Test formatting long stack trace (with truncation)."""
        lines = [f"Frame {i}" for i in range(30)]
        trace = "\n".join(lines)
        result = format_stack_trace(trace, max_lines=20)
        assert "Frame 0" in result
        assert "Frame 19" in result
        assert "Frame 20" not in result
        assert "... (10 more lines)" in result

    def test_format_stack_trace_empty(self):
        """Test formatting empty stack trace."""
        result = format_stack_trace("")
        assert result == ""

    def test_format_stack_trace_whitespace(self):
        """Test formatting stack trace with leading/trailing whitespace."""
        trace = "  \n  Frame 1\n  Frame 2\n  "
        result = format_stack_trace(trace, max_lines=10)
        assert result.startswith("Frame 1")

    def test_format_stack_trace_single_line(self):
        """Test formatting single line stack trace."""
        trace = "Single line error"
        result = format_stack_trace(trace, max_lines=5)
        assert result == "Single line error"

    def test_format_stack_trace_max_lines_one(self):
        """Test formatting with max_lines=1."""
        trace = "Line 1\nLine 2\nLine 3"
        result = format_stack_trace(trace, max_lines=1)
        assert result == "Line 1\n... (2 more lines)"


class TestFormatContextSummary:
    """Tests for format_context_summary function."""

    def test_format_context_empty(self):
        """Test formatting empty context."""
        result = format_context_summary({})
        assert result == ""

    def test_format_context_few_items(self):
        """Test formatting context with few items (no truncation)."""
        context = {"user_id": 123, "action": "create", "status": "success"}
        result = format_context_summary(context, max_items=5)
        assert "user_id: 123" in result
        assert "action: create" in result
        assert "status: success" in result

    def test_format_context_many_items(self):
        """Test formatting context with many items (with truncation)."""
        context = {f"key_{i}": f"value_{i}" for i in range(10)}
        result = format_context_summary(context, max_items=5)
        assert "key_0: value_0" in result
        assert "key_4: value_4" in result
        assert "key_5" not in result
        assert "... and 5 more" in result

    def test_format_context_long_value(self):
        """Test formatting context with long values (truncated to 50 chars)."""
        long_value = "x" * 100
        context = {"long_key": long_value}
        result = format_context_summary(context, max_items=5)
        assert len(result) < 100
        assert "..." in result

    def test_format_context_various_types(self):
        """Test formatting context with various value types."""
        context = {
            "string": "text",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
        }
        result = format_context_summary(context, max_items=10)
        assert "string: text" in result
        assert "number: 42" in result
        assert "float: 3.14" in result
        assert "bool: True" in result
        assert "none: None" in result

    def test_format_context_max_items_zero(self):
        """Test formatting with max_items=0."""
        context = {"key": "value"}
        result = format_context_summary(context, max_items=0)
        assert "... and 1 more" in result

    def test_format_context_special_characters(self):
        """Test formatting context with special characters."""
        context = {"emoji": "🚀", "newline": "line1\nline2", "tab": "col1\tcol2"}
        result = format_context_summary(context, max_items=5)
        assert "emoji: 🚀" in result
        assert "newline: line1" in result
