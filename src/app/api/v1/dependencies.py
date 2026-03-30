"""FastAPI dependency injection for API v1 — resolves from the punq container.

Singletons (NotificationService, MaskingService, etc.) are managed by the
punq container in app.core.container.  Request-scoped objects (DB session,
repositories, use cases) are wired here via FastAPI Depends().
"""

import punq
from app.application.interfaces.interfaces import LokiService, NotificationService
from app.application.services.loki_alert_processor import LokiAlertProcessor
from app.application.use_cases.use_cases import ProcessErrorUseCase
from app.core.config import settings
from app.core.container import container
from app.core.database import get_db
from app.domain.repositories.interfaces import ErrorEventRepository, ErrorGroupRepository
from app.domain.services.services import FingerprintService, MaskingService
from app.infrastructure.db.repositories import (
    AsyncSQLAlchemyErrorEventRepository,
    AsyncSQLAlchemyErrorGroupRepository,
)
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# ── Singleton services (resolved from DI container) ───────────────────────────


def get_fingerprint_service() -> FingerprintService:
    """Resolve FingerprintService singleton from DI container."""
    return container.resolve(FingerprintService)


def get_masking_service() -> MaskingService:
    """Resolve MaskingService singleton from DI container."""
    return container.resolve(MaskingService)


def get_notification_service() -> NotificationService:
    """Resolve NotificationService singleton from DI container."""
    return container.resolve(NotificationService)


def get_loki_client() -> LokiService | None:
    """Resolve LokiClient singleton from DI container, or None if not configured."""
    try:
        return container.resolve(LokiService)
    except punq.MissingDependencyError:
        return None


# ── Request-scoped objects (need DB session — cannot be pre-built singletons) ─


def get_error_event_repo(db: AsyncSession = Depends(get_db)) -> ErrorEventRepository:
    """Get error event repository (request-scoped: wraps the current DB session)."""
    return AsyncSQLAlchemyErrorEventRepository(db)


def get_error_group_repo(db: AsyncSession = Depends(get_db)) -> ErrorGroupRepository:
    """Get error group repository (request-scoped: wraps the current DB session)."""
    return AsyncSQLAlchemyErrorGroupRepository(db)


def get_process_error_use_case(
    event_repo: ErrorEventRepository = Depends(get_error_event_repo),
    group_repo: ErrorGroupRepository = Depends(get_error_group_repo),
    notification_service: NotificationService = Depends(get_notification_service),
    fingerprint_service: FingerprintService = Depends(get_fingerprint_service),
    masking_service: MaskingService = Depends(get_masking_service),
    loki_client: LokiService | None = Depends(get_loki_client),
) -> ProcessErrorUseCase:
    """Assemble ProcessErrorUseCase with all resolved dependencies."""
    return ProcessErrorUseCase(
        event_repo=event_repo,
        group_repo=group_repo,
        notification_service=notification_service,
        fingerprint_service=fingerprint_service,
        masking_service=masking_service,
        throttle_minutes=settings.NOTIFICATION_THROTTLE_MINUTES,
        loki_client=loki_client,
    )


def get_loki_alert_processor(
    use_case: ProcessErrorUseCase = Depends(get_process_error_use_case),
) -> LokiAlertProcessor:
    """Get Loki alert processor instance."""
    return LokiAlertProcessor(use_case)
