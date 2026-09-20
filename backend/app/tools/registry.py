"""The Tool Registry — where agents look up available tools by name.

Mirrors `AgentManager` / `ModelRegistry`'s shape deliberately: register,
get, list. Agents never import a tool module directly; they ask the
registry, so which tools exist (and their risk/network metadata) stays in
one place for Segment 4's security policies to govern later.
"""

from __future__ import annotations

from app.core.exceptions import WorkbenchError
from app.core.logging import get_logger, log_event
from app.tools.base import BaseTool, ToolMetadata

logger = get_logger(__name__)


class ToolNotFoundError(WorkbenchError):
    code = "tool_not_found"
    status_code = 404
    default_message = "Unknown tool."


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        log_event(logger, "tool_registered", tool_name=tool.name, risk=tool.risk.value)

    def get(self, name: str) -> BaseTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"Unknown tool '{name}'.", tool_name=name) from exc

    def list(self) -> list[ToolMetadata]:
        return [tool.metadata() for tool in self._tools.values()]

    def list_for_capabilities(self, capabilities: list[str]) -> list[BaseTool]:
        """Tools sharing at least one capability — how an agent discovers
        what it's allowed to reach for, without hard-coding tool names.
        """
        wanted = set(capabilities)
        return [t for t in self._tools.values() if wanted & set(t.capabilities)]
