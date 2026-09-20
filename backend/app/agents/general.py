"""General Agent — everyday reasoning, questions, and assistance."""

from __future__ import annotations

from app.agents.base import AgentTask, BaseAgent, ExecutionContext, response_notice
from app.models.base import GenerationResult, ModelInfo, ModelType


class GeneralAgent(BaseAgent):
    id = "general"
    name = "General Agent"
    description = "General reasoning, questions, and everyday assistance."
    capabilities = ["reasoning", "text_generation", "question_answering"]
    model_type = ModelType.GENERAL

    async def build_prompt(self, task: AgentTask, context: ExecutionContext) -> str:
        return (
            "You are a helpful, concise general-purpose assistant running "
            "entirely on the user's own local infrastructure. Answer clearly.\n\n"
            f"User: {task.message}"
        )

    def format_response(self, task: AgentTask, model: ModelInfo, raw: GenerationResult) -> str:
        if raw.is_mock:
            return (
                f"**General Agent** ({model.name})\n\n"
                f"{response_notice(model, raw)}\n\n"
                f"Once connected to real inference, this agent will reason over your "
                f"message directly:\n\n> {task.message.strip() or '(empty message)'}\n\n"
                f"Routed model output:\n\n{raw.text}"
            )
        return f"{raw.text}\n\n---\n{response_notice(model, raw)}"
