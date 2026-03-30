"""API v1 routes."""

from app.api.v1.routes.errors import router as errors_router
from app.api.v1.routes.groups import router as groups_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.loki import router as loki_router

__all__ = ["errors_router", "groups_router", "health_router", "loki_router"]
