"""ModelRegistry: register, list, retrieve, remove, enable/disable, and
capability matching — exercised directly, without going through the API.
"""

from __future__ import annotations

import pytest

from app.core.exceptions import ModelNotFoundError
from app.models.base import ModelInfo, ModelStatus, ModelType, ResourceClass
from app.models.registry import ModelRegistry


def _make_model(model_id: str, **overrides: object) -> ModelInfo:
    defaults = dict(
        id=model_id,
        name=model_id,
        type=ModelType.GENERAL,
        identifier=f"dev-mock/{model_id}",
        capabilities=["reasoning"],
        context_length=4096,
        quantization="4bit",
        resource_class=ResourceClass.SMALL,
        status=ModelStatus.ACTIVE,
    )
    defaults.update(overrides)
    return ModelInfo(**defaults)


def test_registry_seeds_four_dev_models() -> None:
    registry = ModelRegistry()
    ids = {m.id for m in registry.list()}
    assert {"general-small", "code-small", "vision-small", "data-small"} <= ids


def test_register_and_get() -> None:
    registry = ModelRegistry(seed=False)
    model = _make_model("test-model")
    registry.register(model)
    assert registry.get("test-model") == model


def test_get_unknown_model_raises() -> None:
    registry = ModelRegistry(seed=False)
    with pytest.raises(ModelNotFoundError):
        registry.get("does-not-exist")


def test_remove_model() -> None:
    registry = ModelRegistry(seed=False)
    registry.register(_make_model("removable"))
    registry.remove("removable")
    with pytest.raises(ModelNotFoundError):
        registry.get("removable")


def test_remove_unknown_model_raises() -> None:
    registry = ModelRegistry(seed=False)
    with pytest.raises(ModelNotFoundError):
        registry.remove("does-not-exist")


def test_enable_disable() -> None:
    registry = ModelRegistry(seed=False)
    registry.register(_make_model("togglable", status=ModelStatus.DISABLED))
    assert registry.get("togglable").status == ModelStatus.DISABLED

    registry.enable("togglable")
    assert registry.get("togglable").status == ModelStatus.ACTIVE

    registry.disable("togglable")
    assert registry.get("togglable").status == ModelStatus.DISABLED


def test_find_by_capabilities_matches_overlap_only() -> None:
    registry = ModelRegistry(seed=False)
    registry.register(_make_model("coder", capabilities=["coding", "debugging"]))
    registry.register(_make_model("writer", capabilities=["reasoning", "summarization"]))

    matches = registry.find_by_capabilities(["coding"])
    assert [m.id for m in matches] == ["coder"]


def test_find_by_capabilities_excludes_unavailable_models() -> None:
    registry = ModelRegistry(seed=False)
    registry.register(_make_model("disabled-coder", capabilities=["coding"], status=ModelStatus.DISABLED))

    assert registry.find_by_capabilities(["coding"]) == []


def test_find_by_capabilities_empty_list_matches_everything_selectable() -> None:
    registry = ModelRegistry(seed=False)
    registry.register(_make_model("a", capabilities=["x"]))
    registry.register(_make_model("b", capabilities=["y"], status=ModelStatus.DISABLED))

    matches = registry.find_by_capabilities([])
    assert [m.id for m in matches] == ["a"]
