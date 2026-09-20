"""API-level tests for the Segment 3 surface: file upload/download,
document ingest/list/search/delete, tool list/execute, and deliverable
list/download.
"""

from __future__ import annotations

import io

from fastapi.testclient import TestClient


def _upload_txt(client: TestClient, filename: str, content: str) -> dict:
    response = client.post(
        "/api/files/upload",
        files={"file": (filename, io.BytesIO(content.encode("utf-8")), "text/plain")},
    )
    assert response.status_code == 200, response.text
    return response.json()


# --- files ----------------------------------------------------------------


def test_upload_and_download_file_roundtrip(client: TestClient) -> None:
    uploaded = _upload_txt(client, "notes.txt", "hello from the test suite")
    assert uploaded["filename"] == "notes.txt"
    assert uploaded["file_type"] == "Text File"
    assert uploaded["size_bytes"] == len("hello from the test suite")

    download = client.get(f"/api/files/{uploaded['id']}")
    assert download.status_code == 200
    assert download.content == b"hello from the test suite"


def test_upload_rejects_unsupported_extension(client: TestClient) -> None:
    response = client.post(
        "/api/files/upload",
        files={"file": ("virus.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_download_unknown_file_returns_clean_404(client: TestClient) -> None:
    response = client.get("/api/files/does-not-exist.txt")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_download_rejects_path_traversal(client: TestClient) -> None:
    response = client.get("/api/files/..%2F..%2Fsecrets.txt")
    assert response.status_code in (400, 404)


# --- documents (RAG) --------------------------------------------------------


def test_document_ingest_list_search_delete_roundtrip(client: TestClient) -> None:
    uploaded = _upload_txt(
        client, "policy.txt", "All confidential documents must remain on local infrastructure."
    )

    ingest = client.post("/api/documents/ingest", json={"file_id": uploaded["id"]})
    assert ingest.status_code == 200, ingest.text
    document = ingest.json()
    assert document["filename"] == "policy.txt"
    assert document["chunk_count"] >= 1

    listed = client.get("/api/documents").json()
    assert any(d["document_id"] == document["document_id"] for d in listed)

    search = client.post("/api/documents/search", json={"query": "confidential documents", "top_k": 3})
    assert search.status_code == 200
    results = search.json()
    assert len(results) >= 1
    assert results[0]["filename"] == "policy.txt"

    deleted = client.delete(f"/api/documents/{document['document_id']}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"

    listed_after = client.get("/api/documents").json()
    assert not any(d["document_id"] == document["document_id"] for d in listed_after)


def test_ingest_unknown_file_returns_clean_404(client: TestClient) -> None:
    response = client.post("/api/documents/ingest", json={"file_id": "not-a-real-file.txt"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_delete_unknown_document_returns_clean_404(client: TestClient) -> None:
    response = client.delete("/api/documents/not-a-real-id")
    assert response.status_code == 404


# --- tools ------------------------------------------------------------------


def test_list_tools_includes_expected_tools(client: TestClient) -> None:
    response = client.get("/api/tools")
    assert response.status_code == 200
    names = {t["name"] for t in response.json()}
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
    calculator = next(t for t in response.json() if t["name"] == "calculator")
    assert calculator["risk"] == "low"
    assert calculator["network"] is False


def test_execute_calculator_tool(client: TestClient) -> None:
    response = client.post("/api/tools/execute", json={"tool_name": "calculator", "input": {"expression": "6 * 7"}})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["output"] == 42


def test_execute_unknown_tool_returns_clean_404(client: TestClient) -> None:
    response = client.post("/api/tools/execute", json={"tool_name": "not-a-real-tool", "input": {}})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "tool_not_found"


# --- deliverables ------------------------------------------------------------


def test_deliverables_list_and_download_roundtrip(client: TestClient) -> None:
    generate = client.post(
        "/api/tools/execute",
        json={
            "tool_name": "document_generation",
            "input": {"filename": "note", "format": "md", "title": "Note", "content": "Hello deliverable."},
        },
    )
    assert generate.status_code == 200
    assert generate.json()["success"] is True

    listed = client.get("/api/deliverables")
    assert listed.status_code == 200
    assert any(d["filename"] == "note.md" for d in listed.json())

    download = client.get("/api/deliverables/note.md")
    assert download.status_code == 200
    assert b"Hello deliverable." in download.content


def test_download_unknown_deliverable_returns_clean_404(client: TestClient) -> None:
    response = client.get("/api/deliverables/does-not-exist.docx")
    assert response.status_code == 404
