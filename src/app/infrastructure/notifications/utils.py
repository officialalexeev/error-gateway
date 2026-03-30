"""Common notification formatting utilities."""

from datetime import datetime, timezone


def format_datetime_utc(dt: datetime) -> str:
    """
    Format datetime to UTC string.

    Args:
        dt: Datetime object (timezone-aware or naive)

    Returns:
        Formatted string in format "YYYY-MM-DD HH:MM:SS UTC"
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncated

    Returns:
        Truncated text with suffix if needed
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_stack_trace(stack_trace: str, max_lines: int = 20) -> str:
    """
    Format stack trace for notification.

    Args:
        stack_trace: Full stack trace string
        max_lines: Maximum number of lines to include

    Returns:
        Formatted stack trace
    """
    if not stack_trace:
        return ""

    lines = stack_trace.strip().split("\n")
    truncated = lines[:max_lines]
    result = "\n".join(truncated)

    if len(lines) > max_lines:
        result += f"\n... ({len(lines) - max_lines} more lines)"

    return result


def format_context_summary(context: dict, max_items: int = 5) -> str:
    """
    Format context dictionary as summary string.

    Args:
        context: Context dictionary
        max_items: Maximum number of items to show

    Returns:
        Formatted context summary
    """
    if not context:
        return ""

    items = []
    for i, (key, value) in enumerate(context.items()):
        if i >= max_items:
            items.append(f"... and {len(context) - max_items} more")
            break
        value_str = str(value)[:50]
        if len(str(value)) > 50:
            value_str += "..."
        items.append(f"{key}: {value_str}")

    return "\n".join(items)
