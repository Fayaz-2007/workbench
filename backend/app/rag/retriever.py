"""Retriever — embeds a query and asks the VectorStore for the closest
chunks. The one place that knows both "how to embed" and "where the
vectors live", so `RAGService` doesn't have to.
"""

from __future__ import annotations

from app.rag.embeddings import EmbeddingProvider
from app.rag.schemas import RetrievedChunk
from app.rag.vector_store import VectorStore


class Retriever:
    def __init__(self, embedding_provider: EmbeddingProvider, vector_store: VectorStore, default_top_k: int = 4) -> None:
        self._embeddings = embedding_provider
        self._store = vector_store
        self._default_top_k = default_top_k

    async def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        [embedding] = await self._embeddings.embed([query])
        return self._store.query(embedding, top_k or self._default_top_k)
