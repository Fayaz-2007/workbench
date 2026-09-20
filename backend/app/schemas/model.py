"""API schemas for model registry endpoints.

`ModelInfo` (the registry's own record type) already matches what we want
to return to clients, so it doubles as the response schema — re-exported
here as `ModelOut` for a stable import path from `app.schemas`. The
request side is different enough (free-text capabilities from the Add
Model form, no id, no version) to warrant its own schema.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.base import ModelInfo as ModelOut
from app.models.base import ModelStatus, ModelType

__all__ = ["ModelOut", "ModelCreateRequest", "ModelDeleteResponse"]


class ModelCreateRequest(BaseModel):
    """Shape sent by the Admin "Add Model" form.

    Metadata-only: registering a model here never downloads or loads any
    weights (see `models/README.md`).
    """

    name: str = Field(min_length=1)
    type: ModelType
    identifier: str = Field(min_length=1)
    # Free-text, comma-separated (matches the frontend form field exactly);
    # parsed into a capability list by the route handler.
    capabilities: str = ""
    context_length: int = Field(gt=0)
    quantization: str = Field(min_length=1)
    status: ModelStatus = ModelStatus.DISABLED


class ModelDeleteResponse(BaseModel):
    id: str
    status: str = "deleted"
