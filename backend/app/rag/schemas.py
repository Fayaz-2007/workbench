"""Internal RAG data types — shared across loaders, the chunker, the
vector store, and the retriever. Distinct from `app/schemas/`, which holds
the public API's request/response models.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DocumentPage:
    """One page/section of extracted text. `page_number` is `None` for
    formats with no page concept (TXT, DOCX, CSV, XLSX).
    """

    text: str
    page_number: int | None = None
    needs_ocr: bool = False


@dataclass
class LoadedDocument:
    document_id: str
    filename: str
    source_path: str
    doc_type: str
    pages: list[DocumentPage] = field(default_factory=list)
    ingested_at: str = ""


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    filename: str
    source_path: str
    doc_type: str
    page_number: int | None
    text: str
    ingested_at: str


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float


@dataclass
class DocumentSummary:
    document_id: str
    filename: str
    doc_type: str
    chunk_count: int
    ingested_at: str
