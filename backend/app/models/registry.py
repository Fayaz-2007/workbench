"""In-memory model registry.

Owns model *metadata* only — it never performs inference (see
`models/providers/` for that). Responsibilities: register, remove, list,
retrieve, enable/disable, and answer capability-matching queries for the
router.

This is intentionally a plain in-memory store (a dict behind a small class)
rather than a database-backed one — `app/database/` is reserved for a real
persistence layer in a later segment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.exceptions import ModelNotFoundError
from app.core.logging import get_logger, log_event
from app.models.base import ModelInfo, ModelStatus, ModelType, ResourceClass

if TYPE_CHECKING:
    from app.core.config import Settings

logger = get_logger(__name__)


def default_dev_models() -> list[ModelInfo]:
    """The Segment 2 development model set.

    Metadata-only mock registrations — none of these are real model
    weights. They exist to prove the routing architecture works: Code Agent
    routes to `code-small`, Document/General Agent to `general-small`,
    Vision Agent to `vision-small`, Data Agent to `data-small`, purely
    through capability matching (see `models/router.py`), never by
    hard-coded agent → model name lookups.
    """
    return [
        ModelInfo(
            id="general-small",
            name="Local General Small",
            type=ModelType.GENERAL,
            identifier="dev-mock/general-small",
            capabilities=[
                "reasoning",
                "text_generation",
                "question_answering",
                "document_analysis",
                "summarization",
                "information_extraction",
            ],
            context_length=8192,
            quantization="4bit",
            resource_class=ResourceClass.SMALL,
            status=ModelStatus.ACTIVE,
        ),
        ModelInfo(
            id="code-small",
            name="Local Code Small",
            type=ModelType.CODE,
            identifier="dev-mock/code-small",
            capabilities=["coding", "debugging", "code_generation", "code_reasoning"],
            context_length=16384,
            quantization="4bit",
            resource_class=ResourceClass.SMALL,
            status=ModelStatus.ACTIVE,
        ),
        ModelInfo(
            id="vision-small",
            name="Local Vision Small",
            type=ModelType.VISION,
            identifier="dev-mock/vision-small",
            capabilities=["image_understanding", "multimodal", "visual_reasoning"],
            context_length=4096,
            quantization="4bit",
            resource_class=ResourceClass.SMALL,
            status=ModelStatus.ACTIVE,
        ),
        ModelInfo(
            id="data-small",
            name="Local Data Small",
            type=ModelType.DATA,
            identifier="dev-mock/data-small",
            capabilities=["data_analysis", "tabular_reasoning", "statistics"],
            context_length=8192,
            quantization="4bit",
            resource_class=ResourceClass.SMALL,
            status=ModelStatus.ACTIVE,
        ),
    ]


def ollama_dev_models(settings: "Settings") -> list[ModelInfo]:
    """Real, Ollama-served models — registered only when `MODEL_PROVIDER=
    ollama` (see `app/main.py` lifespan and `app/core/config.py`).

    Deliberately **not** part of `default_dev_models()`: the test suite
    constructs `ModelRegistry()` (and boots the app) with the default
    `model_provider="mock"`, so these never appear in automated tests
    regardless of whether Ollama happens to be running on the host —
    routing stays 100% deterministic there. When a developer opts in via
    `.env`, the same underlying model is registered under three
    capability-scoped entries so it can compete fairly for General, Code,
    and Data agent requests (no vision entry: this text model has no
    real multimodal capability, and Segment 3 never mislabels a text
    model as vision-capable).
    """
    identifier = settings.ollama_model
    shared = dict(
        identifier=identifier,
        quantization="Q4_K_M",
        context_length=32768,
        resource_class=ResourceClass.SMALL,
        status=ModelStatus.ACTIVE,
        provider="ollama",
        version=identifier.split(":")[-1] if ":" in identifier else "latest",
    )
    return [
        ModelInfo(
            id="ollama-general",
            name=f"Ollama · {identifier} (general)",
            type=ModelType.GENERAL,
            capabilities=[
                "reasoning",
                "text_generation",
                "question_answering",
                "document_analysis",
                "summarization",
                "information_extraction",
            ],
            **shared,
        ),
        ModelInfo(
            id="ollama-code",
            name=f"Ollama · {identifier} (code)",
            type=ModelType.CODE,
            capabilities=["coding", "debugging", "code_generation", "code_reasoning"],
            **shared,
        ),
        ModelInfo(
            id="ollama-data",
            name=f"Ollama · {identifier} (data)",
            type=ModelType.DATA,
            capabilities=["data_analysis", "tabular_reasoning", "statistics"],
            **shared,
        ),
    ]


def ollama_vision_models(settings: "Settings") -> list[ModelInfo]:
    """The real, Ollama-served vision model — registered only when
    `VISION_MODEL_PROVIDER=ollama` (see `app/main.py` lifespan and
    `app/core/config.py`).

    Kept entirely separate from `ollama_dev_models()`: the text model has
    no multimodal capability, and this entry is served through the
    dedicated `ollama_vision` provider (see
    `app/models/providers/ollama_vision.py`) so attached image bytes
    actually reach Ollama's `images` field — never a text-only call
    mislabeled as vision understanding.
    """
    identifier = settings.vision_model
    return [
        ModelInfo(
            id="ollama-vision",
            name=f"Ollama · {identifier} (vision)",
            type=ModelType.VISION,
            identifier=identifier,
            capabilities=["image_understanding", "multimodal", "visual_reasoning"],
            quantization="Q4_K_M",
            context_length=32768,
            resource_class=ResourceClass.SMALL,
            status=ModelStatus.ACTIVE,
            provider="ollama_vision",
            version=identifier.split(":")[-1] if ":" in identifier else "latest",
        ),
    ]


class ModelRegistry:
    """In-memory store of `ModelInfo`, keyed by id."""

    def __init__(self, seed: bool = True) -> None:
        self._models: dict[str, ModelInfo] = {}
        if seed:
            for model in default_dev_models():
                self._models[model.id] = model

    def register(self, model: ModelInfo) -> ModelInfo:
        self._models[model.id] = model
        log_event(logger, "model_registered", model_id=model.id, model_type=model.type.value)
        return model

    def remove(self, model_id: str) -> None:
        if model_id not in self._models:
            raise ModelNotFoundError(f"Model '{model_id}' is not registered.", model_id=model_id)
        del self._models[model_id]
        log_event(logger, "model_removed", model_id=model_id)

    def get(self, model_id: str) -> ModelInfo:
        try:
            return self._models[model_id]
        except KeyError as exc:
            raise ModelNotFoundError(f"Model '{model_id}' is not registered.", model_id=model_id) from exc

    def list(self) -> list[ModelInfo]:
        return list(self._models.values())

    def set_status(self, model_id: str, status: ModelStatus) -> ModelInfo:
        model = self.get(model_id)
        updated = model.model_copy(update={"status": status})
        self._models[model_id] = updated
        log_event(logger, "model_status_changed", model_id=model_id, status=status.value)
        return updated

    def enable(self, model_id: str) -> ModelInfo:
        return self.set_status(model_id, ModelStatus.ACTIVE)

    def disable(self, model_id: str) -> ModelInfo:
        return self.set_status(model_id, ModelStatus.DISABLED)

    def find_by_capabilities(self, capabilities: list[str]) -> list[ModelInfo]:
        """Models that are selectable and share at least one capability.

        An empty `capabilities` list matches every selectable model — the
        router treats "no specific capability required" as "anything will
        do", not as "match nothing".
        """
        wanted = set(capabilities)
        return [
            model
            for model in self._models.values()
            if model.is_selectable() and (not wanted or wanted & set(model.capabilities))
        ]
