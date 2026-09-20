"""Aggregates every resource router under a single `/api` prefix."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import admin, agents, chat, deliverables, documents, files, health, models, monitoring, tools

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(agents.router)
api_router.include_router(models.router)
api_router.include_router(chat.router)
api_router.include_router(admin.router)
api_router.include_router(documents.router)
api_router.include_router(tools.router)
api_router.include_router(files.router)
api_router.include_router(deliverables.router)
api_router.include_router(monitoring.router)

__all__ = ["api_router"]
