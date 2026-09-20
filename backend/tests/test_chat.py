"""POST /api/chat: end-to-end through Agent Manager -> Agent -> Model
Router -> LocalModelProvider -> response, shaped for the frontend's chat
and execution-step UI.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

EXPECTED_MODEL_BY_AGENT = {
    "code": "code-small",
    "document": "general-small",
    "vision": "vision-small",
    "data": "data-small",
    "general": "general-small",
}


def test_chat_response_shape(client: TestClient) -> None:
    response = client.post("/api/chat", json={"agent_id": "general", "message": "Hello there"})
    assert response.status_code == 200
    body = response.json()

    assert body["conversation_id"]
    assert body["agent"] == {"id": "general", "name": "General Agent"}
    assert body["routing"]["model_id"] == "general-small"
    assert 0.0 < body["routing"]["score"] <= 1.0
    assert body["response"]
    assert body["execution"]["status"] == "completed"
    step_ids = [s["id"] for s in body["execution"]["steps"]]
    assert step_ids == [
        "understanding_request",
        "selecting_agent",
        "selecting_model",
        "executing",
        "generating_response",
        "completed",
    ]
    assert all(s["status"] == "completed" for s in body["execution"]["steps"])


def test_chat_reuses_conversation_id(client: TestClient) -> None:
    first = client.post("/api/chat", json={"agent_id": "general", "message": "one"}).json()
    second = client.post(
        "/api/chat",
        json={"agent_id": "general", "message": "two", "conversation_id": first["conversation_id"]},
    ).json()
    assert second["conversation_id"] == first["conversation_id"]


def test_each_agent_routes_to_expected_dev_model(client: TestClient) -> None:
    for agent_id, expected_model_id in EXPECTED_MODEL_BY_AGENT.items():
        response = client.post("/api/chat", json={"agent_id": agent_id, "message": "test message"})
        assert response.status_code == 200, response.text
        assert response.json()["routing"]["model_id"] == expected_model_id, agent_id


def test_chat_rejects_empty_message(client: TestClient) -> None:
    response = client.post("/api/chat", json={"agent_id": "general", "message": ""})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_chat_no_suitable_model_when_capability_unavailable(client: TestClient) -> None:
    delete_response = client.delete("/api/models/code-small")
    assert delete_response.status_code == 200

    response = client.post("/api/chat", json={"agent_id": "code", "message": "write a function"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "no_suitable_model"
