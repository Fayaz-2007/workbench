"""API schemas for the Tool Registry."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.tools.base import ToolRisk


class ToolOut(BaseModel):
    name: str
    description: str
    capabilities: list[str]
    risk: ToolRisk
    network: bool
    input_schema: dict[str, Any]


class ToolExecuteRequest(BaseModel):
    tool_name: str
    input: dict[str, Any] = {}


class ToolExecuteResponse(BaseModel):
    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = {}
