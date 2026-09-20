"""Application-wide singletons and the dependency functions that expose
them to route handlers.

The agent manager and model registry are constructed once, in the FastAPI
lifespan (see `app/main.py`), and stored on `app.state`. Building a fresh
`ModelRouter` per request is intentionally cheap (it just wraps the
registry + the server's configured resource class) so there is no
router-level state to reset between requests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from fastapi import Request

from app.agents.manager import AgentManager
from app.agents.task_router import TaskRouter
from app.core.config import Settings, get_settings
from app.mcp_tools import LocalMCPClient
from app.models.base import ResourceClass
from app.models.registry import ModelRegistry
from app.models.router import ModelRouter
from app.rag.service import RAGService
from app.sandbox.base import SandboxProvider
from app.tools.registry import ToolRegistry

_MAX_ACTIVITY_ENTRIES = 20


def get_agent_manager(request: Request) -> AgentManager:
    return request.app.state.agent_manager


def get_model_registry(request: Request) -> ModelRegistry:
    return request.app.state.model_registry


def get_model_router(request: Request) -> ModelRouter:
    registry = get_model_registry(request)
    settings = get_settings()
    return ModelRouter(registry, ResourceClass(settings.server_resource_class))


def get_task_router(request: Request) -> TaskRouter:
    # Cheap to construct (just wraps the agent manager) — no need to cache
    # on app.state the way the agent manager/model registry are.
    return TaskRouter(get_agent_manager(request))


def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag_service


def get_tool_registry(request: Request) -> ToolRegistry:
    return request.app.state.tool_registry


def get_sandbox(request: Request) -> SandboxProvider:
    return request.app.state.sandbox


def get_mcp_client(request: Request) -> LocalMCPClient:
    return request.app.state.mcp_client


def get_app_settings() -> Settings:
    return get_settings()


def record_activity(
    request: Request,
    action: str,
    resource: str,
    status: Literal["success", "failure", "pending"] = "success",
) -> None:
    """Appends to a small in-memory feed backing the Admin Overview page.

    This is intentionally not a real audit log (no persistence, no user
    identity beyond the single dev session) — that belongs to the
    security/audit layer in a later segment.
    """
    entry = {
        "id": str(uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action,
        "resource": resource,
        "status": status,
    }
    log: list[dict] = request.app.state.activity_log
    log.insert(0, entry)
    del log[_MAX_ACTIVITY_ENTRIES:]
