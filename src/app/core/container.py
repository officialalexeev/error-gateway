"""Application DI container — built with punq.

Composition Root — единственное место где импортируются конкретные реализации.

## Почему это НЕ нарушение Clean Architecture

Это стандартный паттерн Dependency Injection:
- **Domain/Application слои** зависят только от абстракций (Protocol interfaces)
- **Infrastructure слой** предоставляет конкретные реализации
- **Composition Root** (этот файл) собирает всё вместе в точке входа

Импорты из `infrastructure.*` здесь **допустимы и необходимы** для создания
экземпляров сервисов. Это единственное место в приложении где такие импорты
разрешены.

## Registration rules

All shared, long-lived services are registered here.
Request-scoped objects (DB session, repositories) stay in FastAPI Depends.

  - **Singletons**  → `register(Interface, instance=...)` — one instance for the app lifetime
  - **Transient**   → `register(Class, scope=Scope.transient)` — new instance per resolve()
"""

import punq
from app.application.interfaces.interfaces import LokiService, NotificationService
from app.core.config import settings
from app.domain.services.services import FingerprintService, MaskingService, RateLimitService
from app.infrastructure.loki.client import LokiClient
from app.infrastructure.notifications.factory import NotificationFactory
from app.infrastructure.rate_limit.limiter import create_rate_limiter


def _build_container() -> punq.Container:
    """Register all application services into the DI container."""
    c = punq.Container()

    # ── Stateless domain services ─────────────────────────────────────────────
    # Both are configured once at startup and never mutate — safe as singletons.
    c.register(FingerprintService, instance=FingerprintService())
    c.register(
        MaskingService,
        instance=MaskingService(
            mask_email=settings.MASK_EMAIL,
            mask_phone=settings.MASK_PHONE,
            mask_credit_card=settings.MASK_CREDIT_CARD,
            mask_tokens=settings.MASK_TOKENS,
        ),
    )

    # ── Notification service ──────────────────────────────────────────────────
    # Singleton: owns HTTP (Telegram) and SMTP (Email) clients with connection pools.
    c.register(
        NotificationService,
        instance=NotificationFactory.create_notification_service(settings),
    )

    # ── Rate limiter ──────────────────────────────────────────────────────────
    # Singleton: owns either in-memory sliding window state or a Redis connection.
    c.register(
        RateLimitService,
        instance=create_rate_limiter(
            redis_url=settings.REDIS_URL,
            limit=settings.RATE_LIMIT_PER_MINUTE,
            window_seconds=60,
        ),
    )

    # ── Loki client (optional) ────────────────────────────────────────────────
    # Registered only when LOKI_URL is set. Callers use try/except
    # punq.MissingDependencyError to handle the "not configured" case.
    if settings.use_loki and settings.LOKI_URL:
        c.register(LokiService, instance=LokiClient(url=settings.LOKI_URL))

    return c


container = _build_container()
