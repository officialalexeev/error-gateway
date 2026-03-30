"""Main FastAPI router with versioning support."""

from app.api.v1.routes.errors import router as errors_router
from app.api.v1.routes.groups import router as groups_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.loki import router as loki_router
from fastapi import APIRouter

api_router = APIRouter()

# Include v1 routes
api_router.include_router(errors_router, prefix="/v1", tags=["Errors v1"])
api_router.include_router(groups_router, prefix="/v1", tags=["Groups v1"])
api_router.include_router(health_router, prefix="/v1", tags=["Health v1"])
api_router.include_router(loki_router, prefix="/v1", tags=["Loki v1"])

__all__ = ["api_router"]
