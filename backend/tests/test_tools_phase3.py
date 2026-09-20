"""CSV Analysis, Document Generation, and Knowledge Search tools."""

from __future__ import annotations

import pytest

from app.rag.embeddings import MockEmbeddingProvider
from app.rag.service import RAGService
from app.rag.vector_store import ChromaVectorStore
from app.tools import build_default_tool_registry


@pytest.mark.asyncio
async def test_csv_analysis_computes_real_statistics(monkeypatch, tmp_path) -> None:
    from app.core.config import get_settings
    from app.tools.csv_analysis import CSVAnalysisTool

    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "production.csv").write_text(
        "month,units,plant\nJan,100,A\nFeb,150,A\nMar,120,B\n", encoding="utf-8"
    )
    monkeypatch.setattr(get_settings(), "upload_dir", str(uploads))

    result = await CSVAnalysisTool().execute({"path": "production.csv", "root": "uploads"})
    assert result.success
    assert result.output["row_count"] == 3
    assert result.output["numeric_summary"]["units"]["mean"] == pytest.approx(123.3333, rel=1e-3)
    assert result.output["numeric_summary"]["units"]["max"] == 150
    assert result.output["numeric_summary"]["units"]["min"] == 100


@pytest.mark.asyncio
async def test_csv_analysis_group_by(monkeypatch, tmp_path) -> None:
    from app.core.config import get_settings
    from app.tools.csv_analysis import CSVAnalysisTool

    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "production.csv").write_text(
        "month,units,plant\nJan,100,A\nFeb,150,A\nMar,120,B\n", encoding="utf-8"
    )
    monkeypatch.setattr(get_settings(), "upload_dir", str(uploads))

    result = await CSVAnalysisTool().execute(
        {"path": "production.csv", "root": "uploads", "group_by": "plant", "agg_column": "units"}
    )
    assert result.success
    groups = result.output["group_by"]["groups"]
    assert groups["A"]["sum"] == 250
    assert groups["B"]["sum"] == 120


@pytest.mark.asyncio
async def test_csv_analysis_missing_file() -> None:
    from app.tools.csv_analysis import CSVAnalysisTool

    result = await CSVAnalysisTool().execute({"path": "nope.csv", "root": "uploads"})
    assert not result.success


@pytest.mark.asyncio
async def test_document_generation_writes_markdown(monkeypatch, tmp_path) -> None:
    from app.core.config import get_settings
    from app.tools.document_generation import DocumentGenerationTool

    monkeypatch.setattr(get_settings(), "generated_dir", str(tmp_path / "generated"))

    result = await DocumentGenerationTool().execute(
        {"filename": "report", "format": "md", "title": "Report", "content": "Line one.\n\nLine two."}
    )
    assert result.success
    assert result.output["filename"] == "report.md"
    assert result.output["file_type"] == "Markdown Document"
    generated_file = tmp_path / "generated" / "report.md"
    assert generated_file.exists()
    assert "Line one." in generated_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_document_generation_writes_docx(monkeypatch, tmp_path) -> None:
    from app.core.config import get_settings
    from app.tools.document_generation import DocumentGenerationTool

    monkeypatch.setattr(get_settings(), "generated_dir", str(tmp_path / "generated"))

    result = await DocumentGenerationTool().execute(
        {"filename": "approval_note", "format": "docx", "title": "Approval Note", "content": "Approved."}
    )
    assert result.success
    assert (tmp_path / "generated" / "approval_note.docx").exists()


@pytest.mark.asyncio
async def test_document_generation_rejects_unsupported_format() -> None:
    from app.tools.document_generation import DocumentGenerationTool

    result = await DocumentGenerationTool().execute({"filename": "x", "format": "exe", "content": "y"})
    assert not result.success


@pytest.mark.asyncio
async def test_knowledge_search_tool_returns_ingested_content(tmp_path) -> None:
    store = ChromaVectorStore(persist_path=tmp_path / "chroma", collection_name="kb_tool_test")
    rag = RAGService(vector_store=store, embedding_provider=MockEmbeddingProvider())
    path = tmp_path / "policy.txt"
    path.write_text("Confidential documents must never leave the organization's own servers.", encoding="utf-8")
    await rag.ingest_document(path)

    from app.tools.knowledge_search import KnowledgeSearchTool

    result = await KnowledgeSearchTool(rag).execute({"query": "confidential documents policy"})
    assert result.success
    assert len(result.output) >= 1
    assert result.output[0]["filename"] == "policy.txt"


def test_build_default_tool_registry_registers_all_tools(tmp_path) -> None:
    store = ChromaVectorStore(persist_path=tmp_path / "chroma", collection_name="registry_test")
    rag = RAGService(vector_store=store, embedding_provider=MockEmbeddingProvider())
    registry = build_default_tool_registry(rag)
    names = {m.name for m in registry.list()}
    assert names == {
        "file_read",
        "file_write",
        "list_files",
        "calculator",
        "csv_analysis",
        "document_generation",
        "knowledge_search",
        "report_generation",
    }
