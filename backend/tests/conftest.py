"""Shared pytest fixtures.

Every test that boots the app gets its own throwaway data directory —
`isolate_data_dirs` (autouse) points `upload_dir` / `documents_dir` /
`generated_dir` / `chroma_path` at a fresh `tmp_path` *before* `client`
triggers `app.main`'s lifespan, so each test's RAGService/ChromaDB and
uploaded/generated files never touch the real `backend/data/` directory
and never leak between tests (the settings singleton is otherwise shared
process-wide via `get_settings()`'s `lru_cache`).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def isolate_data_dirs(tmp_path, monkeypatch) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "documents_dir", str(tmp_path / "documents"))
    monkeypatch.setattr(settings, "generated_dir", str(tmp_path / "generated"))
    monkeypatch.setattr(settings, "chroma_path", str(tmp_path / "chroma"))


@pytest.fixture
def client(isolate_data_dirs) -> Iterator[TestClient]:
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
