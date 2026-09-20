"""POST /api/documents/ingest, GET /api/documents, POST /api/documents/search,
DELETE /api/documents/{id} — the local knowledge base's public surface.

Thin wrappers around `RAGService` (see `app/rag/`) — no ingestion, chunking,
embedding, or vector-search logic lives in this module.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_app_settings, get_rag_service, record_activity
from app.core.config import Settings
from app.core.exceptions import ResourceNotFoundError
from app.rag.service import RAGService
from app.schemas.documents import DocumentIngestRequest, DocumentOut, SearchRequest, SearchResultOut
from app.tools.fs_utils import PathEscapeError, resolve_within

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/ingest", response_model=DocumentOut)
async def ingest_document(
    payload: DocumentIngestRequest,
    request: Request,
    rag_service: RAGService = Depends(get_rag_service),
    settings: Settings = Depends(get_app_settings),
) -> DocumentOut:
    try:
        target = resolve_within(settings.upload_path, payload.file_id)
    except PathEscapeError as exc:
        raise ResourceNotFoundError(str(exc)) from exc

    if not target.exists():
        raise ResourceNotFoundError(f"Uploaded file '{payload.file_id}' was not found. Upload it first via /api/files/upload.")

    # Uploaded files are stored under a uuid-prefixed name (see
    # app/api/routes/files.py) — strip it so citations/listings show the
    # user's original filename, not the internal storage name.
    display_filename = payload.file_id.split("_", 1)[1] if "_" in payload.file_id else payload.file_id
    summary = await rag_service.ingest_document(target, display_filename=display_filename)
    record_activity(request, action="Ingested document", resource=summary.filename)
    return DocumentOut(**summary.__dict__)


@router.get("", response_model=list[DocumentOut])
def list_documents(rag_service: RAGService = Depends(get_rag_service)) -> list[DocumentOut]:
    return [DocumentOut(**d.__dict__) for d in rag_service.list_documents()]


@router.post("/search", response_model=list[SearchResultOut])
async def search_documents(payload: SearchRequest, rag_service: RAGService = Depends(get_rag_service)) -> list[SearchResultOut]:
    results = await rag_service.search(payload.query, top_k=payload.top_k)
    return [
        SearchResultOut(
            chunk_id=r.chunk.chunk_id,
            document_id=r.chunk.document_id,
            filename=r.chunk.filename,
            page_number=r.chunk.page_number,
            text=r.chunk.text,
            score=r.score,
        )
        for r in results
    ]


@router.delete("/{document_id}")
def delete_document(document_id: str, request: Request, rag_service: RAGService = Depends(get_rag_service)) -> dict[str, str]:
    if not rag_service.delete_document(document_id):
        raise ResourceNotFoundError(f"Document '{document_id}' was not found.")
    record_activity(request, action="Removed document", resource=document_id)
    return {"id": document_id, "status": "deleted"}
