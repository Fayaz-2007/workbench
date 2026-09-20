"""GET /api/system/status, /api/network/status, /api/security/status.

Read-only, local-only snapshots — see `app/monitoring/` and
`app/security/status.py`. These also back the Admin System/Network/
Security pages and Auto-mode's SYSTEM_MONITOR/NETWORK_MONITOR routing
(see `app/agents/task_router.py`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_app_settings
from app.core.config import Settings
from app.monitoring.network import get_network_status
from app.monitoring.system import get_system_status
from app.schemas.monitoring import NetworkStatusOut, SecurityStatusOut, SystemStatusOut
from app.security.status import get_security_status

router = APIRouter(tags=["monitoring"])


@router.get("/system/status", response_model=SystemStatusOut)
def system_status() -> SystemStatusOut:
    status = get_system_status()
    return SystemStatusOut(**status.__dict__)


@router.get("/network/status", response_model=NetworkStatusOut)
def network_status() -> NetworkStatusOut:
    status = get_network_status()
    return NetworkStatusOut(
        available=status.available,
        detail=status.detail,
        local_count=status.local_count,
        external_count=status.external_count,
        connections=[
            {
                "local_address": c.local_address,
                "remote_address": c.remote_address,
                "status": c.status,
                "is_local": c.is_local,
                "flags": c.flags,
            }
            for c in status.connections
        ],
    )


@router.get("/security/status", response_model=SecurityStatusOut)
def security_status(settings: Settings = Depends(get_app_settings)) -> SecurityStatusOut:
    network = get_network_status()
    status = get_security_status(settings, network.available)
    return SecurityStatusOut(items=[i.__dict__ for i in status.items], summary=status.summary)
