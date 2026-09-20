"""GET /api/admin/overview, GET /api/admin/models — Admin Dashboard data.

Only what this segment actually backs. The Admin Network, System, and
Audit Logs pages keep using frontend mock data until a later segment adds
real telemetry, network monitoring, and audit logging.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_model_registry
from app.models.base import ModelStatus
from app.models.registry import ModelRegistry
from app.schemas.admin import ActivityEntry, AdminOverview
from app.schemas.model import ModelOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview", response_model=AdminOverview)
def get_overview(request: Request, registry: ModelRegistry = Depends(get_model_registry)) -> AdminOverview:
    models = registry.list()
    activity: list[dict] = request.app.state.activity_log
    return AdminOverview(
        models_online=sum(1 for m in models if m.status == ModelStatus.ACTIVE),
        models_total=len(models),
        active_sessions=1,
        recent_activity=[ActivityEntry(**entry) for entry in activity],
    )


@router.get("/models", response_model=list[ModelOut])
def get_admin_models(registry: ModelRegistry = Depends(get_model_registry)) -> list[ModelOut]:
    return registry.list()
