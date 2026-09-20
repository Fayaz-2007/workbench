"""RAGService — orchestrates ingestion and search. The single entry point
`app/agents` and `app/api/routes` use; nothing outside `app/rag/` touches
a loader, the chunker, the embedding provider, or the vector store
directly.

    Document -> load -> chunk -> embed -> store           (ingest_document)
    Query -> embed -> vector search -> ranked chunks        (search)

Every document that goes through this stays on local disk
(`documents_dir`) and in the local Chroma store (`chroma_path`) — nothing
here makes a network call except, optionally, to a local Ollama instance
for embeddings (see `embeddings.py`).
"""

from __future__ import annotations

from pathlib import Path

from app.core.logging import get_logger, log_event
from app.rag.chunker import DocumentChunker
from app.rag.embeddings import EmbeddingProvider
from app.rag.loaders import load_document
from app.rag.retriever import Retriever
from app.rag.schemas import DocumentSummary, RetrievedChunk
from app.rag.vector_store import VectorStore

logger = get_logger(__name__)


class RAGService:
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        chunker: DocumentChunker | None = None,
        top_k: int = 4,
    ) -> None:
        self._store = vector_store
        self._embeddings = embedding_provider
        self._chunker = chunker or DocumentChunker()
        self._retriever = Retriever(embedding_provider, vector_store, default_top_k=top_k)
        self._documents: dict[str, DocumentSummary] = {}

    async def ingest_document(self, path: Path, display_filename: str | None = None) -> DocumentSummary:
        log_event(logger, "knowledge_document_received", filename=display_filename or path.name)

        document = load_document(path, display_filename=display_filename)
        extracted_chars = sum(len(p.text) for p in document.pages)
        log_event(
            logger,
            "knowledge_text_extracted",
            document_filename=document.filename,
            characters=extracted_chars,
            pages=len(document.pages),
        )

        chunks = self._chunker.chunk_document(document)
        log_event(logger, "knowledge_chunks_created", document_filename=document.filename, chunks=len(chunks))

        ocr_pages = sum(1 for p in document.pages if p.needs_ocr)
        if chunks:
            embeddings = await self._embeddings.embed([c.text for c in chunks])
            self._store.add(chunks, embeddings)
        log_event(logger, "knowledge_chunks_indexed", document_filename=document.filename, chunks=len(chunks))

        summary = DocumentSummary(
            document_id=document.document_id,
            filename=document.filename,
            doc_type=document.doc_type,
            chunk_count=len(chunks),
            ingested_at=document.ingested_at,
        )
        self._documents[document.document_id] = summary

        log_event(
            logger,
            "document_ingested",
            document_id=document.document_id,
            document_filename=document.filename,
            chunks=len(chunks),
            pages_needing_ocr=ocr_pages,
        )
        return summary

    async def search(self, query: str, top_k: int | None = None, min_score: float | None = None) -> list[RetrievedChunk]:
        """`min_score` (0..1, see vector_store.py's distance->score
        conversion) drops results below the given relevance — omit it (or
        pass None) for raw top-k, as `KnowledgeSearchTool` does; agents
        that need an honest "nothing relevant" signal (Document Agent,
        the security orchestrator) pass `settings.rag_relevance_threshold`.
        """
        # The query text itself (the user's own question, not document
        # content) is safe to log for traceability; retrieved chunk *text*
        # never is — only filenames/scores are logged below.
        log_event(logger, "knowledge_query", query=query, query_length=len(query))
        results = await self._retriever.retrieve(query, top_k)
        if min_score is not None:
            results = [r for r in results if r.score >= min_score]
        log_event(
            logger,
            "knowledge_retrieved",
            chunks=len(results),
            sources=[r.chunk.filename for r in results],
        )
        return results

    def list_documents(self) -> list[DocumentSummary]:
        return sorted(self._documents.values(), key=lambda d: d.ingested_at, reverse=True)

    def delete_document(self, document_id: str) -> bool:
        if document_id not in self._documents:
            return False
        self._store.delete_document(document_id)
        del self._documents[document_id]
        log_event(logger, "document_deleted", document_id=document_id)
        return True

    @property
    def chunk_count(self) -> int:
        return self._store.count()
