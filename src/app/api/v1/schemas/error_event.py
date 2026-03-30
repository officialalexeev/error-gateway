"""Error event Pydantic schemas for API v1."""

import json
import sys
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

MAX_CONTEXT_SIZE = 10240  # 10KB
MAX_CONTEXT_ITEMS = 100
MAX_CONTEXT_DEPTH = 5


def get_json_size(data: Any) -> int:
    """
    Calculate size of data when serialized to JSON.

    This gives accurate measure of data size for API transmission
    and storage, unlike sys.getsizeof() which only measures
    the container object.

    Args:
        data: Any JSON-serializable data

    Returns:
        Size in bytes of JSON-encoded data
    """
    try:
        return len(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError):
        # Fallback to sys.getsizeof if JSON serialization fails
        return sys.getsizeof(data)


class ErrorEventCreateSchemaV1(BaseModel):
    """Schema for creating error event (API v1)."""

    message: str = Field(..., description="Error message", min_length=1, max_length=1000)
    exception_type: str = Field(default="Error", description="Exception type")
    stack_trace: str | None = Field(
        default=None,
        description="Stack trace",
        max_length=10000,
    )
    environment: str = Field(
        default="unknown", description="Environment (development/staging/production)", max_length=50
    )
    release_version: str | None = Field(
        default=None, description="Release version (e.g., 1.2.3)", max_length=50
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Context data",
    )

    @field_validator("stack_trace")
    @classmethod
    def validate_stack_trace(cls, v: str | None) -> str | None:
        """
        Validate and normalize stack trace.

        - Empty strings and whitespace-only strings become None
        - Leading/trailing whitespace is trimmed
        - None is allowed (no stack trace)
        """
        if v is None:
            return None

        # Trim whitespace
        v = v.strip()

        # Convert empty/whitespace-only to None
        if not v:
            return None

        return v

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: dict[str, Any]) -> dict[str, Any]:
        """
        Validate context size, item count, and depth.

        Checks:
        1. Maximum number of items (MAX_CONTEXT_ITEMS)
        2. Maximum JSON-serialized size (MAX_CONTEXT_SIZE)
        3. Maximum nesting depth (MAX_CONTEXT_DEPTH)
        """
        # Check item count
        if len(v) > MAX_CONTEXT_ITEMS:
            raise ValueError(f"Context too many items (max {MAX_CONTEXT_ITEMS})")

        # Check size using JSON serialization (accurate for transmission/storage)
        size = get_json_size(v)
        if size > MAX_CONTEXT_SIZE:
            raise ValueError(f"Context too large (max {MAX_CONTEXT_SIZE} bytes, got {size})")

        # Check depth
        def check_depth(d: dict, depth: int = 0) -> bool:
            if depth > MAX_CONTEXT_DEPTH:
                return False
            return all(
                check_depth(val, depth + 1) if isinstance(val, dict) else True for val in d.values()
            )

        if not check_depth(v, 0):
            raise ValueError(f"Context nesting too deep (max {MAX_CONTEXT_DEPTH})")

        return v


class ErrorEventResponseSchemaV1(BaseModel):
    """Schema for error event response (API v1)."""

    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Response message")


class ErrorEventDetailSchemaV1(BaseModel):
    """Schema for error event details (API v1)."""

    model_config = {"from_attributes": True}

    id: UUID = Field(..., description="Event ID")
    message: str = Field(..., description="Error message")
    stack_trace: str | None = Field(default=None, description="Stack trace")
    context: dict[str, Any] = Field(default_factory=dict, description="Context")
    timestamp: datetime = Field(..., description="Event timestamp (ISO 8601)")
