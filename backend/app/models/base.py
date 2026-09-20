"""Model metadata and the inference-provider abstraction.

Two distinct concerns live here, deliberately kept apart:

- `ModelInfo` — metadata about a model (capabilities, resource footprint,
  status). The registry stores these; the router scores them. No inference
  happens through a `ModelInfo` alone.
- `BaseModelProvider` — the abstraction that actually talks to an inference
  runtime (`generate` / `stream` / `health_check`). Segment 2 ships exactly
  one implementation, `LocalModelProvider` (see `providers/local.py`), which
  returns clearly-labeled mock text. Ollama / llama.cpp / vLLM providers can
  be added later by implementing this same interface — agents and the
  router never change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from enum import StrEnum

from pydantic import BaseModel, Field


class ModelType(StrEnum):
    GENERAL = "general"
    CODE = "code"
    VISION = "vision"
    DATA = "data"
    EMBEDDING = "embedding"


class ResourceClass(StrEnum):
    """Coarse hardware footprint tier. Ranked tiny < small < medium < large."""

    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

    @property
    def rank(self) -> int:
        return {"tiny": 0, "small": 1, "medium": 2, "large": 3}[self.value]


class ModelStatus(StrEnum):
    """Mirrors the frontend's ModelStatus vocabulary (see
    frontend/src/types/admin.ts) so the admin UI needs no translation layer.
    """

    ACTIVE = "active"
    IDLE = "idle"
    LOADING = "loading"
    ERROR = "error"
    DISABLED = "disabled"


class ModelInfo(BaseModel):
    """Metadata-only description of a model the router can select.

    Registering a model here does not download or load any weights — see
    `models/README.md` at the repo root.
    """

    id: str
    name: str
    type: ModelType
    identifier: str
    capabilities: list[str] = Field(default_factory=list)
    context_length: int = Field(gt=0)
    quantization: str
    resource_class: ResourceClass
    status: ModelStatus
    version: str = "0.0.0"
    provider: str = "local"
    priority: int = 0

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities

    def is_selectable(self) -> bool:
        return self.status in (ModelStatus.ACTIVE, ModelStatus.IDLE)


class GenerationResult(BaseModel):
    """What a provider hands back for a single (non-streaming) generation."""

    text: str
    model_id: str
    is_mock: bool = True
    latency_ms: float = 0.0


class ProviderHealth(BaseModel):
    healthy: bool
    detail: str = ""


class BaseModelProvider(ABC):
    """Inference backend abstraction. One instance can serve many models."""

    name: str = "base"

    @abstractmethod
    async def generate(
        self, *, model: ModelInfo, prompt: str, images: list[bytes] | None = None
    ) -> GenerationResult:
        """Runs a single, non-streaming generation against `model`.

        `images` is raw image bytes (not base64/data-URI) for multimodal
        requests — optional and ignored by every text-only provider. Only a
        vision-capable provider (see `providers/ollama_vision.py`) actually
        forwards it to the inference runtime.
        """
        raise NotImplementedError

    @abstractmethod
    async def stream(self, *, model: ModelInfo, prompt: str) -> AsyncIterator[str]:
        """Yields text chunks as they become available.

        Not wired to an API route yet (Segment 2 is request/response only);
        the interface exists so a real provider can support streaming
        without an Agent API change later.
        """
        raise NotImplementedError
        yield  # pragma: no cover - makes this an async generator

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        raise NotImplementedError
