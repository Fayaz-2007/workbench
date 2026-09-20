"""API schemas for the admin overview endpoint.

Only what Segment 2 actually backs (model counts, a light in-memory
activity feed) is here. Network/system/audit-log endpoints are deferred —
the Admin Network, System, and Audit Logs pages keep using frontend mock
data until a later segment adds real telemetry.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ActivityEntry(BaseModel):
    id: str
    timestamp: str
    action: str
    resource: str
    status: Literal["success", "failure", "pending"] = "success"


class AdminOverview(BaseModel):
    system_status: Literal["development", "operational", "degraded", "offline"] = "development"
    external_connections: Literal["not_connected", "connected", "unknown"] = "not_connected"
    active_sessions: int | None = None
    models_online: int | None = None
    models_total: int | None = None
    recent_activity: list[ActivityEntry] = []
