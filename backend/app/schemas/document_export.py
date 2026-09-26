"""API schemas for POST /api/conversations/{conversation_id}/export."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.schemas.chat import DeliverableOut, ExecutionInfo


class ExportMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = ""
    citations: list[str] = []


class ConversationExportRequest(BaseModel):
    format: Literal["docx", "pptx", "xlsx", "pdf"]
    # The frontend's own message history for this conversation — see
    # `app/schemas/chat.py::ConversationMessageIn` for why this is passed
    # in the body rather than looked up server-side.
    messages: list[ExportMessageIn] = []


class ConversationExportResponse(BaseModel):
    deliverable: DeliverableOut
    execution: ExecutionInfo
