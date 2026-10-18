"""GET /health — liveness/readiness."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.services.graph_service import graph_service
from app.utils.time import format_iso8601, now_utc

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness / readiness probe")
async def health_check() -> dict:
    settings = get_settings()
    return {
        "status": "ok" if graph_service.loaded else "degraded",
        "version": settings.app_version,
        "graph_loaded": graph_service.loaded,
        "study_area": settings.study_area,
        "timestamp": format_iso8601(now_utc()),
        "disclaimer": (
            "CascadeIQ is a student datathon simulator. Values are not operational emergency data."
        ),
    }
