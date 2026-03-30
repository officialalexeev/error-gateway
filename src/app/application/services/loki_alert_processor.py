"""Process Grafana Loki alerts and convert to error events."""

from app.application.dto.dto import ErrorEventDTO
from app.application.use_cases.use_cases import ProcessErrorUseCase
from app.core.logger import log


class LokiAlertProcessor:
    """Process Grafana Loki alerts and convert to error events."""

    def __init__(self, use_case: ProcessErrorUseCase):
        """Initialize processor with error processing use case."""
        self.use_case = use_case

    async def process_alert(self, alert: dict) -> None:
        """Process a single alert."""
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        status = alert.get("status", "unknown")

        alert_name = labels.get("alertname", "Unknown Alert")
        severity = labels.get("severity", "unknown")
        description = annotations.get("description", "No description")
        summary = annotations.get("summary", "")

        message = f"[{severity.upper()}] {alert_name}: {description}"
        if summary:
            message += f" - {summary}"

        context = {
            "alert_name": alert_name,
            "severity": severity,
            "status": status,
            "labels": labels,
            "annotations": annotations,
            "environment": "loki",
        }

        if "startsAt" in alert:
            context["starts_at"] = alert["startsAt"]
        if "endsAt" in alert:
            context["ends_at"] = alert["endsAt"]

        dto = ErrorEventDTO(
            message=message,
            exception_type=f"LokiAlert:{alert_name}",
            stack_trace=None,
            context=context,
        )

        try:
            await self.use_case.execute(dto)
            log.info(
                "Processed Loki alert",
                extra={
                    "alert_name": alert_name,
                    "severity": severity,
                    "event": "loki_alert_processed",
                },
            )
        except Exception as e:
            log.error(
                f"Failed to process Loki alert {alert_name}: {e}",
                extra={
                    "alert_name": alert_name,
                    "severity": severity,
                    "event": "loki_alert_failed",
                    "error": str(e),
                },
            )
            raise

    async def process_alerts(self, alerts: list[dict]) -> dict:
        """Process multiple alerts."""
        if not alerts:
            log.debug("No alerts to process")
            return {"processed": 0, "failed": 0}

        processed = 0
        failed = 0

        for alert in alerts:
            try:
                await self.process_alert(alert)
                processed += 1
            except Exception:
                failed += 1

        log.info(
            f"Loki alert processing complete: {processed} processed, {failed} failed",
            extra={
                "event": "loki_alert_processing_complete",
                "processed_count": processed,
                "failed_count": failed,
                "total_count": len(alerts),
            },
        )

        return {"processed": processed, "failed": failed}
