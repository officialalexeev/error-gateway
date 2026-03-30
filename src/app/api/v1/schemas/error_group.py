"""Error group Pydantic schemas for API v1."""

from datetime import datetime
from typing import List
from uuid import UUID

from app.api.v1.schemas.error_event import ErrorEventDetailSchemaV1
from pydantic import BaseModel, Field


class ErrorGroupSchemaV1(BaseModel):
    """Schema for error group (API v1)."""

    model_config = {"from_attributes": True}

    id: UUID = Field(..., description="Group ID")
    fingerprint: str = Field(..., description="Error fingerprint")
    exception_type: str = Field(..., description="Exception type")
    message: str = Field(..., description="Error message")
    count: int = Field(..., description="Error count")
    first_seen: datetime = Field(..., description="First occurrence (ISO 8601)")
    last_seen: datetime = Field(..., description="Last occurrence (ISO 8601)")
    is_notified: bool = Field(default=False, description="Notification status")


class ErrorGroupListSchemaV1(BaseModel):
    """Schema for error group list (API v1)."""

    groups: List[ErrorGroupSchemaV1] = Field(..., description="Error groups")
    total: int = Field(..., description="Total count")


class ErrorGroupDetailSchemaV1(BaseModel):
    """Schema for error group details (API v1)."""

    model_config = {"from_attributes": True}

    id: UUID = Field(..., description="Group ID")
    fingerprint: str = Field(..., description="Error fingerprint")
    exception_type: str = Field(..., description="Exception type")
    message: str = Field(..., description="Error message")
    count: int = Field(..., description="Error count")
    first_seen: datetime = Field(..., description="First occurrence (ISO 8601)")
    last_seen: datetime = Field(..., description="Last occurrence (ISO 8601)")
    is_notified: bool = Field(default=False, description="Notification status")
    events: List[ErrorEventDetailSchemaV1] = Field(default_factory=list)
