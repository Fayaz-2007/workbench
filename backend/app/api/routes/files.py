"""POST /api/files/upload, GET /api/files/{id} — local file storage.

Uploaded bytes are saved under `UPLOAD_DIR` only (never elsewhere on the
host) and never leave this process — no cloud storage, no external call.
The returned `path` is what a chat request's `attachments[].path` should
echo back so agents/tools (CSV analysis, RAG ingestion) can read the real
file — see `app/agents/base.py`'s `AttachmentRef`.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse

from app.api.dependencies import get_app_settings
from app.core.config import Settings
from app.core.exceptions import InvalidRequestError, ResourceNotFoundError
from app.schemas.files import UploadedFileOut
from app.tools.fs_utils import PathEscapeError, resolve_within

router = APIRouter(tags=["files"])

_TYPE_LABELS = {
    "pdf": "PDF Document",
    "docx": "Word Document",
    "xlsx": "Excel Spreadsheet",
    "csv": "CSV File",
    "pptx": "PowerPoint Presentation",
    "png": "PNG Image",
    "jpg": "JPEG Image",
    "jpeg": "JPEG Image",
    "txt": "Text File",
    "md": "Markdown Document",
    "py": "Python Script",
    "cpp": "C++ Source",
    "c": "C Source",
    "js": "JavaScript File",
    "ts": "TypeScript File",
}


@router.post("/files/upload", response_model=UploadedFileOut)
async def upload_file(file: UploadFile, settings: Settings = Depends(get_app_settings)) -> UploadedFileOut:
    original_name = Path(file.filename or "upload").name  # strip any path components
    extension = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    if extension not in _TYPE_LABELS:
        raise InvalidRequestError(
            f"Unsupported file type '.{extension}'. Supported: {', '.join(sorted(_TYPE_LABELS))}.",
            extension=extension,
        )

    data = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise InvalidRequestError(f"File exceeds the {settings.max_upload_mb}MB upload limit.", size_bytes=len(data))

    stored_name = f"{uuid4().hex}_{original_name}"
    target = resolve_within(settings.upload_path, stored_name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)

    return UploadedFileOut(
        id=stored_name,
        filename=original_name,
        file_type=_TYPE_LABELS[extension],
        size_bytes=len(data),
        path=stored_name,
    )


@router.get("/files/{file_id}")
async def download_file(file_id: str, settings: Settings = Depends(get_app_settings)) -> FileResponse:
    try:
        target = resolve_within(settings.upload_path, file_id)
    except PathEscapeError as exc:
        raise InvalidRequestError(str(exc)) from exc

    if not target.exists() or not target.is_file():
        raise ResourceNotFoundError(f"File '{file_id}' was not found.")

    # Strip the uuid-prefix this endpoint's own upload handler added, so the
    # browser downloads with the user's original filename.
    display_name = file_id.split("_", 1)[1] if "_" in file_id else file_id
    return FileResponse(path=target, filename=display_name)
