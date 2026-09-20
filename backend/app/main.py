"""Application entry point — Segment 3: real local AI platform.

Wires together the pieces described in `backend/README.md`:

    Browser Client -> FastAPI -> Agent Manager -> Selected Agent
        -> Model Router -> Model Provider (mock or real Ollama) -> Response

Segment 2 built the routing architecture behind a mock provider. Segment 3
adds a real local provider (Ollama, see app/models/providers/ollama.py),
local RAG, OCR, tools, sandboxed execution, and document generation — all
strictly local; nothing here calls an external AI API.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.manager import build_default_agent_manager
from app.api.routes import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger, log_event
from app.mcp_tools import build_local_mcp_client
from app.models.registry import ModelRegistry, ollama_dev_models, ollama_vision_models
from app.rag import build_rag_service
from app.sandbox.subprocess_provider import get_sandbox_provider
from app.tools import build_default_tool_registry

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


def _ensure_data_dirs() -> None:
    for path in (
        settings.upload_path,
        settings.documents_path,
        settings.generated_path,
        settings.chroma_resolved_path,
    ):
        path.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _ensure_data_dirs()

    app.state.agent_manager = build_default_agent_manager()
    app.state.model_registry = ModelRegistry()

    # Real, Ollama-served models are opt-in via MODEL_PROVIDER=ollama (see
    # app/core/config.py) so the automated test suite stays deterministic
    # regardless of what's running on the host. No live health check here
    # by design — startup stays fast/offline-safe; an unreachable Ollama
    # surfaces as a clean ModelUnavailableError on the first chat request
    # that needs it, not as a boot failure.
    if settings.model_provider == "ollama":
        for model in ollama_dev_models(settings):
            app.state.model_registry.register(model)

    # Separate opt-in from the text model above: Vision Agent gets a real,
    # Ollama-served multimodal model only when `VISION_MODEL_PROVIDER=ollama`
    # (see app/core/config.py) — independent of `MODEL_PROVIDER` so the two
    # can be toggled without affecting each other.
    if settings.vision_model_provider == "ollama":
        for model in ollama_vision_models(settings):
            app.state.model_registry.register(model)

    app.state.rag_service = build_rag_service(settings)
    app.state.tool_registry = build_default_tool_registry(app.state.rag_service)
    app.state.sandbox = get_sandbox_provider()
    app.state.mcp_client = build_local_mcp_client()

    app.state.activity_log = [
        {
            "id": "boot",
            "timestamp": datetime.now(UTC).isoformat(),
            "action": "Backend started",
            "resource": "Sovereign AI Workbench API",
            "status": "success",
        }
    ]
    log_event(
        logger,
        "backend_started",
        agents=len(app.state.agent_manager.list()),
        models=len(app.state.model_registry.list()),
        tools=len(app.state.tool_registry.list()),
        mcp_tools=len(app.state.mcp_client.list_tools()),
        resource_class=settings.server_resource_class,
        model_provider=settings.model_provider,
        vision_model_provider=settings.vision_model_provider,
        embedding_provider=settings.embedding_provider,
        sandbox_provider=app.state.sandbox.name,
    )
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "Self-hosted, air-gapped agentic AI workbench. Real local inference "
        "(Ollama), local RAG, OCR, tools, sandboxed code execution, and "
        "document generation — no external AI API is ever called."
    ),
    version="0.3.0",
    lifespan=lifespan,
)

# Never "*": the browser client is the only intended caller, and the LAN
# origin it runs from is explicit configuration (see .env.example), not a
# wildcard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)
