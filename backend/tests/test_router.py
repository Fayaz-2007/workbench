"""ModelRouter: capability-based scoring and selection, and the
no-suitable-model error path. Exercised directly against a fresh registry
so these tests don't depend on the API layer.
"""

from __future__ import annotations

import pytest

from app.core.exceptions import NoSuitableModelError
from app.models.base import ResourceClass
from app.models.registry import ModelRegistry
from app.models.router import ModelRouter, RoutingRequest


@pytest.fixture
def router() -> ModelRouter:
    return ModelRouter(ModelRegistry(), server_resource_class=ResourceClass.SMALL)


def test_routes_to_capability_matching_model(router: ModelRouter) -> None:
    result = router.route(RoutingRequest(agent_id="general", required_capabilities=["reasoning"]))
    assert result.model.id == "general-small"
    assert 0.0 < result.score <= 1.0
    assert result.reason


def test_code_agent_routes_to_code_model(router: ModelRouter) -> None:
    result = router.route(
        RoutingRequest(agent_id="code", required_capabilities=["coding", "debugging", "code_generation", "code_reasoning"])
    )
    assert result.model.id == "code-small"


def test_document_agent_routes_to_general_model(router: ModelRouter) -> None:
    result = router.route(
        RoutingRequest(agent_id="document", required_capabilities=["document_analysis", "summarization", "information_extraction"])
    )
    assert result.model.id == "general-small"


def test_vision_agent_routes_to_vision_model(router: ModelRouter) -> None:
    result = router.route(
        RoutingRequest(agent_id="vision", required_capabilities=["image_understanding", "multimodal", "visual_reasoning"])
    )
    assert result.model.id == "vision-small"


def test_data_agent_routes_to_data_model(router: ModelRouter) -> None:
    result = router.route(
        RoutingRequest(agent_id="data", required_capabilities=["data_analysis", "tabular_reasoning", "statistics"])
    )
    assert result.model.id == "data-small"


def test_no_suitable_model_raises(router: ModelRouter) -> None:
    with pytest.raises(NoSuitableModelError):
        router.route(RoutingRequest(agent_id="unknown-capability-agent", required_capabilities=["quantum_flux_capacitance"]))


def test_routing_ignores_disabled_models() -> None:
    registry = ModelRegistry()
    registry.disable("code-small")
    router = ModelRouter(registry, server_resource_class=ResourceClass.SMALL)

    with pytest.raises(NoSuitableModelError):
        router.route(RoutingRequest(agent_id="code", required_capabilities=["coding"]))
