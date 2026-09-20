"""API schemas for file upload."""

from __future__ import annotations

from pydantic import BaseModel


class UploadedFileOut(BaseModel):
    id: str
    filename: str
    file_type: str
    size_bytes: int
    # Relative path within the uploads directory — what a chat request's
    # `attachments[].path` should echo back so agents/tools can read the
    # real file (see app/agents/base.py's AttachmentRef).
    path: str
