"""API schemas for generated deliverables."""

from __future__ import annotations

from pydantic import BaseModel


class DeliverableOut(BaseModel):
    id: str
    filename: str
    size_bytes: int
    created_at: str
