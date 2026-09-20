"""The Agent Manager — registers agents and executes the selected one.

This is the only place that turns an `agent_id` string into a concrete
`BaseAgent` instance. The API layer never talks to an agent class directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.base import AgentExecutionResult, AgentTask, BaseAgent, ExecutionContext
from app.core.exceptions import AgentNotFoundError
from app.core.logging import get_logger, log_event

logger = get_logger(__name__)


@dataclass
class AgentInfo:
    id: str
    name: str
    description: str
    capabilities: list[str]


class AgentManager:
    """Registers agents and dispatches execution to the requested one."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.id] = agent
        log_event(logger, "agent_registered", agent_id=agent.id)

    def get(self, agent_id: str) -> BaseAgent:
        try:
            return self._agents[agent_id]
        except KeyError as exc:
            raise AgentNotFoundError(f"Unknown agent '{agent_id}'.", agent_id=agent_id) from exc

    def validate(self, agent_id: str) -> None:
        """Raises `AgentNotFoundError` if `agent_id` is not registered."""
        self.get(agent_id)

    def list(self) -> list[AgentInfo]:
        return [
            AgentInfo(id=a.id, name=a.name, description=a.description, capabilities=list(a.capabilities))
            for a in self._agents.values()
        ]

    async def execute(self, agent_id: str, task: AgentTask, context: ExecutionContext) -> AgentExecutionResult:
        agent = self.get(agent_id)
        log_event(logger, "agent_selected", agent_id=agent_id, conversation_id=context.conversation_id)
        return await agent.execute(task, context)


def build_default_agent_manager() -> AgentManager:
    """Registers the five Segment 2 agents."""
    from app.agents.code import CodeAgent
    from app.agents.data import DataAgent
    from app.agents.document import DocumentAgent
    from app.agents.general import GeneralAgent
    from app.agents.vision import VisionAgent

    manager = AgentManager()
    for agent_cls in (GeneralAgent, CodeAgent, DocumentAgent, VisionAgent, DataAgent):
        manager.register(agent_cls())
    return manager
