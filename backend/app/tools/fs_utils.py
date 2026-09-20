"""Shared path-safety helper for every file-touching tool.

Every file tool is confined to one of the application's own configured
data directories (`uploads`, `documents`, `generated`) — never an
arbitrary host path. `resolve_within` is the single choke point that
enforces that; nothing in `app/tools/` builds a filesystem path any other
way.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from app.core.config import Settings

RootName = Literal["uploads", "documents", "generated"]


class PathEscapeError(ValueError):
    """Raised when a requested path would resolve outside its allowed root."""


def root_path(settings: "Settings", root: RootName) -> Path:
    """The configured directory a file tool's `root` selector refers to."""
    return {
        "uploads": settings.upload_path,
        "documents": settings.documents_path,
        "generated": settings.generated_path,
    }[root]


def resolve_within(root: Path, relative: str) -> Path:
    if not relative or not relative.strip():
        raise PathEscapeError("A path is required.")

    normalized = PurePosixPath(relative.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        raise PathEscapeError(f"Path must be relative and may not contain '..': {relative!r}")

    root_resolved = root.resolve()
    candidate = (root_resolved / str(normalized)).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise PathEscapeError(f"Path escapes the allowed directory: {relative!r}") from exc
    return candidate
