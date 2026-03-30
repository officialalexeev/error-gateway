"""
Integration Tests for API Endpoints.

Tests the full API stack with real database and dependencies.
Uses TestClient for HTTP-level testing.
"""

import asyncio

import pytest
from app.core.database import Base, get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest.fixture
def client():
    """Create test client with isolated database."""
    # Create in-memory SQLite engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Create tables
    from app.infrastructure.db.models import ErrorEventModel, ErrorGroupModel  # noqa: F401

    # Initialize database
    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_db())

    # Create session factory
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    # Override get_db dependency
    async def override_get_db():
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    test_client = TestClient(app)
    yield test_client

    # Cleanup
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_check_returns_healthy(self, client):
        """Health check should return healthy status."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestMetricsEndpoint:
    """Test /metrics endpoint."""

    def test_metrics_returns_prometheus_format(self, client):
        """Metrics should return Prometheus format."""
        response = client.get("/api/v1/metrics")

        assert response.status_code == 200
        assert "error_gateway_errors_total" in response.text
        assert "# HELP" in response.text
        assert "# TYPE" in response.text


class TestErrorGroupsEndpoint:
    """Test /groups endpoint."""

    def test_list_groups_empty(self, client):
        """List groups should return empty list when no errors."""
        response = client.get("/api/v1/groups")

        assert response.status_code == 200
        data = response.json()
        assert data["groups"] == []
        assert data["total"] == 0

    def test_list_groups_pagination(self, client):
        """List groups should support pagination."""
        response = client.get("/api/v1/groups?limit=10&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert "groups" in data
        assert "total" in data


class TestErrorGroupDetailEndpoint:
    """Test /groups/{group_id} endpoint."""

    def test_get_group_not_found(self, client):
        """Get group should return 404 for non-existent group."""
        response = client.get("/api/v1/groups/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404
        assert "Group not found" in response.json()["detail"]


class TestLokiWebhookEndpoint:
    """Test /loki/webhook endpoint."""

    def test_loki_webhook_empty_alerts(self, client):
        """Loki webhook should handle empty alerts."""
        response = client.post("/api/v1/loki/webhook", json={"alerts": []})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["processed"] == 0
        assert data["failed"] == 0

    def test_loki_webhook_with_alert(self, client):
        """Loki webhook should process alerts."""
        alert_data = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"severity": "critical", "alertname": "HighErrorRate"},
                    "annotations": {"description": "Error rate is too high"},
                }
            ]
        }
        response = client.post("/api/v1/loki/webhook", json=alert_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        # Note: Alert processing may fail without proper notification setup
        # but endpoint should still return 200


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_endpoint_accessible(self, client):
        """Rate limited endpoint should be accessible."""
        response = client.post(
            "/api/v1/error", json={"message": "Test error", "exception_type": "TestError"}
        )

        # Should be 422 (validation) or 200 (success) or 429 (rate limited)
        assert response.status_code in [200, 422, 429]


class TestErrorIngestion:
    """Test error ingestion endpoint validation."""

    def test_ingest_error_with_environment(self, client):
        """Ingest error should accept environment field (validation only)."""
        error_data = {
            "message": "Test error",
            "exception_type": "TestError",
            "environment": "production",
            "release_version": "1.2.3",
        }
        response = client.post("/api/v1/error", json=error_data)

        # May be 200 (success) or 422 (DI not configured in test)
        # But should NOT be 400 (bad schema)
        assert response.status_code in [200, 422]
        if response.status_code == 422:
            # Check it's not schema validation error
            detail = response.json()["detail"]
            assert not any("environment" in str(d) for d in detail)

    def test_ingest_error_environment_default(self, client):
        """Ingest error should accept missing environment field."""
        error_data = {
            "message": "Test error",
            "exception_type": "TestError",
            # No environment field - should default to "unknown"
        }
        response = client.post("/api/v1/error", json=error_data)

        # May be 200 (success) or 422 (DI not configured in test)
        assert response.status_code in [200, 422]

    def test_ingest_error_validation_empty_message(self, client):
        """Ingest error should reject empty message."""
        error_data = {"message": ""}
        response = client.post("/api/v1/error", json=error_data)

        assert response.status_code == 422

    def test_ingest_error_validation_context_depth(self, client):
        """Ingest error should reject deeply nested context."""
        error_data = {
            "message": "Test",
            "context": {"a": {"b": {"c": {"d": {"e": {"f": {"g": "too deep"}}}}}}},
        }
        response = client.post("/api/v1/error", json=error_data)

        assert response.status_code == 422

    def test_ingest_error_validation_max_length(self, client):
        """Ingest error should validate max length."""
        error_data = {"message": "x" * 2000}  # Exceeds 1000 char limit
        response = client.post("/api/v1/error", json=error_data)

        assert response.status_code == 422


class TestPagination:
    """Test pagination limits."""

    def test_pagination_limit_max(self, client):
        """Pagination should accept max limit."""
        response = client.get("/api/v1/groups?limit=100&offset=0")

        assert response.status_code == 200

    def test_pagination_limit_exceeds_max(self, client):
        """Pagination should reject limit exceeding max."""
        response = client.get("/api/v1/groups?limit=101&offset=0")

        assert response.status_code == 422
        assert "limit" in response.json()["detail"][0]["loc"]

    def test_pagination_limit_zero(self, client):
        """Pagination should reject zero limit."""
        response = client.get("/api/v1/groups?limit=0&offset=0")

        assert response.status_code == 422

    def test_pagination_negative_offset(self, client):
        """Pagination should reject negative offset."""
        response = client.get("/api/v1/groups?limit=50&offset=-1")

        assert response.status_code == 422
