"""Agent listing, retrieval, and the invalid-agent error path."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

EXPECTED_AGENT_IDS = {"general", "code", "document", "vision", "data"}


def test_list_agents(client: TestClient) -> None:
    response = client.get("/api/agents")
    assert response.status_code == 200
    agents = response.json()
    assert {a["id"] for a in agents} == EXPECTED_AGENT_IDS
    for agent in agents:
        assert agent["name"]
        assert agent["description"]
        assert isinstance(agent["capabilities"], list) and agent["capabilities"]


def test_agent_retrieval_via_manager(client: TestClient) -> None:
    manager = app.state.agent_manager
    code_agent = manager.get("code")
    assert code_agent.id == "code"
    assert "coding" in code_agent.capabilities


def test_invalid_agent_returns_clean_error(client: TestClient) -> None:
    response = client.post("/api/chat", json={"agent_id": "not-a-real-agent", "message": "hello"})
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "agent_not_found"
    # No Python traceback should ever reach the client.
    assert "Traceback" not in response.text
