"""Knowledge Search Tool — the tool-layer wrapper around `RAGService.search`.

Kept separate from `DocumentAgent` itself (see `app/agents/document.py`):
the agent decides *when* to search and how to use the results; this tool
is just the narrow, reusable "search the local knowledge base" operation
any agent could reach for via the Tool Registry.
"""

from __future__ import annotations

from typing import Any

from app.rag.service import RAGService
from app.tools.base import BaseTool, ToolResult, ToolRisk


class KnowledgeSearchTool(BaseTool):
    name = "knowledge_search"
    description = "Searches the local, ingested document knowledge base for relevant passages."
    capabilities = ["knowledge_search", "document_analysis"]
    risk = ToolRisk.LOW
    network = False

    def __init__(self, rag_service: RAGService) -> None:
        self._rag = rag_service

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 4},
            },
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        query = input.get("query", "")
        if not query.strip():
            return ToolResult(success=False, error="A search query is required.")

        results = await self._rag.search(query, top_k=input.get("top_k"))
        output = [
            {
                "chunk_id": r.chunk.chunk_id,
                "document_id": r.chunk.document_id,
                "filename": r.chunk.filename,
                "page_number": r.chunk.page_number,
                "text": r.chunk.text,
                "score": r.score,
            }
            for r in results
        ]
        return ToolResult(success=True, output=output, metadata={"query": query, "result_count": len(output)})
