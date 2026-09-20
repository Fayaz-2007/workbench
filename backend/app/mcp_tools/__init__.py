"""Segment 4 — the local MCP tool layer.

`server.py` owns tool registration/execution; `client.py` is the
caller-facing boundary Auto mode's system/network monitor dispatch goes
through instead of importing `app/monitoring/` directly. See both modules'
docstrings for why this is a minimal, dependency-free stand-in for the
official MCP wire protocol rather than that SDK itself.
"""

from app.mcp_tools.client import LocalMCPClient, build_local_mcp_client
from app.mcp_tools.server import LocalMCPServer, MCPToolNotFoundError, MCPToolSpec

__all__ = ["LocalMCPClient", "LocalMCPServer", "MCPToolNotFoundError", "MCPToolSpec", "build_local_mcp_client"]
