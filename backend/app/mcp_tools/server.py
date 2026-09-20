"""Local MCP-style tool server — Segment 4.

A minimal, dependency-free stand-in for the Model Context Protocol's
tool-serving role (list tools / call tool by name), scoped to this
segment's two local tools. It is deliberately NOT the official MCP SDK/
wire protocol (no JSON-RPC, no stdio/SSE transport): that would pull in
~13 new transitive dependencies and force a pydantic upgrade for what is,
functionally, two local psutil reads — a poor trade against this
project's "no unnecessary dependencies, keep it minimal and stable" rule.
What's preserved is the *architecture* the segment asks for: a distinct
server that owns tool registration/execution, reached only through a
client (`client.py`), so swapping in a real transport later is a change
confined to those two files — nothing that calls `LocalMCPClient` would
need to change.

Both tools wrap the *existing* `app/monitoring/` readers — no new data
source, no duplicated psutil logic. This module only adapts their output
to the tool contracts described in the Segment 4 spec (flat dicts with
the field names judges were shown, not the internal dataclasses).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.exceptions import WorkbenchError
from app.core.logging import get_logger, log_event
from app.monitoring.network import get_network_status
from app.monitoring.system import get_system_status

logger = get_logger(__name__)


class MCPToolNotFoundError(WorkbenchError):
    code = "mcp_tool_not_found"
    status_code = 404
    default_message = "Unknown MCP tool."


@dataclass
class MCPToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})


def _split_host_port(address: str | None) -> tuple[str, int | None]:
    """"ip:port" -> (ip, port). Tolerant of IPv6 (only the last ":"-segment
    is treated as the port) and of the missing/blank case.
    """
    if not address or ":" not in address:
        return address or "", None
    host, _, port = address.rpartition(":")
    try:
        return host, int(port)
    except ValueError:
        return address, None


def get_system_status_tool() -> dict[str, Any]:
    """`get_system_status` — real CPU/RAM/disk/host data via `psutil`,
    reused as-is from `app/monitoring/system.py` (never re-read or
    guessed here); only the field names are adapted to the tool contract.
    """
    status = get_system_status()
    return {
        "cpu_percent": status.cpu_percent,
        "memory_used_gb": status.ram_used_gb,
        "memory_total_gb": status.ram_total_gb,
        "memory_percent": status.ram_percent,
        "disk_percent": status.disk_percent,
        "disk_used_gb": status.disk_used_gb,
        "disk_total_gb": status.disk_total_gb,
        "os": status.operating_system,
        "hostname": status.hostname,
        "uptime_hours": round(status.uptime_seconds / 3600, 1),
        "process_count": status.process_count,
    }


def get_active_connections_tool() -> dict[str, Any]:
    """`get_active_connections` — real active connections via `psutil`,
    reused as-is from `app/monitoring/network.py`. `scope` is a neutral
    local/external classification only, never a verdict — see
    `app/monitoring/network.py` for the same rule.
    """
    status = get_network_status()
    if not status.available:
        return {"connections": [], "available": False, "detail": status.detail}

    connections = []
    for conn in status.connections:
        local_ip, _ = _split_host_port(conn.local_address)
        remote_ip, remote_port = _split_host_port(conn.remote_address)
        connections.append(
            {
                "local_address": local_ip,
                "remote_address": remote_ip,
                "port": remote_port,
                "protocol": "tcp",
                "status": conn.status,
                "scope": "internal" if conn.is_local else "external",
                "flags": conn.flags,
            }
        )
    return {
        "connections": connections,
        "available": True,
        "local_count": status.local_count,
        "external_count": status.external_count,
    }


class LocalMCPServer:
    """Owns tool registration + execution — the "server" half of the
    Segment 4 MCP flow.
    """

    def __init__(self) -> None:
        self._specs: dict[str, MCPToolSpec] = {}
        self._handlers: dict[str, Callable[[], dict[str, Any]]] = {}
        self._register(
            MCPToolSpec(name="get_system_status", description="Real local CPU/RAM/disk/host status, read via psutil."),
            get_system_status_tool,
        )
        self._register(
            MCPToolSpec(
                name="get_active_connections",
                description="Real local active network connections, classified local vs. external (not a security verdict).",
            ),
            get_active_connections_tool,
        )
        log_event(logger, "mcp_server_initialized", tools=list(self._specs))

    def _register(self, spec: MCPToolSpec, handler: Callable[[], dict[str, Any]]) -> None:
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler

    def list_tools(self) -> list[MCPToolSpec]:
        return list(self._specs.values())

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if name not in self._handlers:
            raise MCPToolNotFoundError(f"Unknown MCP tool '{name}'.", tool_name=name)
        log_event(logger, "mcp_tool_called", tool_name=name)
        return self._handlers[name]()
