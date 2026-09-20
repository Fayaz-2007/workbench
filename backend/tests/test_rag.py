"""RAG pipeline: chunking, mock embeddings, the Chroma vector store, and
RAGService end-to-end ingestion + search — all against the deterministic
mock embedding provider, so these tests need no Ollama and no network.
"""

from __future__ import annotations

import pytest

from app.rag.chunker import DocumentChunker
from app.rag.embeddings import MockEmbeddingProvider
from app.rag.loaders import load_document
from app.rag.schemas import LoadedDocument
from app.rag.service import RAGService
from app.rag.vector_store import ChromaVectorStore


def test_chunker_short_text_is_one_chunk() -> None:
    from app.rag.schemas import DocumentPage

    document = LoadedDocument(
        document_id="doc1", filename="a.txt", source_path="a.txt", doc_type="txt",
        pages=[DocumentPage(text="short text")], ingested_at="2026-01-01T00:00:00Z",
    )
    chunks = DocumentChunker(chunk_size=800, chunk_overlap=100).chunk_document(document)
    assert len(chunks) == 1
    assert chunks[0].text == "short text"
    assert chunks[0].document_id == "doc1"


def test_chunker_splits_long_text_with_overlap() -> None:
    from app.rag.schemas import DocumentPage

    long_text = "word " * 1000
    document = LoadedDocument(
        document_id="doc2", filename="b.txt", source_path="b.txt", doc_type="txt",
        pages=[DocumentPage(text=long_text, page_number=1)], ingested_at="2026-01-01T00:00:00Z",
    )
    chunks = DocumentChunker(chunk_size=200, chunk_overlap=40).chunk_document(document)
    assert len(chunks) > 1
    assert all(c.page_number == 1 for c in chunks)
    assert all(len(c.text) <= 200 for c in chunks)


def test_chunker_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError):
        DocumentChunker(chunk_size=100, chunk_overlap=100)


@pytest.mark.asyncio
async def test_mock_embedding_provider_is_deterministic() -> None:
    provider = MockEmbeddingProvider()
    [v1] = await provider.embed(["hello world"])
    [v2] = await provider.embed(["hello world"])
    assert v1 == v2
    assert len(v1) == provider.dimensions


@pytest.mark.asyncio
async def test_mock_embedding_different_text_differs() -> None:
    provider = MockEmbeddingProvider()
    [v1] = await provider.embed(["pump maintenance schedule"])
    [v2] = await provider.embed(["quarterly financial report"])
    assert v1 != v2


def _make_txt(tmp_path, name: str, content: str):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_rag_service_ingest_and_search_roundtrip(tmp_path) -> None:
    store = ChromaVectorStore(persist_path=tmp_path / "chroma", collection_name="test_docs")
    service = RAGService(vector_store=store, embedding_provider=MockEmbeddingProvider(), top_k=3)

    path = _make_txt(
        tmp_path,
        "maintenance.txt",
        "Pump station 4 requires quarterly maintenance. Replace the seal every 6 months. "
        "Inspect bearings annually. Lubricate motor shafts monthly.",
    )
    summary = await service.ingest_document(path)
    assert summary.filename == "maintenance.txt"
    assert summary.chunk_count >= 1
    assert service.chunk_count == summary.chunk_count

    results = await service.search("pump station maintenance")
    assert len(results) >= 1
    assert results[0].chunk.filename == "maintenance.txt"
    assert results[0].chunk.document_id == summary.document_id
    assert 0.0 < results[0].score <= 1.0


@pytest.mark.asyncio
async def test_rag_service_list_and_delete_document(tmp_path) -> None:
    store = ChromaVectorStore(persist_path=tmp_path / "chroma", collection_name="test_docs2")
    service = RAGService(vector_store=store, embedding_provider=MockEmbeddingProvider())

    path = _make_txt(tmp_path, "notes.txt", "some notes about the refinery inspection")
    summary = await service.ingest_document(path)

    assert [d.document_id for d in service.list_documents()] == [summary.document_id]

    deleted = service.delete_document(summary.document_id)
    assert deleted is True
    assert service.list_documents() == []
    assert service.chunk_count == 0


@pytest.mark.asyncio
async def test_rag_service_search_empty_store_returns_nothing(tmp_path) -> None:
    store = ChromaVectorStore(persist_path=tmp_path / "chroma", collection_name="test_docs3")
    service = RAGService(vector_store=store, embedding_provider=MockEmbeddingProvider())

    results = await service.search("anything")
    assert results == []


def test_load_csv_document(tmp_path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("name,value\nfoo,1\nbar,2\n", encoding="utf-8")
    document = load_document(path)
    assert document.doc_type == "csv"
    assert "foo" in document.pages[0].text


def test_load_unsupported_extension_raises(tmp_path) -> None:
    from app.core.exceptions import InvalidRequestError

    path = tmp_path / "file.exe"
    path.write_bytes(b"binary")
    with pytest.raises(InvalidRequestError):
        load_document(path)
