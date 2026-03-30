"""Async database setup with SQLite/PostgreSQL auto-detection."""

from pathlib import Path
from typing import AsyncGenerator

from app.core.config import settings
from app.core.logger import log
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


# Auto-detect database type
if settings.use_postgres:
    engine = create_async_engine(  # type: ignore[assignment]
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        execution_options={"statement_timeout": 30000},
    )
else:
    DATA_DIR = Path("./data")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    engine = create_async_engine(
        "sqlite+aiosqlite:///./data/error-gateway.db",
        echo=False,
        connect_args={
            # Required for aiosqlite + asyncio compatibility.
            # aiosqlite serializes all queries through an internal executor queue,
            # so thread safety is maintained despite this setting.
            # Without this, asyncio event loop would be blocked.
            "check_same_thread": False,
            "timeout": 30,  # Busy timeout in seconds
        },
    )

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Initialize database by creating all tables and optimizing SQLite settings."""
    async with engine.begin() as conn:
        from app.infrastructure.db.models import ErrorEventModel, ErrorGroupModel  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)

        # Optimize SQLite for better concurrent safety and performance
        if not settings.use_postgres:
            log.info(
                "SQLite mode: Using SQLite for embedded deployment. "
                "Switch to PostgreSQL for high write loads.",
                extra={"event": "sqlite_mode_info"},
            )

            # Apply PRAGMA optimizations for SQLite
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA busy_timeout=30000"))
            await conn.execute(text("PRAGMA synchronous=NORMAL"))
            await conn.execute(text("PRAGMA cache_size=-64000"))  # 64MB cache
            await conn.execute(text("PRAGMA temp_store=MEMORY"))

            log.info(
                "SQLite PRAGMA settings applied: WAL mode, 30s busy timeout",
                extra={"event": "sqlite_pragma_applied"},
            )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.

    Usage in FastAPI:
        db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
