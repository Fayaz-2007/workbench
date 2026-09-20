"""Document Generation Tool — writes real deliverable files (DOCX / XLSX /
PDF / Markdown / plain text) into the configured generated-output
directory. Every result carries the metadata the frontend's existing
Deliverable card needs (filename, type, size, creation timestamp, and a
download id — the file's own relative path).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.tools.base import BaseTool, ToolResult, ToolRisk
from app.tools.fs_utils import PathEscapeError, resolve_within

_TYPE_LABELS = {
    "docx": "Word Document",
    "xlsx": "Excel Spreadsheet",
    "pdf": "PDF Document",
    "md": "Markdown Document",
    "txt": "Text File",
}


def _write_docx(target, title: str, content: str) -> None:
    import docx

    document = docx.Document()
    if title:
        document.add_heading(title, level=1)
    for paragraph in content.split("\n\n"):
        document.add_paragraph(paragraph)
    document.save(str(target))


def _write_xlsx(target, title: str, content: str) -> None:
    """Interprets `content` as CSV-ish rows (one line per row, comma-separated)."""
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = (title or "Sheet1")[:31]
    for line in content.splitlines():
        sheet.append([cell.strip() for cell in line.split(",")])
    workbook.save(str(target))


def _write_pdf(target, title: str, content: str) -> None:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    if title:
        pdf.multi_cell(0, 10, title)
        pdf.ln(2)
    pdf.set_font("Helvetica", size=11)
    for paragraph in content.split("\n\n"):
        pdf.multi_cell(0, 7, paragraph)
        pdf.ln(2)
    pdf.output(str(target))


def _write_text(target, title: str, content: str) -> None:
    text = f"{title}\n{'=' * len(title)}\n\n{content}" if title else content
    target.write_text(text, encoding="utf-8")


_WRITERS = {"docx": _write_docx, "xlsx": _write_xlsx, "pdf": _write_pdf, "md": _write_text, "txt": _write_text}


class DocumentGenerationTool(BaseTool):
    name = "document_generation"
    description = "Generates a real DOCX, XLSX, PDF, Markdown, or plain-text deliverable file from provided content."
    capabilities = ["document_generation"]
    risk = ToolRisk.MEDIUM
    network = False

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["filename", "format", "content"],
            "properties": {
                "filename": {"type": "string"},
                "format": {"type": "string", "enum": list(_WRITERS)},
                "title": {"type": "string", "default": ""},
                "content": {"type": "string"},
            },
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        fmt = input.get("format", "")
        writer = _WRITERS.get(fmt)
        if writer is None:
            return ToolResult(success=False, error=f"Unsupported format '{fmt}'. Supported: {', '.join(_WRITERS)}.")

        filename = input.get("filename", "")
        if not filename.lower().endswith(f".{fmt}"):
            filename = f"{filename}.{fmt}"

        settings = get_settings()
        try:
            target = resolve_within(settings.generated_path, filename)
        except PathEscapeError as exc:
            return ToolResult(success=False, error=str(exc))

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            writer(target, input.get("title", ""), input.get("content", ""))
        except Exception as exc:  # noqa: BLE001 - surface any generation failure as a clean tool error
            return ToolResult(success=False, error=f"Document generation failed: {exc}")

        return ToolResult(
            success=True,
            output={
                "id": target.name,
                "filename": target.name,
                "file_type": _TYPE_LABELS.get(fmt, fmt.upper()),
                "size_bytes": target.stat().st_size,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
