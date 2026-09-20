"""API schemas for the local knowledge base (RAG)."""

from __future__ import annotations

from pydantic import BaseModel


class DocumentIngestRequest(BaseModel):
    # References a file already uploaded via POST /api/files/upload
    # (its `path`) — this endpoint never accepts raw bytes directly, so
    # every document that reaches RAG has already passed upload validation.
    file_id: str


class DocumentOut(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    chunk_count: int
    ingested_at: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = 4


class SearchResultOut(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int | None
    text: str
    score: float
