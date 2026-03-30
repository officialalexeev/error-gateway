"""API v1 Pydantic schemas."""

from app.api.v1.schemas.error_event import (
    ErrorEventCreateSchemaV1,
    ErrorEventDetailSchemaV1,
    ErrorEventResponseSchemaV1,
)
from app.api.v1.schemas.error_group import (
    ErrorGroupDetailSchemaV1,
    ErrorGroupListSchemaV1,
    ErrorGroupSchemaV1,
)
from app.api.v1.schemas.loki import LokiWebhookSchemaV1

__all__ = [
    # Error Event
    "ErrorEventCreateSchemaV1",
    "ErrorEventResponseSchemaV1",
    "ErrorEventDetailSchemaV1",
    # Error Group
    "ErrorGroupSchemaV1",
    "ErrorGroupListSchemaV1",
    "ErrorGroupDetailSchemaV1",
    # Loki
    "LokiWebhookSchemaV1",
]
