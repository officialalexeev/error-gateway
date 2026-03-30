"""Health check and metrics endpoints."""

from app.core.metrics import generate_metrics
from fastapi import APIRouter, Response

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/metrics")
async def metrics():
    """Metrics endpoint for Prometheus."""
    return Response(content=generate_metrics().decode("utf-8"), media_type="text/plain")
