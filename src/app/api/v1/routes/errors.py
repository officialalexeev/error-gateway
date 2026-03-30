"""Error ingestion endpoint."""

from app.api.v1.dependencies import get_process_error_use_case
from app.api.v1.rate_limit_deps import check_rate_limit
from app.api.v1.schemas.error_event import (
    ErrorEventCreateSchemaV1,
    ErrorEventResponseSchemaV1,
)
from app.application.dto.dto import ErrorEventDTO
from app.application.use_cases.use_cases import ProcessErrorUseCase
from app.core.logger import log
from fastapi import APIRouter, Depends

router = APIRouter()


@router.post(
    "/error",
    response_model=ErrorEventResponseSchemaV1,
    dependencies=[Depends(check_rate_limit)],
)
async def ingest_error(
    event: ErrorEventCreateSchemaV1,
    use_case: ProcessErrorUseCase = Depends(get_process_error_use_case),
) -> ErrorEventResponseSchemaV1:
    """Accept and process incoming error."""
    # Create DTO from schema
    dto = ErrorEventDTO(
        message=event.message,
        exception_type=event.exception_type,
        stack_trace=event.stack_trace,
        environment=event.environment,
        release_version=event.release_version,
        context=event.context or {},
    )

    # Process error via use case
    await use_case.execute(dto)

    log.info(
        "Error received and processed",
        extra={
            "event": "error_ingested",
            "exception_type": event.exception_type,
            "environment": event.environment,
            "release_version": event.release_version,
        },
    )

    return ErrorEventResponseSchemaV1(
        status="accepted",
        message="Error received and processed",
    )
