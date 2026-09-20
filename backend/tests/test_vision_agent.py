"""Vision Agent: real Ollama vision inference, kept fully offline/deterministic
in this suite via `httpx.MockTransport` — no real Ollama server is ever
contacted here (see `app/models/providers/ollama_vision.py`).

Covers: vision provider selection, missing-image handling, Ollama-unavailable
handling, the successful image request path, and that default/mock mode
(no `VISION_MODEL_PROVIDER=ollama`) is completely unchanged.
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest

from app.agents.base import AgentTask, AttachmentRef, ExecutionContext
from app.agents.vision import VisionAgent
from app.core.config import get_settings
from app.core.exceptions import ModelUnavailableError
from app.models.base import ModelType, ResourceClass
from app.models.registry import ModelRegistry, ollama_vision_models
from app.models.router import ModelRouter, RoutingRequest


def _client_with_transport(transport: httpx.MockTransport) -> type[httpx.AsyncClient]:
    """An `httpx.AsyncClient` subclass that always uses `transport`, so
    `OllamaVisionProvider`'s internal `httpx.AsyncClient(timeout=...)` calls
    hit a fake handler instead of a real network socket.
    """

    class _MockedAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs) -> None:
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    return _MockedAsyncClient


def _vision_registry_and_router(settings) -> ModelRouter:
    registry = ModelRegistry()  # seeds default mock models, including vision-small
    for model in ollama_vision_models(settings):
        registry.register(model)
    return ModelRouter(registry, server_resource_class=ResourceClass.SMALL)


# --------------------------------------------------------------------------
# 1. Vision provider selection
# --------------------------------------------------------------------------


def test_ollama_vision_models_uses_configured_identifier(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "vision_model", "qwen2.5vl:3b")

    models = ollama_vision_models(settings)

    assert len(models) == 1
    model = models[0]
    assert model.id == "ollama-vision"
    assert model.type == ModelType.VISION
    assert model.provider == "ollama_vision"
    assert model.identifier == "qwen2.5vl:3b"
    assert set(model.capabilities) == {"image_understanding", "multimodal", "visual_reasoning"}


def test_router_prefers_real_ollama_vision_model_when_registered(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "vision_model", "qwen2.5vl:3b")
    router = _vision_registry_and_router(settings)

    result = router.route(
        RoutingRequest(
            agent_id="vision",
            required_capabilities=VisionAgent.capabilities,
            preferred_type=ModelType.VISION,
        )
    )

    assert result.model.id == "ollama-vision"
    assert result.model.provider == "ollama_vision"


# --------------------------------------------------------------------------
# 2. Successful image request path
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vision_agent_sends_real_image_bytes_to_ollama(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "vision_model", "qwen2.5vl:3b")
    settings.upload_path.mkdir(parents=True, exist_ok=True)

    image_bytes = b"\x89PNG\r\n\x1a\nnot-a-real-png-but-real-bytes"
    stored_name = "abc123_photo.png"
    (settings.upload_path / stored_name).write_bytes(image_bytes)

    router = _vision_registry_and_router(settings)
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"response": "A red circle on a white background."})

    monkeypatch.setattr(
        "app.models.providers.ollama_vision.httpx.AsyncClient",
        _client_with_transport(httpx.MockTransport(handler)),
    )

    task = AgentTask(
        message="I need the content in the image.",
        attachments=[AttachmentRef(id="1", filename="photo.png", file_type="PNG Image", path=stored_name)],
    )
    context = ExecutionContext(model_router=router, conversation_id="c1", request_id="r1", settings=settings)

    result = await VisionAgent().execute(task, context)

    assert result.status.value == "completed"
    assert captured["payload"]["images"] == [base64.b64encode(image_bytes).decode("ascii")]
    assert "I need the content in the image." in captured["payload"]["prompt"]
    assert "A red circle on a white background." in result.response_text
    assert "Generated locally by" in result.response_text
    assert "development response" not in result.response_text.lower()
    assert "not yet implemented" not in result.response_text.lower()

    step_ids = [s.id for s in result.steps]
    assert step_ids == [
        "understanding_request",
        "selecting_agent",
        "selecting_model",
        "executing",
        "generating_response",
        "completed",
    ]


@pytest.mark.asyncio
async def test_vision_agent_ignores_non_image_attachments(monkeypatch) -> None:
    """A .pdf attached alongside/instead of an image must never be read as
    image bytes — only real png/jpg/jpeg attachments are sent to Ollama.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "vision_model", "qwen2.5vl:3b")
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    (settings.upload_path / "doc123_notes.pdf").write_bytes(b"%PDF-1.4 fake")

    task = AgentTask(
        message="what does this say?",
        attachments=[AttachmentRef(id="1", filename="notes.pdf", file_type="PDF Document", path="doc123_notes.pdf")],
    )
    router = _vision_registry_and_router(settings)
    context = ExecutionContext(model_router=router, conversation_id="c1", request_id="r1", settings=settings)

    images = await VisionAgent().resolve_images(task, context)

    assert images == []


