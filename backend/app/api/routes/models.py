"""GET/POST /api/models, DELETE /api/models/{model_id} — model registry CRUD.

Registration is metadata-only: nothing here downloads, loads, or validates
real model weights (see `models/README.md`).
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_model_registry, record_activity
from app.models.base import ModelInfo
from app.models.registry import ModelRegistry
from app.schemas.model import ModelCreateRequest, ModelDeleteResponse, ModelOut

router = APIRouter(tags=["models"])


@router.get("/models", response_model=list[ModelOut])
def list_models(registry: ModelRegistry = Depends(get_model_registry)) -> list[ModelOut]:
    return registry.list()


@router.post("/models", response_model=ModelOut)
def create_model(
    payload: ModelCreateRequest,
    request: Request,
    registry: ModelRegistry = Depends(get_model_registry),
) -> ModelOut:
    capabilities = [c.strip() for c in payload.capabilities.split(",") if c.strip()]
    model = ModelInfo(
        id=f"{payload.type.value}-{uuid4().hex[:8]}",
        name=payload.name,
        type=payload.type,
        identifier=payload.identifier,
        capabilities=capabilities,
        context_length=payload.context_length,
        quantization=payload.quantization,
        # No weights are installed, so a real resource footprint can't be
        # evaluated yet — this server's own class is the safest default.
        resource_class="small",
        status=payload.status,
    )
    registry.register(model)
    record_activity(request, action="Registered model", resource=model.name)
    return model


@router.delete("/models/{model_id}", response_model=ModelDeleteResponse)
def delete_model(
    model_id: str,
    request: Request,
    registry: ModelRegistry = Depends(get_model_registry),
) -> ModelDeleteResponse:
    model = registry.get(model_id)
    registry.remove(model_id)
    record_activity(request, action="Removed model", resource=model.name)
    return ModelDeleteResponse(id=model_id)
