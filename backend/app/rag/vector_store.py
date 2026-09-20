"""VectorStore — a thin, swappable abstraction over ChromaDB.

Embeddings are always computed by our own `EmbeddingProvider` and passed
in explicitly (see `service.py`) — Chroma's own embedding-function hooks
are not used, so exactly one thing in this codebase decides how text
becomes a vector. ChromaDB runs embedded/local (`PersistentClient` against
`CHROMA_PATH`); no server process, no network.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.core.exceptions import KnowledgeStoreConfigError
from app.rag.schemas import Chunk, RetrievedChunk


class VectorStore(ABC):
    @abstractmethod
    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def query(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        raise NotImplementedError

    @abstractmethod
    def delete_document(self, document_id: str) -> int:
        """Removes every chunk belonging to `document_id`; returns how many."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError


def _chunk_metadata(chunk: Chunk) -> dict[str, Any]:
    return {
        "document_id": chunk.document_id,
        "filename": chunk.filename,
        "source_path": chunk.source_path,
        "doc_type": chunk.doc_type,
        "page_number": chunk.page_number if chunk.page_number is not None else -1,
        "ingested_at": chunk.ingested_at,
    }


def _chunk_from_result(chunk_id: str, text: str, metadata: dict[str, Any]) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id=metadata.get("document_id", ""),
        filename=metadata.get("filename", ""),
        source_path=metadata.get("source_path", ""),
        doc_type=metadata.get("doc_type", ""),
        page_number=None if metadata.get("page_number", -1) == -1 else metadata.get("page_number"),
        text=text,
        ingested_at=metadata.get("ingested_at", ""),
    )


class ChromaVectorStore(VectorStore):
    """Local, persistent ChromaDB collection — no external vector database."""

    def __init__(self, persist_path: Path, collection_name: str = "workbench_documents") -> None:
        import chromadb

        persist_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_path))
        # Explicit cosine space: Chroma's default (L2 on raw, non-normalized
        # embedding vectors) produces distances whose scale depends entirely
        # on the embedding model's vector magnitude — not comparable to a
        # fixed 0..1 relevance threshold. Cosine distance is bounded (0..2)
        # regardless of model, so `query()`'s score conversion stays valid
        # whether the active EmbeddingProvider is mock or a real model.
        self._collection = self._client.get_or_create_collection(collection_name, metadata={"hnsw:space": "cosine"})

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        try:
            self._collection.add(
                ids=[c.chunk_id for c in chunks],
                embeddings=embeddings,
                documents=[c.text for c in chunks],
                metadatas=[_chunk_metadata(c) for c in chunks],
            )
        except Exception as exc:
            if "dimension" in str(exc).lower():
                raise KnowledgeStoreConfigError() from exc
            raise

    def query(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        if self.count() == 0:
            return []
        try:
            result = self._collection.query(query_embeddings=[embedding], n_results=min(top_k, self.count()))
        except Exception as exc:
            if "dimension" in str(exc).lower():
                raise KnowledgeStoreConfigError() from exc
            raise
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        retrieved = []
        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            # With the collection in cosine space (see __init__), Chroma's
            # distance is `1 - cosine_similarity`, bounded to [0, 2] — so
            # this recovers the cosine similarity directly as a 0..1-ish
            # "higher is better" score, independent of embedding model.
            score = max(0.0, 1.0 - distance)
            retrieved.append(RetrievedChunk(chunk=_chunk_from_result(chunk_id, text, dict(metadata)), score=round(score, 4)))
        return retrieved

    def delete_document(self, document_id: str) -> int:
        existing = self._collection.get(where={"document_id": document_id})
        ids = existing.get("ids", [])
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    def count(self) -> int:
        return self._collection.count()
