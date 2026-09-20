"""Local tools available to agents.

    Agent -> Tool Registry -> available tools -> Tool execution

Agents never import a tool module directly — they ask the `ToolRegistry`
(see `registry.py`) built here. Every tool is local-only (`network=False`
on every one below) and, where it touches the filesystem, confined to this
application's own data directories (`app/tools/fs_utils.py`).
"""

from __future__ import annotations

from app.rag.service import RAGService
from app.tools.calculator import CalculatorTool
from app.tools.csv_analysis import CSVAnalysisTool
from app.tools.document_generation import DocumentGenerationTool
from app.tools.file_tools import FileReadTool, FileWriteTool, ListFilesTool
from app.tools.knowledge_search import KnowledgeSearchTool
from app.tools.registry import ToolRegistry
from app.tools.report_generation import ReportGenerationTool


def build_default_tool_registry(rag_service: RAGService) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(ListFilesTool())
    registry.register(CalculatorTool())
    registry.register(CSVAnalysisTool())
    registry.register(DocumentGenerationTool())
    registry.register(KnowledgeSearchTool(rag_service))
    registry.register(ReportGenerationTool())
    return registry


__all__ = ["ToolRegistry", "build_default_tool_registry"]
