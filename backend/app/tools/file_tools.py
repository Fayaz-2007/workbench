"""File Read / Write / List tools.

Every one of these is confined to the application's own configured data
directories (`app/core/config.py`'s `upload_dir` / `documents_dir` /
`generated_dir`) via `resolve_within` — never an arbitrary host path, and
never outside `backend/data/`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.tools.base import BaseTool, ToolResult, ToolRisk
from app.tools.fs_utils import PathEscapeError, RootName, resolve_within, root_path as _root_path

_MAX_READ_BYTES = 200_000  # generous for text/markdown/source files; large binaries are rejected


class FileReadTool(BaseTool):
    name = "file_read"
    description = "Reads a text file from the workbench's local uploads, documents, or generated directory."
    capabilities = ["local_file_read"]
    risk = ToolRisk.LOW
    network = False

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "Path relative to `root`."},
                "root": {"type": "string", "enum": ["uploads", "documents", "generated"], "default": "uploads"},
            },
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        settings = get_settings()
        root: RootName = input.get("root", "uploads")
        try:
            target = resolve_within(_root_path(settings, root), input.get("path", ""))
        except PathEscapeError as exc:
            return ToolResult(success=False, error=str(exc))

        if not target.exists() or not target.is_file():
            return ToolResult(success=False, error=f"File not found: {input.get('path')}")
        if target.stat().st_size > _MAX_READ_BYTES:
            return ToolResult(success=False, error=f"File exceeds the {_MAX_READ_BYTES // 1000}KB read limit.")

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return ToolResult(success=False, error=f"Could not read file: {exc}")

        return ToolResult(
            success=True,
            output=content,
            metadata={"path": str(target.relative_to(_root_path(settings, root))), "size_bytes": target.stat().st_size},
        )


class FileWriteTool(BaseTool):
    name = "file_write"
    description = "Writes a text file into the workbench's local generated-output directory."
    capabilities = ["local_file_write"]
    risk = ToolRisk.MEDIUM
    network = False

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["path", "content"],
            "properties": {
                "path": {"type": "string", "description": "Path relative to the generated-output directory."},
                "content": {"type": "string"},
            },
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        settings = get_settings()
        try:
            target = resolve_within(settings.generated_path, input.get("path", ""))
        except PathEscapeError as exc:
            return ToolResult(success=False, error=str(exc))

        content = input.get("content", "")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            return ToolResult(success=False, error=f"Could not write file: {exc}")

        return ToolResult(
            success=True,
            output={"path": str(target.relative_to(settings.generated_path))},
            metadata={"size_bytes": len(content.encode("utf-8")), "written_at": datetime.now(UTC).isoformat()},
        )


class ListFilesTool(BaseTool):
    name = "list_files"
    description = "Lists files in the workbench's local uploads, documents, or generated directory."
    capabilities = ["local_file_read"]
    risk = ToolRisk.LOW
    network = False

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"root": {"type": "string", "enum": ["uploads", "documents", "generated"], "default": "uploads"}},
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        settings = get_settings()
        root: RootName = input.get("root", "uploads")
        root_path = _root_path(settings, root)
        root_path.mkdir(parents=True, exist_ok=True)

        entries = [
            {"name": p.name, "size_bytes": p.stat().st_size, "modified_at": datetime.fromtimestamp(p.stat().st_mtime, UTC).isoformat()}
            for p in sorted(root_path.iterdir())
            if p.is_file()
        ]
        return ToolResult(success=True, output=entries, metadata={"root": root, "count": len(entries)})
