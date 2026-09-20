"""GET/POST /api/models, DELETE /api/models/{id}, and the admin views that
read from the same registry — the path the Admin Models page uses.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_models_includes_seeded_dev_models(client: TestClient) -> None:
    response = client.get("/api/models")
    assert response.status_code == 200
    ids = {m["id"] for m in response.json()}
    assert {"general-small", "code-small", "vision-small", "data-small"} <= ids


def test_add_model_matches_admin_add_model_form_shape(client: TestClient) -> None:
    payload = {
        "name": "Embedding Model",
        "type": "embedding",
        "identifier": "dev-mock/bge-base-en",
        "capabilities": "embedding, retrieval",
        "context_length": 8192,
        "quantization": "Q4_K_M",
        "status": "disabled",
    }
    response = client.post("/api/models", json=payload)
    assert response.status_code == 200
    created = response.json()
    assert created["name"] == "Embedding Model"
    assert created["capabilities"] == ["embedding", "retrieval"]
    assert created["status"] == "disabled"
    assert created["id"]

    listed_ids = {m["id"] for m in client.get("/api/models").json()}
    assert created["id"] in listed_ids


def test_delete_model(client: TestClient) -> None:
    created = client.post(
        "/api/models",
        json={
            "name": "Temp Model",
            "type": "general",
            "identifier": "dev-mock/temp",
            "capabilities": "reasoning",
            "context_length": 2048,
            "quantization": "4bit",
            "status": "disabled",
        },
    ).json()

    delete_response = client.delete(f"/api/models/{created['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"id": created["id"], "status": "deleted"}

    listed_ids = {m["id"] for m in client.get("/api/models").json()}
    assert created["id"] not in listed_ids


def test_delete_unknown_model_returns_clean_error(client: TestClient) -> None:
    response = client.delete("/api/models/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "model_not_found"


def test_admin_overview(client: TestClient) -> None:
    response = client.get("/api/admin/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["models_total"] >= 4
    assert body["models_online"] >= 4
    assert body["system_status"] == "development"
    assert body["external_connections"] == "not_connected"


def test_admin_models_matches_public_models(client: TestClient) -> None:
    admin_ids = {m["id"] for m in client.get("/api/admin/models").json()}
    public_ids = {m["id"] for m in client.get("/api/models").json()}
    assert admin_ids == public_ids
