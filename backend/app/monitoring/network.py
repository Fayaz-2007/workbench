"""Local network monitoring — active connections, classified local vs.
external by IP range only. Never labels a connection "malicious" or
"suspicious" from IP alone; only neutral, explainable observations (see
`flag_reasons` below) — judgement calls are left to a human.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field

import psutil

# Ports that are unremarkable for a local dev workbench to have open —
# used only to decide whether to note a connection as "uncommon port",
# never to call anything malicious.
_COMMON_PORTS = {80, 443, 22, 53, 123, 3000, 5173, 8000, 8080, 11434}


@dataclass
class ConnectionInfo:
    local_address: str
    remote_address: str | None
    status: str
    is_local: bool
    pid: int | None
    flags: list[str] = field(default_factory=list)


@dataclass
class NetworkStatus:
    available: bool
    detail: str
    local_count: int
    external_count: int
    connections: list[ConnectionInfo]


def _is_local_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback or addr.is_link_local


def _flags_for(remote_port: int | None, status: str) -> list[str]:
    flags: list[str] = []
    if remote_port and remote_port not in _COMMON_PORTS and remote_port < 1024:
        flags.append("uncommon privileged port")
    if status == "SYN_SENT":
        flags.append("connection attempt in progress")
    return flags


def get_network_status(limit: int = 100) -> NetworkStatus:
    try:
        raw = psutil.net_connections(kind="inet")
    except (PermissionError, psutil.AccessDenied):
        return NetworkStatus(
            available=False,
            detail="Network monitoring requires the appropriate system permissions.",
            local_count=0,
            external_count=0,
            connections=[],
        )
    except Exception as exc:  # noqa: BLE001 - never let monitoring crash the app
        return NetworkStatus(available=False, detail=f"Network monitoring unavailable: {exc}", local_count=0, external_count=0, connections=[])

    connections: list[ConnectionInfo] = []
    local_count = 0
    external_count = 0

    for conn in raw:
        if not conn.raddr:
            continue  # listening sockets / no remote peer — not a "connection" to classify
        remote_ip = conn.raddr.ip
        is_local = _is_local_ip(remote_ip)
        if is_local:
            local_count += 1
        else:
            external_count += 1

        connections.append(
            ConnectionInfo(
                local_address=f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "",
                remote_address=f"{remote_ip}:{conn.raddr.port}",
                status=conn.status,
                is_local=is_local,
                pid=conn.pid,
                flags=_flags_for(conn.raddr.port, conn.status),
            )
        )

    connections.sort(key=lambda c: c.is_local, reverse=True)
    return NetworkStatus(
        available=True,
        detail="ok",
        local_count=local_count,
        external_count=external_count,
        connections=connections[:limit],
    )