# --------------------------------------------------------------------------
# 3. Missing image handling
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vision_agent_without_image_answers_as_text_only_no_crash(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "vision_model", "qwen2.5vl:3b")
    router = _vision_registry_and_router(settings)
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"response": "I can only answer generally without an image."})

    monkeypatch.setattr(
        "app.models.providers.ollama_vision.httpx.AsyncClient",
        _client_with_transport(httpx.MockTransport(handler)),
    )

    task = AgentTask(message="what is in this image?", attachments=[])
    context = ExecutionContext(model_router=router, conversation_id="c1", request_id="r1", settings=settings)

    result = await VisionAgent().execute(task, context)

    assert result.status.value == "completed"
    assert "images" not in captured["payload"]
    assert "No image attachment was found" in result.response_text
    assert "I can only answer generally without an image." in result.response_text


@pytest.mark.asyncio
async def test_vision_agent_resolve_images_without_settings_returns_empty() -> None:
    task = AgentTask(
        message="hi",
        attachments=[AttachmentRef(id="1", filename="photo.png", file_type="PNG Image", path="whatever.png")],
    )
    registry = ModelRegistry()
    router = ModelRouter(registry, server_resource_class=ResourceClass.SMALL)
    context = ExecutionContext(model_router=router, conversation_id="c1", request_id="r1", settings=None)

    images = await VisionAgent().resolve_images(task, context)

    assert images == []


# --------------------------------------------------------------------------
# 4. Ollama / vision model unavailable handling
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vision_agent_raises_clear_error_when_ollama_unreachable(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "vision_model", "qwen2.5vl:3b")
    router = _vision_registry_and_router(settings)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=request)

    monkeypatch.setattr(
        "app.models.providers.ollama_vision.httpx.AsyncClient",
        _client_with_transport(httpx.MockTransport(handler)),
    )

    task = AgentTask(message="describe this", attachments=[])
    context = ExecutionContext(model_router=router, conversation_id="c1", request_id="r1", settings=settings)

    with pytest.raises(ModelUnavailableError) as exc_info:
        await VisionAgent().execute(task, context)

    assert "Local vision model unavailable" in str(exc_info.value)
    assert "qwen2.5vl:3b" in str(exc_info.value)


@pytest.mark.asyncio
async def test_vision_agent_raises_clear_error_when_model_not_pulled(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "vision_model", "qwen2.5vl:3b")
    router = _vision_registry_and_router(settings)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    monkeypatch.setattr(
        "app.models.providers.ollama_vision.httpx.AsyncClient",
        _client_with_transport(httpx.MockTransport(handler)),
    )

    task = AgentTask(message="describe this", attachments=[])
    context = ExecutionContext(model_router=router, conversation_id="c1", request_id="r1", settings=settings)

    with pytest.raises(ModelUnavailableError) as exc_info:
        await VisionAgent().execute(task, context)

    assert "Local vision model unavailable" in str(exc_info.value)
    assert "ollama pull qwen2.5vl:3b" in str(exc_info.value)


# --------------------------------------------------------------------------
# 5. Mock/default mode is unchanged
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vision_agent_default_mock_mode_unchanged() -> None:
    """No VISION_MODEL_PROVIDER=ollama registration at all — Vision Agent
    must behave exactly as before: routed to the metadata-only mock model,
    clearly labeled as non-real.
    """
    registry = ModelRegistry()  # default seed only: vision-small, no ollama-vision
    router = ModelRouter(registry, server_resource_class=ResourceClass.SMALL)
    context = ExecutionContext(
        model_router=router, conversation_id="c1", request_id="r1", settings=get_settings()
    )
    task = AgentTask(message="what is in this image?", attachments=[])

    result = await VisionAgent().execute(task, context)

    assert result.routing.model.id == "vision-small"
    assert "Structured development response" in result.response_text
    assert "Real image/scanned-document understanding is not implemented yet" in result.response_text
