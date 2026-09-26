"""POST /api/conversations/{conversation_id}/export — turns a conversation
into a real, downloadable DOCX/PPTX/XLSX/PDF file.

Calls the exact same `export_conversation()` the chat route's Task Router
dispatch uses for the natural-language trigger ("generate a document about
this", ...) — see `app/api/routes/chat.py::_dispatch_export_conversation`
and `app/services/conversation_export/pipeline.py`. No generation logic is
duplicated between the two entry points.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_app_settings, get_model_router
from app.core.config import Settings
from app.models.router import ModelRouter
from app.schemas.chat import DeliverableOut, ExecutionInfo, ExecutionStepOut
from app.schemas.document_export import ConversationExportRequest, ConversationExportResponse
from app.services.conversation_export import ExportMessage, export_conversation

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/{conversation_id}/export", response_model=ConversationExportResponse)
async def export_conversation_endpoint(
    conversation_id: str,
    payload: ConversationExportRequest,
    model_router: ModelRouter = Depends(get_model_router),
    settings: Settings = Depends(get_app_settings),
) -> ConversationExportResponse:
    history = [ExportMessage(role=m.role, text=m.text, citations=list(m.citations)) for m in payload.messages]

    export = await export_conversation(
        history,
        payload.format,
        model_router=model_router,
        settings=settings,
        conversation_id=conversation_id,
    )

    return ConversationExportResponse(
        deliverable=DeliverableOut(
            id=export.deliverable.id,
            filename=export.deliverable.filename,
            file_type=export.deliverable.file_type,
            size_bytes=export.deliverable.size_bytes,
            status=export.deliverable.status,
        ),
        execution=ExecutionInfo(
            status="completed",
            steps=[ExecutionStepOut(id=s.id, title=s.title, status=s.status.value, detail=s.detail) for s in export.steps],
        ),
    )
