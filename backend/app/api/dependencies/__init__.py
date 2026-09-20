"""Shared FastAPI dependencies: access to the app-wide agent manager, model
registry, model router, task router, RAG service, tool registry, sandbox
provider, local MCP client, and the lightweight in-memory activity feed.
"""

from app.api.dependencies.state import (
    get_agent_manager,
    get_app_settings,
    get_mcp_client,
    get_model_registry,
    get_model_router,
    get_rag_service,
    get_sandbox,
    get_task_router,
    get_tool_registry,
    record_activity,
)

__all__ = [
    "get_agent_manager",
    "get_app_settings",
    "get_mcp_client",
    "get_model_registry",
    "get_model_router",
    "get_rag_service",
    "get_sandbox",
    "get_task_router",
    "get_tool_registry",
    "record_activity",
]
