"""GET /api/deliverables, GET /api/deliverables/{id} — files the
Document Generation Tool wrote to `GENERATED_DIR` (see
`app/tools/document_generation.py`). Read-only: nothing here writes.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api.dependencies import get_app_settings
from app.core.config import Settings
from app.core.exceptions import ResourceNotFoundError
from app.schemas.deliverables import DeliverableOut
from app.tools.fs_utils import PathEscapeError, resolve_within

router = APIRouter(prefix="/deliverables", tags=["deliverables"])


@router.get("", response_model=list[DeliverableOut])
def list_deliverables(settings: Settings = Depends(get_app_settings)) -> list[DeliverableOut]:
    settings.generated_path.mkdir(parents=True, exist_ok=True)
    return [
        DeliverableOut(
            id=p.name,
            filename=p.name,
            size_bytes=p.stat().st_size,
            created_at=datetime.fromtimestamp(p.stat().st_mtime, UTC).isoformat(),
        )
        for p in sorted(settings.generated_path.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
        if p.is_file()
    ]


@router.get("/{deliverable_id}")
def download_deliverable(deliverable_id: str, settings: Settings = Depends(get_app_settings)) -> FileResponse:
    try:
        target = resolve_within(settings.generated_path, deliverable_id)
    except PathEscapeError as exc:
        raise ResourceNotFoundError(str(exc)) from exc

    if not target.exists() or not target.is_file():
        raise ResourceNotFoundError(f"Deliverable '{deliverable_id}' was not found.")
    return FileResponse(path=target, filename=target.name)
