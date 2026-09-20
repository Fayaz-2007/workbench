"""DocumentChunker — splits a loaded document's pages into overlapping,
retrieval-sized text chunks, preserving the metadata that lets the UI show
sources later (filename, page, document id, chunk id, source path,
ingestion timestamp).
"""

from __future__ import annotations

from uuid import uuid4

from app.rag.schemas import Chunk, LoadedDocument


class DocumentChunker:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 120) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, document: LoadedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        for page in document.pages:
            for text in self._split(page.text):
                if not text.strip():
                    continue
                chunks.append(
                    Chunk(
                        chunk_id=uuid4().hex,
                        document_id=document.document_id,
                        filename=document.filename,
                        source_path=document.source_path,
                        doc_type=document.doc_type,
                        page_number=page.page_number,
                        text=text,
                        ingested_at=document.ingested_at,
                    )
                )
        return chunks

    def _split(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.chunk_overlap
        pieces: list[str] = []
        start = 0
        while start < len(text):
            pieces.append(text[start : start + self.chunk_size])
            start += step
        return pieces
