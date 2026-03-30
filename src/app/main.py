"""Error Gateway — FastAPI microservice for error tracking with notifications."""

import asyncio
import time
from contextlib import asynccontextmanager, suppress

import punq
from app.api.router import api_router
from app.application.interfaces.interfaces import LokiService, NotificationService
from app.core.config import settings
from app.core.container import container
from app.core.database import init_db
from app.core.logger import log
from app.core.metrics import ACTIVE_CHANNELS, REQUEST_LATENCY, REQUEST_TOTAL
from app.core.shutdown import ShutdownManager
from app.domain.services.services import RateLimitService
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

shutdown_manager = ShutdownManager()

_CLEANUP_INTERVAL_SECONDS = 3600  # run in-memory rate limiter GC every hour


async def _rate_limiter_cleanup_loop() -> None:
    """Periodically purge stale keys from the in-memory rate limiter."""
    rate_limiter = container.resolve(RateLimitService)
    if not hasattr(rate_limiter, "cleanup"):
        return  # Redis limiter manages TTL natively — nothing to do
    while True:
        await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
        try:
            removed: int = await rate_limiter.cleanup()  # type: ignore[attr-defined]
            if removed > 0:
                log.info(
                    f"Rate limiter GC: removed {removed} stale keys",
                    extra={"event": "rate_limiter_cleanup", "removed": removed},
                )
        except Exception as e:
            log.error(
                f"Rate limiter cleanup error: {e}", extra={"event": "rate_limiter_cleanup_error"}
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    log.info("Starting Error Gateway...", extra={"event": "startup"})
    await init_db()
    log.info("Database initialized", extra={"event": "db_initialized"})

    # Register graceful shutdown handlers for stateful singletons from the container
    notification_service = container.resolve(NotificationService)
    shutdown_manager.register(notification_service.close)

    # Initialise ACTIVE_CHANNELS gauge so Prometheus shows 0 for unconfigured channels
    if hasattr(notification_service, "channels"):
        for channel_name in notification_service.channels:
            ACTIVE_CHANNELS.labels(channel=channel_name).set(1)

    try:
        loki_client = container.resolve(LokiService)
        shutdown_manager.register(loki_client.close)
        log.info(
            f"Loki log shipping enabled: {settings.LOKI_URL}",
            extra={"event": "loki_enabled"},
        )
    except punq.MissingDependencyError:
        pass  # Loki not configured — skip

    cleanup_task = asyncio.create_task(_rate_limiter_cleanup_loop())

    yield

    cleanup_task.cancel()
    with suppress(asyncio.CancelledError):
        await cleanup_task

    log.info("Shutting down Error Gateway...", extra={"event": "shutdown"})
    await shutdown_manager.shutdown()


app = FastAPI(
    title="Error Gateway",
    description="Autonomous microservice for error tracking with notifications",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
if settings.cors_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def request_metrics_middleware(request: Request, call_next):
    """Record request count and latency for all endpoints."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    REQUEST_TOTAL.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=str(response.status_code),
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(elapsed)
    return response


# Include router
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": "Error Gateway", "version": "1.0.0", "status": "running"}
