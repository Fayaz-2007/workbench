"""The tool abstraction.

A tool is a narrow, local capability an agent can invoke — reading a file,
running a calculation, searching the knowledge base. Tools are not agents:
they don't reason, they execute one well-defined operation and return a
structured result. Every tool carries explicit risk/network metadata (used
by `app/tools/registry.py` and, later, Segment 4's security policies) and
none of them have unrestricted host access — see each tool's own module
for its specific restriction (e.g. file tools are confined to the
configured data directories).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel


class ToolRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ToolMetadata(BaseModel):
    name: str
    description: str
    capabilities: list[str]
    risk: ToolRisk
    network: bool
    input_schema: dict[str, Any]


class ToolResult(BaseModel):
    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = {}


class BaseTool(ABC):
    """One local, narrowly-scoped operation an agent can invoke."""

    name: ClassVar[str]
    description: ClassVar[str]
    capabilities: ClassVar[list[str]]
    risk: ClassVar[ToolRisk]
    # Every tool in this system runs fully offline — `network` exists as
    # explicit, checkable metadata (not a switch that turns network on).
    network: ClassVar[bool] = False

    def input_schema(self) -> dict[str, Any]:
        """A minimal JSON-Schema-shaped description of `execute`'s expected
        input dict. Default: any object — override for real validation.
        """
        return {"type": "object"}

    @abstractmethod
    async def execute(self, input: dict[str, Any]) -> ToolResult:
        raise NotImplementedError

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self.name,
            description=self.description,
            capabilities=self.capabilities,
            risk=self.risk,
            network=self.network,
            input_schema=self.input_schema(),
        )
