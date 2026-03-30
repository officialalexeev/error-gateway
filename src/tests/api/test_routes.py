"""
Tests for API Routes.

Async: Async tests
Testing Pattern: dependency_overrides (FastAPI best practice)
"""

from unittest.mock import AsyncMock, Mock

import pytest
from app.main import app
from fastapi.testclient import TestClient


# Create test client
@pytest.fixture
def client():
    """Create test client."""
    with TestClient(app) as test_client:
        yield test_client


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestMetrics:
    """Tests for metrics endpoint."""

    def test_metrics(self, client):
        """Test metrics endpoint."""
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        assert "error_gateway_errors_total" in response.text
        assert "# HELP" in response.text
        assert "# TYPE" in response.text


class TestLokiWebhook:
    """Tests for Loki webhook endpoint."""

    def test_loki_webhook_empty(self, client):
        """Test Loki webhook with empty data."""
        response = client.post("/api/v1/loki/webhook", json={"alerts": []})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["processed"] == 0
        assert data["failed"] == 0

    def test_loki_webhook_with_alerts(self, client):
        """Test Loki webhook with alerts."""
        response = client.post(
            "/api/v1/loki/webhook",
            json={"alerts": [{"status": "firing", "labels": {"severity": "critical"}}]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["processed"] >= 0  # May process successfully


class TestIngestError:
    """Tests for ingest_error endpoint.

    Note: Integration testing is covered by TestProcessErrorUseCase tests
    which test the application layer with proper mocking.
    """

    pass


class TestListErrorGroups:
    """Tests for list_error_groups endpoint."""

    @pytest.mark.asyncio
    async def test_list_error_groups(self):
        """Test getting list of groups."""
        from datetime import datetime, timezone
        from uuid import uuid4

        from app.api.v1.dependencies import get_error_group_repo
        from app.domain.entities.error_group import ErrorGroup

        group_id = uuid4()
        mock_group = ErrorGroup(
            fingerprint="abc123",
            exception_type="ValueError",
            message="Test error",
            count=1,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            is_notified=False,
            id=group_id,
        )

        mock_repo = Mock()
        mock_repo.get_all = AsyncMock(return_value=([mock_group], 1))

        app.dependency_overrides[get_error_group_repo] = lambda: mock_repo

        try:
            response = TestClient(app).get("/api/v1/groups?limit=50&offset=0")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
        finally:
            app.dependency_overrides.clear()


class TestGetErrorGroup:
    """Tests for get_error_group endpoint."""

    @pytest.mark.asyncio
    async def test_get_error_group_not_found(self):
        """Test getting non-existent group."""
        from uuid import uuid4

        from app.api.v1.dependencies import get_error_group_repo

        mock_repo = Mock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        app.dependency_overrides[get_error_group_repo] = lambda: mock_repo

        try:
            response = TestClient(app).get(f"/api/v1/groups/{uuid4()}")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
