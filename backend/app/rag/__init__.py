"""Local retrieval-augmented generation.

    Document -> Ingestion -> Text extraction -> Chunking -> Local embeddings
        -> ChromaDB -> Retriever -> Relevant context -> Agent -> Local LLM
        -> Grounded response

Every piece is independently replaceable: `loaders.py` (DocumentLoader),
`chunker.py` (DocumentChunker), `embeddings.py` (EmbeddingProvider),
`vector_store.py` (VectorStore), `retriever.py` (Retriever). `service.py`
(RAGService) is the only thing the rest of the app imports.
"""

from __future__ import annotations

from app.core.config import Settings
from app.rag.chunker import DocumentChunker
from app.rag.embeddings import get_embedding_provider
from app.rag.service import RAGService
from app.rag.vector_store import ChromaVectorStore


def build_rag_service(settings: Settings) -> RAGService:
    store = ChromaVectorStore(persist_path=settings.chroma_resolved_path)
    embeddings = get_embedding_provider()
    chunker = DocumentChunker(chunk_size=settings.rag_chunk_size, chunk_overlap=settings.rag_chunk_overlap)
    return RAGService(vector_store=store, embedding_provider=embeddings, chunker=chunker, top_k=settings.rag_top_k)


__all__ = ["RAGService", "build_rag_service"]
