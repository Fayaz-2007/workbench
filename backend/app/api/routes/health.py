"""GET /api/health — liveness check."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health_check() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "environment": settings.environment}
