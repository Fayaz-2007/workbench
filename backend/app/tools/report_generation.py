"""Report Generation Tool (Phase I) — assembles a structured report
(task, data sources, findings, AI analysis, citations, sovereignty status,
timestamp) and writes it as a real file via `DocumentGenerationTool` —
reusing the same DOCX/PDF/Markdown writers, not duplicating them.

Observed facts and AI-generated interpretation are kept in clearly
separate sections, never blended into one paragraph.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.tools.base import BaseTool, ToolResult, ToolRisk
from app.tools.document_generation import DocumentGenerationTool

_SUPPORTED_FORMATS = ("md", "docx", "pdf")


def _build_content(payload: dict[str, Any]) -> str:
    sources = payload.get("data_sources") or []
    citations = payload.get("citations") or []
    sections = [
        f"## Task\n{payload.get('task', '')}",
        "## Data Sources\n" + ("\n".join(f"- {s}" for s in sources) if sources else "- None specified"),
        f"## Findings (observed facts)\n{payload.get('findings', '(none recorded)')}",
        f"## AI Analysis (interpretation)\n{payload.get('ai_analysis', '(none recorded)')}",
        "## Sources / Citations\n" + ("\n".join(f"- {c}" for c in citations) if citations else "- None"),
        f"## Data Sovereignty\n{payload.get('sovereignty_status', 'LOCAL — no data or model prompt left this machine.')}",
        f"## Generated\n{datetime.now(UTC).isoformat()}",
    ]
    return "\n\n".join(sections)


class ReportGenerationTool(BaseTool):
    name = "report_generation"
    description = "Assembles a structured task/findings/analysis report and writes it as a real DOCX/PDF/Markdown file."
    capabilities = ["document_generation", "reporting"]
    risk = ToolRisk.MEDIUM
    network = False

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["title", "task"],
            "properties": {
                "title": {"type": "string"},
                "task": {"type": "string"},
                "data_sources": {"type": "array", "items": {"type": "string"}},
                "findings": {"type": "string"},
                "ai_analysis": {"type": "string"},
                "citations": {"type": "array", "items": {"type": "string"}},
                "sovereignty_status": {"type": "string"},
                "format": {"type": "string", "enum": list(_SUPPORTED_FORMATS), "default": "md"},
            },
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        fmt = input.get("format", "md")
        if fmt not in _SUPPORTED_FORMATS:
            return ToolResult(success=False, error=f"Unsupported report format '{fmt}'. Supported: {', '.join(_SUPPORTED_FORMATS)}.")

        title = input.get("title", "Sovereign AI Workbench Report")
        content = _build_content(input)
        filename = input.get("title", "report").lower().replace(" ", "_")[:60]

        return await DocumentGenerationTool().execute(
            {"filename": filename, "format": fmt, "title": title, "content": content}
        )
