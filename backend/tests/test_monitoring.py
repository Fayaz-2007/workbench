"""System monitoring, network monitoring, and security status — plus the
Task Router's new routing targets and the /api/chat dispatch for each.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.agents.manager import build_default_agent_manager
from app.agents.task_router import TaskRouter
from app.monitoring.network import get_network_status
from app.monitoring.system import get_system_status


def test_get_system_status_returns_real_values() -> None:
    status = get_system_status()
    assert status.hostname
    assert 0.0 <= status.cpu_percent <= 100.0
    assert 0.0 <= status.ram_percent <= 100.0
    assert status.ram_total_gb > 0
    assert status.process_count > 0
    assert status.uptime_seconds >= 0


def test_get_network_status_classifies_local_vs_external() -> None:
    status = get_network_status()
    assert status.available in (True, False)
    if status.available:
        assert status.local_count >= 0
        assert status.external_count >= 0
        for conn in status.connections:
            assert isinstance(conn.is_local, bool)


# --- Task Router: new targets -------------------------------------------


def _router() -> TaskRouter:
    return TaskRouter(build_default_agent_manager())


def test_router_routes_system_status_question() -> None:
    result = _router().select("What is the current CPU usage?", [])
    assert result.target == "system_monitor"


def test_router_routes_network_status_question() -> None:
    result = _router().select("Check whether this device is reachable.", [])
    assert result.target == "network_monitor"


def test_router_routes_security_status_question() -> None:
    result = _router().select("Is this system sovereign? Where does my data go?", [])
    assert result.target == "security_status"


def test_router_routes_compound_assessment_to_orchestrator() -> None:
    result = _router().select("Assess whether anything looks unusual based on our security policy.", [])
    assert result.target == "orchestrator"


def test_router_normal_agent_requests_unaffected() -> None:
    result = _router().select("There's a bug in this function, can you find the error?", [])
    assert result.target == "agent"
    assert result.agent_id == "code"


# --- /api/chat integration -----------------------------------------------


def test_chat_auto_system_monitor(client: TestClient) -> None:
    response = client.post("/api/chat", json={"message": "What is the current CPU and RAM usage?"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["task_routing"]["target"] == "system_monitor"
    assert body["agent"]["id"] == "system_monitor"
    assert "CPU" in body["response"]
    step_ids = [s["id"] for s in body["execution"]["steps"]]
    assert "collecting_system_info" in step_ids


def test_chat_auto_network_monitor(client: TestClient) -> None:
    response = client.post("/api/chat", json={"message": "Show me my network activity and connections."})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["task_routing"]["target"] == "network_monitor"
    assert body["agent"]["id"] == "network_monitor"


def test_chat_auto_security_status(client: TestClient) -> None:
    response = client.post("/api/chat", json={"message": "What is our data sovereignty status?"})
    assert response.status_code == 200
    body = response.json()
    assert body["task_routing"]["target"] == "security_status"
    assert "LOCAL" in body["response"]


def test_chat_auto_orchestrator_returns_execution_trace(client: TestClient) -> None:
    response = client.post(
        "/api/chat", json={"message": "Assess whether anything looks unusual based on our security policy."}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["task_routing"]["target"] == "orchestrator"
    step_ids = [s["id"] for s in body["execution"]["steps"]]
    assert "collecting_system_info" in step_ids
    assert "analyzing_network" in step_ids
    assert "retrieving_policy" in step_ids
    assert "evaluating_findings" in step_ids
    assert "generating_report" in step_ids
    assert all(s["status"] == "completed" for s in body["execution"]["steps"])


# --- API endpoints ---------------------------------------------------------


def test_system_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/system/status")
    assert response.status_code == 200
    body = response.json()
    assert body["hostname"]
    assert 0.0 <= body["cpu_percent"] <= 100.0


def test_network_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/network/status")
    assert response.status_code == 200
    body = response.json()
    assert "local_count" in body and "external_count" in body


def test_security_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/security/status")
    assert response.status_code == 200
    body = response.json()
    labels = {item["label"] for item in body["items"]}
    assert {"Data Location", "Model", "Vector Store", "External API"} <= labels
    external_api_item = next(i for i in body["items"] if i["label"] == "External API")
    assert external_api_item["value"] == "NOT REQUIRED"
