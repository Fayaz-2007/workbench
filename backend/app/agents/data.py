"""Data Agent — CSV, spreadsheet, and data-analysis tasks.

Numerical results come from the deterministic CSV Analysis Tool
(`app/tools/csv_analysis.py`, real pandas statistics), not the LLM's own
arithmetic. `build_prompt` runs the tool over any attached CSV/XLSX file
*before* generation so the model explains real, computed numbers rather
than guessing them; `finalize_response` records that as an explicit step.
"""

from __future__ import annotations

from app.agents.base import (
    AgentTask,
    BaseAgent,
    ExecutionContext,
    FinalizedResponse,
    StepStatus,
    response_notice,
)
from app.models.base import GenerationResult, ModelInfo, ModelType
from app.tools.csv_analysis import CSVAnalysisTool

_ANALYZABLE_SUFFIXES = (".csv", ".xlsx")


def _find_table_attachment(task: AgentTask):
    for attachment in task.attachments:
        if attachment.path and attachment.filename.lower().endswith(_ANALYZABLE_SUFFIXES):
            return attachment
    return None


class DataAgent(BaseAgent):
    id = "data"
    name = "Data Agent"
    description = "CSV, spreadsheet, and data-analysis tasks."
    capabilities = ["data_analysis", "tabular_reasoning", "statistics"]
    model_type = ModelType.DATA

    async def build_prompt(self, task: AgentTask, context: ExecutionContext) -> str:
        context.tool_result = None
        attachment = _find_table_attachment(task)

        if attachment and attachment.path:
            result = await CSVAnalysisTool().execute({"path": attachment.path, "root": "uploads"})
            if result.success:
                context.tool_result = {"tool": "csv_analysis", "filename": attachment.filename, "output": result.output}
                return (
                    "You are a data analysis assistant running entirely on local "
                    "infrastructure. The statistics below were computed deterministically "
                    "(not by you) — explain what they mean for the user's question; do not "
                    "recompute or contradict them.\n\n"
                    f"Computed statistics for `{attachment.filename}`:\n{result.output}\n\n"
                    f"User: {task.message}"
                )
            context.tool_result = {"tool": "csv_analysis", "filename": attachment.filename, "error": result.error}
            return (
                "You are a data analysis assistant running entirely on local "
                f"infrastructure. Analysis of the attached file failed ({result.error}) — "
                "explain that plainly rather than inventing numbers.\n\n"
                f"User: {task.message}"
            )

        return (
            "You are a data analysis assistant running entirely on local "
            "infrastructure. No CSV/XLSX file is attached — explain what analysis "
            "would answer the user's question without inventing specific numbers.\n\n"
            f"User: {task.message}"
        )

    def format_response(self, task: AgentTask, model: ModelInfo, raw: GenerationResult) -> str:
        attachment_note = (
            f" with {len(task.attachments)} attached file(s)" if task.attachments else ""
        )
        if raw.is_mock:
            return (
                f"**Data Agent** ({model.name})\n\n"
                f"{response_notice(model, raw)}\n\n"
                f"Request received{attachment_note}:\n\n> {task.message.strip() or '(empty message)'}\n\n"
                "Real spreadsheet/tabular analysis is not implemented yet — this "
                "agent only demonstrates that Data requests route to a "
                "data-analysis-capable model.\n\n"
                f"Routed model output:\n\n{raw.text}"
            )
        return f"{raw.text}\n\n---\n{response_notice(model, raw)}"

    async def finalize_response(
        self, task: AgentTask, model: ModelInfo, raw: GenerationResult, context: ExecutionContext, record
    ) -> FinalizedResponse:
        if raw.is_mock:
            return FinalizedResponse(text=self.format_response(task, model, raw))

        text = f"{raw.text}\n\n---\n{response_notice(model, raw)}"
        if context.tool_result is not None:
            ok = "error" not in context.tool_result
            record("running_analysis", StepStatus.COMPLETED if ok else StepStatus.FAILED)
            if ok:
                filename = context.tool_result["filename"]
                text = (
                    f"_Statistics computed deterministically from `{filename}` via the "
                    f"CSV Analysis Tool (pandas) — not estimated by the model._\n\n{text}"
                )
        return FinalizedResponse(text=text)
