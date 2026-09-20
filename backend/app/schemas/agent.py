"""API schemas for agent metadata."""

from __future__ import annotations

from pydantic import BaseModel


class AgentOut(BaseModel):
    id: str
    name: str
    description: str
    capabilities: list[str]
