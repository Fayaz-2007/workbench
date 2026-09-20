"""POST /api/chat — runs the full pipeline for one message and returns a
structured response the frontend's chat UI can render directly (see
frontend/src/components/execution and .../chat):

    (Auto mode only) Task Router -> dispatch:
        "agent"           -> Agent Manager -> Model Router -> Provider
        "system_monitor"  -> LocalMCPClient -> LocalMCPServer -> get_system_status()
        "network_monitor" -> LocalMCPClient -> LocalMCPServer -> get_active_connections()
        "security_status" -> deterministic sovereignty/security status (no model)
        "orchestrator"    -> bounded multi-step assessment (system + network + RAG + model)

    system_monitor/network_monitor go through the local MCP tool layer
    (see `app/mcp_tools/`) — Segment 4. security_status/orchestrator are
    unchanged and still read `app/monitoring/` directly.

Manual mode (a concrete `agent_id`) skips the Task Router entirely —
behavior is byte-for-byte what Segment 2 shipped.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Request

from app.agents import monitor_responses, orchestrator
from app.agents.base import AgentExecutionResult, AgentTask, AttachmentRef, ExecutionContext
from app.agents.manager import AgentManager
from app.agents.task_router import TaskRouter
from app.api.dependencies import (
    get_agent_manager,
    get_app_settings,
    get_mcp_client,
    get_model_router,
    get_rag_service,
    get_sandbox,
    get_task_router,
    get_tool_registry,
    record_activity,
)
from app.core.config import Settings
from app.core.exceptions import InvalidRequestError
from app.mcp_tools import LocalMCPClient
from app.models.router import ModelRouter
from app.rag.service import RAGService
from app.sandbox.base import SandboxProvider
from app.schemas.chat import (
    AgentSummary,
    ChatRequest,
    ChatResponse,
    CitationOut,
    DeliverableOut,
    ExecutionInfo,
    ExecutionStepOut,
    RoutingInfo,
    TaskRoutingOut,
)
from app.tools.registry import ToolRegistry

router = APIRouter(tags=["chat"])

_TARGET_DISPLAY_NAMES = {
    "system_monitor": "System Monitor",
    "network_monitor": "Network Monitor",
    "security_status": "Security Status",
    "orchestrator": "Security Orchestrator",
}


def _is_auto(agent_id: str | None) -> bool:
    return agent_id is None or agent_id.strip().lower() in ("", "auto")


async def _dispatch_auto(
    selection_target: str,
    selection_agent_id: str,
    task: AgentTask,
    context: ExecutionContext,
    agent_manager: AgentManager,
    settings: Settings,
    mcp_client: LocalMCPClient,
) -> tuple[AgentExecutionResult, str, str]:
    """Runs whatever the Task Router selected. Returns (result, display_id, display_name)."""
    if selection_target == "system_monitor":
        result = await monitor_responses.build_system_monitor_result(mcp_client)
        return result, "system_monitor", _TARGET_DISPLAY_NAMES["system_monitor"]
    if selection_target == "network_monitor":
        result = await monitor_responses.build_network_monitor_result(mcp_client)
        return result, "network_monitor", _TARGET_DISPLAY_NAMES["network_monitor"]
    if selection_target == "security_status":
        return monitor_responses.build_security_status_result(settings), "security_status", _TARGET_DISPLAY_NAMES["security_status"]
    if selection_target == "orchestrator":
        result = await orchestrator.run_security_assessment(task, context)
        return result, "orchestrator", _TARGET_DISPLAY_NAMES["orchestrator"]

    agent_manager.validate(selection_agent_id)
    result = await agent_manager.execute(selection_agent_id, task, context)
    agent = agent_manager.get(selection_agent_id)
    return result, agent.id, agent.name


@router.post("/chat", response_model=ChatResponse)
async def send_chat_message(
    payload: ChatRequest,
    request: Request,
    agent_manager: AgentManager = Depends(get_agent_manager),
    task_router: TaskRouter = Depends(get_task_router),
    model_router: ModelRouter = Depends(get_model_router),
    rag_service: RAGService = Depends(get_rag_service),
    tool_registry: ToolRegistry = Depends(get_tool_registry),
    sandbox: SandboxProvider = Depends(get_sandbox),
    settings: Settings = Depends(get_app_settings),
    mcp_client: LocalMCPClient = Depends(get_mcp_client),
) -> ChatResponse:
    if not payload.message.strip() and not payload.attachments:
        raise InvalidRequestError("A message or at least one attachment is required.")

    task_attachments = [
        AttachmentRef(id=a.id, filename=a.filename, file_type=a.file_type, path=a.path)
        for a in (payload.attachments or [])
    ]

    conversation_id = payload.conversation_id or str(uuid4())
    task = AgentTask(message=payload.message, attachments=task_attachments)
    context = ExecutionContext(
        model_router=model_router,
        conversation_id=conversation_id,
        request_id=str(uuid4()),
        settings=settings,
        rag_service=rag_service,
        tool_registry=tool_registry,
        sandbox=sandbox,
    )

    task_routing_out: TaskRoutingOut | None = None

    if _is_auto(payload.agent_id):
        selection = task_router.select(payload.message, task_attachments)
        task_routing_out = TaskRoutingOut(
            target=selection.target, agent_id=selection.agent_id, reason=selection.reason, confidence=selection.confidence
        )
        result, display_agent_id, display_agent_name = await _dispatch_auto(
            selection.target, selection.agent_id, task, context, agent_manager, settings, mcp_client
        )
        for step in result.steps:
            if step.id == "selecting_agent" and not step.detail:
                step.detail = selection.reason
                break
        record_activity(request, action=f"Auto-routed to {display_agent_name}", resource=display_agent_name)
    else:
        agent_manager.validate(payload.agent_id)  # raises AgentNotFoundError if unknown
        result = await agent_manager.execute(payload.agent_id, task, context)
        agent = agent_manager.get(payload.agent_id)
        display_agent_id, display_agent_name = agent.id, agent.name
        record_activity(request, action="Started conversation", resource=agent.name)

    return ChatResponse(
        conversation_id=conversation_id,
        agent=AgentSummary(id=display_agent_id, name=display_agent_name),
        task_routing=task_routing_out,
        routing=RoutingInfo(
            model_id=result.routing.model.id,
            reason=result.routing.reason,
            score=result.routing.score,
        ),
        response=result.response_text,
        execution=ExecutionInfo(
            status=result.status.value,
            steps=[ExecutionStepOut(id=s.id, title=s.title, status=s.status.value, detail=s.detail) for s in result.steps],
        ),
        citations=[CitationOut(id=c.id, label=c.label, source=c.source) for c in result.citations],
        deliverables=[
            DeliverableOut(id=d.id, filename=d.filename, file_type=d.file_type, size_bytes=d.size_bytes, status=d.status)
            for d in result.deliverables
        ],
    )
