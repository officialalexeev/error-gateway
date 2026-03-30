"""Loki webhook Pydantic schemas for API v1."""

from typing import Any, List

from pydantic import BaseModel, Field


class LokiWebhookSchemaV1(BaseModel):
    """Schema for Loki webhook (API v1)."""

    alerts: List[dict[str, Any]] = Field(..., description="Alert list")
