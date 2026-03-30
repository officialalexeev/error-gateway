"""Error group endpoints."""

from uuid import UUID

from app.api.v1.dependencies import get_error_group_repo
from app.api.v1.schemas.error_group import (
    ErrorGroupDetailSchemaV1,
    ErrorGroupListSchemaV1,
    ErrorGroupSchemaV1,
)
from app.core.config import settings
from app.domain.repositories.interfaces import ErrorGroupRepository
from fastapi import APIRouter, Depends, HTTPException, Query, status

router = APIRouter()


@router.get("/groups", response_model=ErrorGroupListSchemaV1)
async def list_error_groups(
    limit: int = Query(
        default=50,
        le=settings.MAX_PAGINATION_LIMIT,
        ge=1,
        description=f"Max {settings.MAX_PAGINATION_LIMIT}",
    ),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    repo: ErrorGroupRepository = Depends(get_error_group_repo),
) -> ErrorGroupListSchemaV1:
    """Get list of error groups."""
    groups, total = await repo.get_all(limit=limit, offset=offset)

    return ErrorGroupListSchemaV1(
        groups=[ErrorGroupSchemaV1.model_validate(g) for g in groups],
        total=total,
    )


@router.get("/groups/{group_id}", response_model=ErrorGroupDetailSchemaV1)
async def get_error_group(
    group_id: UUID,
    repo: ErrorGroupRepository = Depends(get_error_group_repo),
) -> ErrorGroupDetailSchemaV1:
    """Get error group details."""
    group = await repo.get_by_id(group_id)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    return ErrorGroupDetailSchemaV1.model_validate(group)
