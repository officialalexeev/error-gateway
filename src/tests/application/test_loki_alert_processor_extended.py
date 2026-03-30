"""
Extended Tests for Loki Alert Processor.

Test Isolation Principle:
- Mock error_service
- Only alert processor logic is tested

Async: Async tests
"""

from unittest.mock import AsyncMock, Mock

import pytest
from app.application.dto.dto import ErrorEventDTO
from app.application.services.loki_alert_processor import LokiAlertProcessor


class TestLokiAlertProcessor:
    """Tests for LokiAlertProcessor."""

    @pytest.fixture
    def mock_error_service(self):
        """Mock use case."""
        use_case = Mock()
        use_case.execute = AsyncMock(return_value=None)
        return use_case

    @pytest.fixture
    def processor(self, mock_error_service):
        """Create alert processor."""
        return LokiAlertProcessor(mock_error_service)

    @pytest.mark.asyncio
    async def test_process_alert_minimal(self, processor, mock_error_service):
        """Test minimal alert processing."""
        alert = {
            "labels": {"alertname": "TestAlert"},
            "annotations": {},
            "status": "firing",
        }

        await processor.process_alert(alert)

        mock_error_service.execute.assert_called_once()
        call_args = mock_error_service.execute.call_args
        dto = call_args[0][0]

        assert isinstance(dto, ErrorEventDTO)
        assert dto.exception_type == "LokiAlert:TestAlert"
        assert "TestAlert" in dto.message
        assert dto.context["alert_name"] == "TestAlert"
        assert dto.context["severity"] == "unknown"
        assert dto.context["status"] == "firing"

    @pytest.mark.asyncio
    async def test_process_alert_full_data(self, processor, mock_error_service):
        """Test alert processing with full data."""
        alert = {
            "labels": {
                "alertname": "HighCPU",
                "severity": "critical",
                "instance": "server-1",
            },
            "annotations": {
                "description": "CPU usage is above 90%",
                "summary": "High CPU detected",
            },
            "status": "firing",
            "startsAt": "2024-01-01T12:00:00Z",
            "endsAt": "2024-01-01T12:05:00Z",
        }

        await processor.process_alert(alert)

        mock_error_service.execute.assert_called_once()
        call_args = mock_error_service.execute.call_args
        dto = call_args[0][0]

        assert dto.exception_type == "LokiAlert:HighCPU"
        assert "[CRITICAL]" in dto.message
        assert "HighCPU" in dto.message
        assert "CPU usage is above 90%" in dto.message
        assert dto.context["severity"] == "critical"
        assert dto.context["starts_at"] == "2024-01-01T12:00:00Z"
        assert dto.context["ends_at"] == "2024-01-01T12:05:00Z"
        assert dto.context["labels"]["instance"] == "server-1"

    @pytest.mark.asyncio
    async def test_process_alert_no_labels(self, processor, mock_error_service):
        """Test alert processing without labels."""
        alert = {
            "labels": {},
            "annotations": {},
            "status": "firing",
        }

        await processor.process_alert(alert)

        mock_error_service.execute.assert_called_once()
        call_args = mock_error_service.execute.call_args
        dto = call_args[0][0]

        assert dto.exception_type == "LokiAlert:Unknown Alert"
        assert dto.context["alert_name"] == "Unknown Alert"

    @pytest.mark.asyncio
    async def test_process_alert_no_annotations(self, processor, mock_error_service):
        """Test alert processing without annotations."""
        alert = {
            "labels": {"alertname": "TestAlert"},
            "annotations": {},
            "status": "firing",
        }

        await processor.process_alert(alert)

        call_args = mock_error_service.execute.call_args
        dto = call_args[0][0]

        assert "No description" in dto.message

    @pytest.mark.asyncio
    async def test_process_alert_no_status(self, processor, mock_error_service):
        """Test alert processing without status."""
        alert = {
            "labels": {"alertname": "TestAlert"},
            "annotations": {"description": "Test"},
        }

        await processor.process_alert(alert)

        call_args = mock_error_service.execute.call_args
        dto = call_args[0][0]

        assert dto.context["status"] == "unknown"

    @pytest.mark.asyncio
    async def test_process_alert_with_summary(self, processor, mock_error_service):
        """Test alert processing with summary."""
        alert = {
            "labels": {"alertname": "TestAlert", "severity": "warning"},
            "annotations": {
                "description": "Something happened",
                "summary": "Brief summary",
            },
            "status": "firing",
        }

        await processor.process_alert(alert)

        call_args = mock_error_service.execute.call_args
        dto = call_args[0][0]

        assert "[WARNING]" in dto.message
        assert "Brief summary" in dto.message

    @pytest.mark.asyncio
    async def test_process_alert_error_handling(self, mock_error_service):
        """Test error handling during processing."""
        processor = LokiAlertProcessor(mock_error_service)
        mock_error_service.execute.side_effect = Exception("Processing failed")

        alert = {
            "labels": {"alertname": "TestAlert"},
            "annotations": {},
            "status": "firing",
        }

        # Should raise exception
        with pytest.raises(Exception, match="Processing failed"):
            await processor.process_alert(alert)

    @pytest.mark.asyncio
    async def test_process_alerts_empty_list(self, processor, mock_error_service):
        """Test processing empty alert list."""
        result = await processor.process_alerts([])

        assert result["processed"] == 0
        assert result["failed"] == 0
        mock_error_service.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_alerts_single_success(self, processor, mock_error_service):
        """Test processing single successful alert."""
        alerts = [
            {
                "labels": {"alertname": "Alert1"},
                "annotations": {"description": "Test"},
                "status": "firing",
            }
        ]

        result = await processor.process_alerts(alerts)

        assert result["processed"] == 1
        assert result["failed"] == 0
        mock_error_service.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_alerts_multiple_success(self, processor, mock_error_service):
        """Test processing multiple successful alerts."""
        alerts = [
            {
                "labels": {"alertname": "Alert1"},
                "annotations": {"description": "Test 1"},
                "status": "firing",
            },
            {
                "labels": {"alertname": "Alert2"},
                "annotations": {"description": "Test 2"},
                "status": "firing",
            },
            {
                "labels": {"alertname": "Alert3"},
                "annotations": {"description": "Test 3"},
                "status": "firing",
            },
        ]

        result = await processor.process_alerts(alerts)

        assert result["processed"] == 3
        assert result["failed"] == 0
        assert mock_error_service.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_process_alerts_mixed_results(self, processor, mock_error_service):
        """Test processing with partial failures."""
        alerts = [
            {
                "labels": {"alertname": "Alert1"},
                "annotations": {"description": "Test 1"},
                "status": "firing",
            },
            {
                "labels": {"alertname": "Alert2"},
                "annotations": {"description": "Test 2"},
                "status": "firing",
            },
            {
                "labels": {"alertname": "Alert3"},
                "annotations": {"description": "Test 3"},
                "status": "firing",
            },
        ]

        # Second alert fails
        mock_error_service.execute.side_effect = [None, Exception("Failed"), None]

        result = await processor.process_alerts(alerts)

        assert result["processed"] == 2
        assert result["failed"] == 1
        assert mock_error_service.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_process_alerts_all_failed(self, processor, mock_error_service):
        """Test processing where all alerts failed."""
        alerts = [
            {
                "labels": {"alertname": "Alert1"},
                "annotations": {"description": "Test 1"},
                "status": "firing",
            },
            {
                "labels": {"alertname": "Alert2"},
                "annotations": {"description": "Test 2"},
                "status": "firing",
            },
        ]

        mock_error_service.execute.side_effect = Exception("Always failed")

        result = await processor.process_alerts(alerts)

        assert result["processed"] == 0
        assert result["failed"] == 2

    @pytest.mark.asyncio
    async def test_process_alerts_preserves_order(self, processor, mock_error_service):
        """Test order preservation."""
        alerts = [
            {
                "labels": {"alertname": "First"},
                "annotations": {"description": "1"},
                "status": "firing",
            },
            {
                "labels": {"alertname": "Second"},
                "annotations": {"description": "2"},
                "status": "firing",
            },
            {
                "labels": {"alertname": "Third"},
                "annotations": {"description": "3"},
                "status": "firing",
            },
        ]

        await processor.process_alerts(alerts)

        # Check call order
        calls = mock_error_service.execute.call_args_list
        assert len(calls) == 3

        first_dto = calls[0][0][0]
        second_dto = calls[1][0][0]
        third_dto = calls[2][0][0]

        assert "First" in first_dto.exception_type
        assert "Second" in second_dto.exception_type
        assert "Third" in third_dto.exception_type

    @pytest.mark.asyncio
    async def test_process_alert_with_complex_labels(self, processor, mock_error_service):
        """Test alert processing with complex labels."""
        alert = {
            "labels": {
                "alertname": "DatabaseError",
                "severity": "critical",
                "team": "backend",
                "environment": "production",
                "region": "us-east-1",
            },
            "annotations": {
                "description": "Database connection pool exhausted",
                "summary": "DB pool full",
            },
            "status": "firing",
        }

        await processor.process_alert(alert)

        call_args = mock_error_service.execute.call_args
        dto = call_args[0][0]

        assert dto.context["labels"]["team"] == "backend"
        assert dto.context["labels"]["environment"] == "production"
        assert dto.context["labels"]["region"] == "us-east-1"

    @pytest.mark.asyncio
    async def test_process_alert_with_complex_annotations(self, processor, mock_error_service):
        """Test alert processing with complex annotations."""
        alert = {
            "labels": {"alertname": "TestAlert", "severity": "high"},
            "annotations": {
                "description": "Detailed description",
                "summary": "Quick summary",
                "runbook_url": "https://runbooks.example.com/alert123",
                "dashboard_url": "https://grafana.example.com/dash/abc",
            },
            "status": "firing",
        }

        await processor.process_alert(alert)

        call_args = mock_error_service.execute.call_args
        dto = call_args[0][0]

        assert dto.context["annotations"]["runbook_url"] == "https://runbooks.example.com/alert123"
        assert dto.context["annotations"]["dashboard_url"] == "https://grafana.example.com/dash/abc"

    @pytest.mark.asyncio
    async def test_process_alerts_returns_correct_counts(self, processor, mock_error_service):
        """Test returning correct counts."""
        alerts = [
            {
                "labels": {"alertname": f"Alert{i}"},
                "annotations": {"description": f"Test {i}"},
                "status": "firing",
            }
            for i in range(10)
        ]

        # Every third fails
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise Exception("Every third fails")
            return None

        mock_error_service.execute.side_effect = side_effect

        result = await processor.process_alerts(alerts)

        assert result["processed"] == 7  # 10 - 3 = 7
        assert result["failed"] == 3
        assert result["processed"] + result["failed"] == len(alerts)

    @pytest.mark.asyncio
    async def test_process_alert_context_environment(self, processor, mock_error_service):
        """Test that context contains environment=loki."""
        alert = {
            "labels": {"alertname": "TestAlert"},
            "annotations": {"description": "Test"},
            "status": "firing",
        }

        await processor.process_alert(alert)

        call_args = mock_error_service.execute.call_args
        dto = call_args[0][0]

        assert dto.context["environment"] == "loki"

    @pytest.mark.asyncio
    async def test_process_alert_stack_trace_none(self, processor, mock_error_service):
        """Test that stack_trace=None for alerts."""
        alert = {
            "labels": {"alertname": "TestAlert"},
            "annotations": {"description": "Test"},
            "status": "firing",
        }

        await processor.process_alert(alert)

        call_args = mock_error_service.execute.call_args
        dto = call_args[0][0]

        assert dto.stack_trace is None


