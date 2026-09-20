"""The agent abstraction.

An agent is task-oriented *behavior*, not a model. It declares what it's
for (`capabilities`) and, given a task, asks the `ModelRouter` for a
suitable model at execution time — it never names a model itself. This is
what lets new local models be added later without touching agent code:

    BAD:   CodeAgent → hard-codes "use qwen-model"
    GOOD:  CodeAgent → required_capabilities=["coding", ...]
           ModelRouter → finds the best currently-registered match

Segment 2 agents produce clearly-labeled development/mock responses, since
no real model runtime is connected yet (see `models/providers/local.py`).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar

from app.core.exceptions import AgentExecutionError, WorkbenchError
from app.core.logging import get_logger, log_event
from app.models.base import GenerationResult, ModelInfo, ModelType
from app.models.providers import get_provider
from app.models.router import ModelRouter, RoutingRequest, RoutingResult

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.rag.service import RAGService
    from app.sandbox.base import SandboxProvider
    from app.tools.registry import ToolRegistry

logger = get_logger(__name__)


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Canonical step id → human title, shared by every agent so the frontend's
# execution-step UI (see frontend/src/components/execution) sees a
# consistent pipeline no matter which agent ran. The base six run for
# every request; agents that use RAG/sandbox/tools (see `finalize_response`
# overrides in code.py/document.py/data.py) append from the rest.
STEP_TITLES: dict[str, str] = {
    "understanding_request": "Understanding request",
    "selecting_agent": "Selecting agent",
    "selecting_model": "Selecting local model",
    "executing": "Executing",
    "generating_response": "Generating response",
    "completed": "Completed",
    "retrieving_context": "Searching knowledge base",
    "running_sandbox": "Running sandbox",
    "revising_code": "Revising code",
    "verifying_output": "Verifying output",
    "running_analysis": "Running data analysis",
    "collecting_system_info": "Collecting system information",
    "analyzing_network": "Analyzing network connections",
    "retrieving_policy": "Retrieving relevant policy",
    "evaluating_findings": "Evaluating findings",
    "generating_report": "Generating report",
    "calling_mcp_tool": "Calling local MCP tool",
}


@dataclass
class AttachmentRef:
    id: str
    filename: str
    file_type: str | None = None
    # Resolved, on-disk path (within the app's own upload/documents
    # directory — see app/tools/fs_utils.py) when the attachment has
    # actually been saved server-side; None for metadata-only references.
    path: str | None = None


@dataclass
class AgentTask:
    message: str
    attachments: list[AttachmentRef] = field(default_factory=list)


@dataclass
class ExecutionContext:
    model_router: ModelRouter
    conversation_id: str
    request_id: str
    settings: "Settings | None" = None
    rag_service: "RAGService | None" = None
    tool_registry: "ToolRegistry | None" = None
    sandbox: "SandboxProvider | None" = None
    # Scratch space for passing data from `build_prompt` to
    # `finalize_response` within one request (e.g. DocumentAgent stashes
    # RAG hits here so `finalize_response` can turn them into citations;
    # DataAgent stashes its CSV Analysis Tool result in `tool_result`). A
    # fresh `ExecutionContext` is created per chat request (see
    # api/routes/chat.py), so none of this ever leaks between requests.
    retrieved_chunks: list = field(default_factory=list)
    tool_result: dict | None = None


@dataclass
class ExecutionStep:
    id: str
    title: str
    status: StepStatus
    # Populated by the chat route for the "selecting_agent" step in Auto
    # mode (the Task Router's one-sentence reason) — None in manual mode
    # and for every other step.
    detail: str | None = None


@dataclass
class CitationRef:
    id: str
    label: str
    source: str


@dataclass
class DeliverableRef:
    id: str
    filename: str
    file_type: str
    size_bytes: int
    status: str = "ready"


@dataclass
class FinalizedResponse:
    text: str
    citations: list[CitationRef] = field(default_factory=list)
    deliverables: list[DeliverableRef] = field(default_factory=list)


@dataclass
class AgentExecutionResult:
    response_text: str
    routing: RoutingResult
    steps: list[ExecutionStep]
    status: ExecutionStatus
    citations: list[CitationRef] = field(default_factory=list)
    deliverables: list[DeliverableRef] = field(default_factory=list)


def development_notice() -> str:
    """Framing for mock output, so it's never mistaken for a real model's
    output. Used when `raw.is_mock` is True (see `response_notice`).
    """
    return (
        "_Structured development response — no real model inference ran. "
        "Set `MODEL_PROVIDER=ollama` (see backend/.env.example) to route this "
        "through a real local model._"
    )


def real_inference_notice(model: ModelInfo) -> str:
    """Footer for genuine local inference, symmetric with
    `development_notice()` — real output must be as clearly labeled as mock
    output, never conflated with it.
    """
    return f"_Generated locally by `{model.name}` via the `{model.provider}` provider — no cloud API involved._"


def response_notice(model: ModelInfo, raw: GenerationResult) -> str:
    return development_notice() if raw.is_mock else real_inference_notice(model)


class BaseAgent(ABC):
    """Task-oriented behavior. Subclasses declare identity + capabilities
    and implement `format_response`; model selection is never their job.
    """

    id: ClassVar[str]
    name: ClassVar[str]
    description: ClassVar[str]
    capabilities: ClassVar[list[str]]
    # Hints the router toward a model *type*; still scored, never forced.
    model_type: ClassVar[ModelType | None] = None

    def can_handle(self, task: AgentTask) -> bool:
        """Whether this agent is willing to take on `task`.

        Segment 2 selects agents explicitly by id (the frontend already
        does agent selection in the UI), so this is always true today. The
        hook exists for a future capability-based auto-routing layer.
        """
        return True

    async def build_prompt(self, task: AgentTask, context: ExecutionContext) -> str:
        """Default prompt construction; override for agent-specific framing.

        Async (and given `context`) so an override can do something like a
        RAG lookup *before* generation — see `DocumentAgent.build_prompt`.
        """
        attachment_note = f" ({len(task.attachments)} attachment(s))" if task.attachments else ""
        return f"[{self.name}] {task.message}{attachment_note}"

    @abstractmethod
    def format_response(self, task: AgentTask, model: ModelInfo, raw: GenerationResult) -> str:
        """Turns the provider's raw (mock) output into this agent's final,
        clearly-labeled development response.
        """
        raise NotImplementedError

    async def resolve_images(self, task: AgentTask, context: ExecutionContext) -> list[bytes]:
        """Raw image bytes (if any) this task's request should carry to the
        provider. Default: none — every agent except `VisionAgent` (which
        reads attached image files from disk) keeps today's text-only
        `provider.generate()` call completely unchanged.
        """
        return []

    async def finalize_response(
        self,
        task: AgentTask,
        model: ModelInfo,
        raw: GenerationResult,
        context: ExecutionContext,
        record: Any,
    ) -> FinalizedResponse:
        """Hook for agents that do more than format text: CodeAgent runs the
        sandbox, DocumentAgent grounds via RAG, DataAgent runs the CSV
        tool. `record(step_id, status)` appends an extra step to the same
        list `execute()` is building — use `STEP_TITLES` ids like
        `"retrieving_context"` / `"running_sandbox"` / `"running_analysis"`.

        Default: just formats the response, no extra steps, no citations
        or deliverables — this is what General/Vision agents use as-is.
        """
        return FinalizedResponse(text=self.format_response(task, model, raw))

    async def execute(self, task: AgentTask, context: ExecutionContext) -> AgentExecutionResult:
        steps: list[ExecutionStep] = []

        def record(step_id: str, status: StepStatus) -> None:
            steps.append(ExecutionStep(id=step_id, title=STEP_TITLES[step_id], status=status))

        log_event(logger, "agent_execution_started", agent_id=self.id, conversation_id=context.conversation_id)
        record("understanding_request", StepStatus.COMPLETED)
        record("selecting_agent", StepStatus.COMPLETED)

        try:
            routing_request = RoutingRequest(
                agent_id=self.id,
                required_capabilities=self.capabilities,
                preferred_type=self.model_type,
                task_excerpt=task.message[:160],
            )
            routing = context.model_router.route(routing_request)
            record("selecting_model", StepStatus.COMPLETED)

            provider = get_provider(routing.model.provider)
            prompt = await self.build_prompt(task, context)
            images = await self.resolve_images(task, context)
            raw = await provider.generate(model=routing.model, prompt=prompt, images=images or None)
            record("executing", StepStatus.COMPLETED)

            finalized = await self.finalize_response(task, routing.model, raw, context, record)
            record("generating_response", StepStatus.COMPLETED)
            record("completed", StepStatus.COMPLETED)

            log_event(
                logger,
                "agent_execution_completed",
                agent_id=self.id,
                model_id=routing.model.id,
                conversation_id=context.conversation_id,
            )
            return AgentExecutionResult(
                response_text=finalized.text,
                routing=routing,
                steps=steps,
                status=ExecutionStatus.COMPLETED,
                citations=finalized.citations,
                deliverables=finalized.deliverables,
            )
        except WorkbenchError:
            # Already a clean, structured domain error (e.g. no suitable
            # model) — log and let it propagate to the API error handler.
            log_event(
                logger,
                "agent_execution_failed",
                level=logging.WARNING,
                agent_id=self.id,
                conversation_id=context.conversation_id,
            )
            raise
        except Exception as exc:  # noqa: BLE001 - deliberately broad: last line of defense
            log_event(
                logger,
                "agent_execution_failed",
                level=logging.ERROR,
                agent_id=self.id,
                conversation_id=context.conversation_id,
                error=str(exc),
            )
            raise AgentExecutionError(f"{self.name} failed to complete the request.", agent_id=self.id) from exc
