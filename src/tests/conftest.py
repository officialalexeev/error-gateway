"""
Test Fixtures.

DRY Principle (Don't Repeat Yourself):
- Common fixtures extracted to conftest
- Reuse across tests

Async: Async fixtures
"""

from unittest.mock import AsyncMock, Mock

import pytest
from app.core.config import get_settings
from app.core.database import Base
from app.domain.services.services import FingerprintService, MaskingService

# Import models to register them with Base BEFORE creating tables
from app.infrastructure.db.models import ErrorEventModel, ErrorGroupModel  # noqa: F401
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest.fixture
def settings():
    """Get settings (cached)."""
    return get_settings()


@pytest.fixture(scope="function")
def db_session():
    """
    Async in-memory database session (SQLite).

    Used for test isolation from main database.
    Created synchronously to avoid pytest-asyncio caching issues.
    """
    import asyncio

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Create tables
    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create_tables())

    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    session = AsyncSessionLocal()

    yield session

    # Cleanup
    async def cleanup():
        await session.close()
        await engine.dispose()

    asyncio.run(cleanup())


@pytest.fixture
def mock_notification_service():
    """Mock notification service for tests."""
    service = Mock()
    service.notify = AsyncMock(return_value=True)
    service.should_notify = Mock(return_value=True)
    return service


@pytest.fixture
def fingerprint_service():
    """Real fingerprinting service for tests."""
    return FingerprintService()


@pytest.fixture
def masking_service():
    """Real masking service for tests."""
    return MaskingService()


@pytest.fixture
def sample_error_data():
    """Sample error data for tests."""
    return {
        "message": "Database connection failed",
        "exception_type": "ConnectionError",
        "stack_trace": "File 'app/db.py', line 42, in connect\nraise ConnectionError()",
        "context": {
            "user_id": 123,
            "email": "test@example.com",
            "token": "secret_token_123",
        },
    }


@pytest.fixture
def sample_error_group():
    """Sample error group for tests."""
    from app.domain.entities.error_group import ErrorGroup

    return ErrorGroup(
        fingerprint="abc123",
        exception_type="ConnectionError",
        message="Database connection failed",
        count=1,
    )
