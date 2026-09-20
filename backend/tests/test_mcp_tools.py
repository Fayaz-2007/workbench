"""Segment 4 — the local MCP tool layer (`app/mcp_tools/`) and its wiring
into Auto mode's system_monitor / network_monitor dispatch.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.mcp_tools import LocalMCPClient, LocalMCPServer, MCPToolNotFoundError, build_local_mcp_client


def test_server_lists_both_required_tools() -> None:
    server = LocalMCPServer()
    names = {spec.name for spec in server.list_tools()}
    assert names == {"get_system_status", "get_active_connections"}


def test_get_system_status_tool_returns_real_values() -> None:
    server = LocalMCPServer()
    result = server.call_tool("get_system_status")
    assert result["hostname"]
    assert result["os"]
    assert 0.0 <= result["cpu_percent"] <= 100.0
    assert 0.0 <= result["memory_percent"] <= 100.0
    assert result["memory_total_gb"] > 0
    assert result["process_count"] > 0
    assert result["uptime_hours"] >= 0


def test_get_active_connections_tool_shape() -> None:
    server = LocalMCPServer()
    result = server.call_tool("get_active_connections")
    assert "connections" in result
    if result["available"]:
        for conn in result["connections"]:
            assert conn["scope"] in ("internal", "external")
            assert conn["port"] is None or isinstance(conn["port"], int)
            assert conn["local_address"]
            assert conn["remote_address"]


def test_unknown_tool_raises() -> None:
    server = LocalMCPServer()
    with pytest.raises(MCPToolNotFoundError):
        server.call_tool("not_a_real_tool")


@pytest.mark.asyncio
async def test_client_wraps_server() -> None:
    client = build_local_mcp_client()
    assert isinstance(client, LocalMCPClient)
    assert set(client.list_tools()) == {"get_system_status", "get_active_connections"}
    result = await client.call_tool("get_system_status")
    assert result["hostname"]


# --- /api/chat integration --------------------------------------------------


def test_chat_system_monitor_goes_through_mcp(client: TestClient) -> None:
    response = client.post("/api/chat", json={"message": "What is the current CPU and RAM usage?"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["task_routing"]["target"] == "system_monitor"
    step_ids = [s["id"] for s in body["execution"]["steps"]]
    assert "calling_mcp_tool" in step_ids
    mcp_step = next(s for s in body["execution"]["steps"] if s["id"] == "calling_mcp_tool")
    assert "get_system_status" in mcp_step["detail"]
    assert "LOCAL" in mcp_step["detail"]


def test_chat_network_monitor_goes_through_mcp(client: TestClient) -> None:
    response = client.post("/api/chat", json={"message": "Show me my network activity and connections."})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["task_routing"]["target"] == "network_monitor"
    step_ids = [s["id"] for s in body["execution"]["steps"]]
    assert "calling_mcp_tool" in step_ids
    mcp_step = next(s for s in body["execution"]["steps"] if s["id"] == "calling_mcp_tool")
    assert "get_active_connections" in mcp_step["detail"]
    assert "LOCAL" in mcp_step["detail"]
