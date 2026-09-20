"""LocalMCPClient — the caller-facing half of Segment 4's MCP boundary.

Every caller (today: Auto mode's system/network monitor dispatch, see
`app/agents/monitor_responses.py`) goes through this client rather than
`LocalMCPServer` directly, reproducing the client/server separation a real
MCP transport would have. `call_tool` is `async` for that reason too — the
call site awaits it exactly as it would await a real network/stdio round
trip — even though today's implementation is an in-process, synchronous
call. Swapping in an actual transport later is confined to this file and
`server.py`; nothing else imports `LocalMCPServer`.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger, log_event
from app.mcp_tools.server import LocalMCPServer

logger = get_logger(__name__)


class LocalMCPClient:
    def __init__(self, server: LocalMCPServer) -> None:
        self._server = server

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        log_event(logger, "mcp_client_call", tool_name=name)
        return self._server.call_tool(name, arguments)

    def list_tools(self) -> list[str]:
        return [spec.name for spec in self._server.list_tools()]


def build_local_mcp_client() -> LocalMCPClient:
    return LocalMCPClient(LocalMCPServer())
