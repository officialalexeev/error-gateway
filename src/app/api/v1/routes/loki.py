"""Grafana Loki webhook endpoint."""

from app.api.v1.dependencies import get_loki_alert_processor
from app.api.v1.schemas.loki import LokiWebhookSchemaV1
from app.application.services.loki_alert_processor import LokiAlertProcessor
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/loki")


@router.post("/webhook")
async def loki_webhook(
    webhook: LokiWebhookSchemaV1,
    processor: LokiAlertProcessor = Depends(get_loki_alert_processor),
) -> dict:
    """Grafana Loki webhook for receiving alerts."""
    result = await processor.process_alerts(webhook.alerts)

    return {
        "status": "ok",
        "processed": result["processed"],
        "failed": result["failed"],
    }