class TestLokiAlertProcessorIntegration:
    """Integration tests for LokiAlertProcessor."""

    @pytest.mark.asyncio
    async def test_full_alert_processing_workflow(self):
        """Test full alert processing workflow."""
        # Create real mock service
        mock_error_service = Mock()
        mock_error_service.execute = AsyncMock(return_value=None)

        processor = LokiAlertProcessor(mock_error_service)

        # Realistic alert from Grafana
        alert = {
            "labels": {
                "alertname": "HighErrorRate",
                "severity": "critical",
                "service": "api-gateway",
                "namespace": "production",
            },
            "annotations": {
                "description": "Error rate is above 5% for the last 5 minutes",
                "summary": "High error rate detected",
                "runbook": "https://wiki.example.com/high-error-rate",
            },
            "status": "firing",
            "startsAt": "2024-01-15T10:30:00Z",
            "endsAt": "0001-01-01T00:00:00Z",
        }

        await processor.process_alert(alert)

        # Assertions
        mock_error_service.execute.assert_called_once()
        call_args = mock_error_service.execute.call_args
        dto = call_args[0][0]

        assert isinstance(dto, ErrorEventDTO)
        assert dto.exception_type == "LokiAlert:HighErrorRate"
        assert "[CRITICAL]" in dto.message
        assert "HighErrorRate" in dto.message
        assert "Error rate is above 5%" in dto.message
        assert dto.context["labels"]["service"] == "api-gateway"
        assert dto.context["labels"]["namespace"] == "production"
        assert dto.context["starts_at"] == "2024-01-15T10:30:00Z"
