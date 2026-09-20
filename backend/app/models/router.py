"""The Model Router — selects the best approved model for a task.

This is the piece that makes it possible to add new open-weight models
without redesigning the application: agents never name a model. They ask
the router for the best model matching a set of *capabilities*, and the
router scores every eligible, currently-registered model against the
request.

`score()` is an internal routing heuristic, not a benchmark accuracy score.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.exceptions import NoSuitableModelError
from app.core.logging import get_logger, log_event
from app.models.base import ModelInfo, ModelType, ResourceClass
from app.models.registry import ModelRegistry

logger = get_logger(__name__)

# Scoring weights. Kept as named constants (rather than magic numbers
# scattered through `_score`) so the routing behavior is easy to tune later
# without touching the algorithm's shape.
WEIGHT_CAPABILITY_MATCH = 0.50
WEIGHT_TYPE_MATCH = 0.15
WEIGHT_RESOURCE_FIT = 0.20
WEIGHT_CONTEXT_LENGTH = 0.10
WEIGHT_PRIORITY = 0.05

# Used to normalize context_length into a 0..1 score. Not a hard cap.
_CONTEXT_LENGTH_REFERENCE = 32_768
_PRIORITY_REFERENCE = 10


@dataclass
class RoutingRequest:
    agent_id: str
    required_capabilities: list[str] = field(default_factory=list)
    preferred_type: ModelType | None = None
    resource_constraint: ResourceClass | None = None
    task_excerpt: str = ""


@dataclass
class ScoredCandidate:
    model: ModelInfo
    score: float
    capability_matches: list[str]


@dataclass
class RoutingResult:
    model: ModelInfo
    reason: str
    score: float
    candidates_considered: int


def _capability_score(model: ModelInfo, required: list[str]) -> tuple[float, list[str]]:
    if not required:
        return 1.0, []
    matched = [cap for cap in required if model.has_capability(cap)]
    return len(matched) / len(required), matched


def _type_score(model: ModelInfo, preferred_type: ModelType | None) -> float:
    if preferred_type is None:
        return 0.5  # neutral — no type preference expressed
    return 1.0 if model.type == preferred_type else 0.0


def _resource_score(model: ModelInfo, server_class: ResourceClass) -> float:
    diff = model.resource_class.rank - server_class.rank
    if diff <= 0:
        # Fits comfortably; an exact match is marginally preferred over a
        # smaller-than-necessary model (which may be under-powered).
        return 1.0 if diff == 0 else 0.9
    # Larger than this server's class: still usable in principle, but
    # increasingly penalized the further it exceeds the server's tier.
    return max(0.0, 1.0 - 0.4 * diff)


def _context_length_score(model: ModelInfo) -> float:
    return min(1.0, model.context_length / _CONTEXT_LENGTH_REFERENCE)


def _priority_score(model: ModelInfo) -> float:
    return max(0.0, min(1.0, model.priority / _PRIORITY_REFERENCE))


def score(
    model: ModelInfo,
    request: RoutingRequest,
    *,
    server_class: ResourceClass,
) -> ScoredCandidate:
    """Scores one model against a routing request. Higher is better."""
    cap_score, matched = _capability_score(model, request.required_capabilities)
    total = (
        WEIGHT_CAPABILITY_MATCH * cap_score
        + WEIGHT_TYPE_MATCH * _type_score(model, request.preferred_type)
        + WEIGHT_RESOURCE_FIT * _resource_score(model, request.resource_constraint or server_class)
        + WEIGHT_CONTEXT_LENGTH * _context_length_score(model)
        + WEIGHT_PRIORITY * _priority_score(model)
    )
    return ScoredCandidate(model=model, score=round(total, 4), capability_matches=matched)


def _reason(candidate: ScoredCandidate, request: RoutingRequest) -> str:
    if request.required_capabilities:
        if candidate.capability_matches:
            return (
                f"Matched {len(candidate.capability_matches)}/{len(request.required_capabilities)} "
                f"required capabilities ({', '.join(candidate.capability_matches)}) at "
                f"{candidate.model.resource_class.value} resource class."
            )
        return "No exact capability match; selected as the closest available candidate."
    return f"No specific capability required; selected {candidate.model.id} as the best general fit."


class ModelRouter:
    """Evaluates registered models and selects the best candidate for a task."""

    def __init__(self, registry: ModelRegistry, server_resource_class: ResourceClass) -> None:
        self._registry = registry
        self._server_resource_class = server_resource_class

    def route(self, request: RoutingRequest) -> RoutingResult:
        log_event(
            logger,
            "model_routing_started",
            agent_id=request.agent_id,
            required_capabilities=request.required_capabilities,
        )

        eligible = self._registry.find_by_capabilities(request.required_capabilities)
        if not eligible:
            log_event(
                logger,
                "model_routing_failed",
                agent_id=request.agent_id,
                required_capabilities=request.required_capabilities,
            )
            raise NoSuitableModelError(
                "No approved, available model provides the required capabilities.",
                agent_id=request.agent_id,
                required_capabilities=request.required_capabilities,
            )

        scored = [self._score_model(m, request) for m in eligible]
        scored.sort(key=lambda c: c.score, reverse=True)
        best = scored[0]

        result = RoutingResult(
            model=best.model,
            reason=_reason(best, request),
            score=best.score,
            candidates_considered=len(scored),
        )
        log_event(
            logger,
            "model_selected",
            agent_id=request.agent_id,
            model_id=best.model.id,
            score=best.score,
            candidates_considered=len(scored),
        )
        return result

    def _score_model(self, model: ModelInfo, request: RoutingRequest) -> ScoredCandidate:
        return score(model, request, server_class=self._server_resource_class)
