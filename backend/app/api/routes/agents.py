"""GET /api/agents — the agent catalog the frontend's agent selector reads."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.agents.manager import AgentManager
from app.api.dependencies import get_agent_manager
from app.schemas.agent import AgentOut

router = APIRouter(tags=["agents"])


@router.get("/agents", response_model=list[AgentOut])
def list_agents(manager: AgentManager = Depends(get_agent_manager)) -> list[AgentOut]:
    return [AgentOut(id=a.id, name=a.name, description=a.description, capabilities=a.capabilities) for a in manager.list()]
