"""API schemas for the chat endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AttachmentIn(BaseModel):
    id: str
    filename: str
    file_type: str | None = None
    size_bytes: int | None = None
    # Relative path within `uploads/` once the file has actually been
    # saved server-side via POST /api/files/upload — lets agents/tools
    # (CSV analysis, RAG ingestion) read the real file, not just its name.
    path: str | None = None


class ConversationMessageIn(BaseModel):
    """One prior message, as the frontend already holds it client-side —
    there is no server-side conversation store yet (see
    `app/database/__init__.py` and `backend/README.md`'s "Intentionally
    not implemented yet"). Sent only so the natural-language
    "export this conversation" path (see `app/services/conversation_export`)
    has something to summarize; every other agent ignores this field
    entirely, so it changes nothing about today's stateless `/api/chat`
    behavior.
    """

    role: Literal["user", "assistant"]
    text: str = ""
    citations: list[str] = []


class ChatRequest(BaseModel):
    # None (omitted) or the literal "auto" triggers automatic agent
    # selection via the Task Router (see app/agents/task_router.py) —
    # a concrete id ("code", "document", ...) is manual mode, unchanged
    # from Segment 2. Task Router and Model Router are independent: this
    # field is about WHO handles the request, never WHICH model.
    agent_id: str | None = None
    message: str = Field(default="", max_length=8000)
    conversation_id: str | None = None
    attachments: list[AttachmentIn] | None = None
    conversation_history: list[ConversationMessageIn] | None = None


class AgentSummary(BaseModel):
    id: str
    name: str


class TaskRoutingOut(BaseModel):
    """Present only when Auto mode actually ran the Task Router — absent
    (null) in manual mode. `reason` is always one plain sentence, never
    internal scores or chain-of-thought. `target` is what the frontend
    renders as "AUTO MODE -> {target}" (see Phase E/J).
    """

    target: str
    agent_id: str
    reason: str
    confidence: float


class RoutingInfo(BaseModel):
    model_id: str
    reason: str
    score: float


class ExecutionStepOut(BaseModel):
    id: str
    title: str
    status: Literal["pending", "running", "completed", "failed"]
    detail: str | None = None


class ExecutionInfo(BaseModel):
    status: Literal["pending", "running", "completed", "failed"]
    steps: list[ExecutionStepOut]


class CitationOut(BaseModel):
    id: str
    label: str
    source: str


class DeliverableOut(BaseModel):
    id: str
    filename: str
    file_type: str
    size_bytes: int
    status: Literal["ready", "failed"] = "ready"


class ChatResponse(BaseModel):
    conversation_id: str
    agent: AgentSummary
    task_routing: TaskRoutingOut | None = None
    routing: RoutingInfo
    response: str
    execution: ExecutionInfo
    citations: list[CitationOut] = []
    deliverables: list[DeliverableOut] = []
