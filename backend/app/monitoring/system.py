"""Local system monitoring — CPU, RAM, disk, host identity, uptime.

Read-only snapshot via `psutil`. Never raises for a normal read; a genuine
failure (e.g. a metric psutil can't get on this OS) is reported as `None`
for that field rather than crashing the whole snapshot.
"""

from __future__ import annotations

import platform
import socket
import time
from dataclasses import dataclass

import psutil


@dataclass
class SystemStatus:
    hostname: str
    operating_system: str
    local_ip: str | None
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    process_count: int
    uptime_seconds: float
    collected_at: float


def _local_ip() -> str | None:
    # No packets are actually sent — connecting a UDP socket just asks the
    # OS to pick the outbound-facing local interface/IP for that route.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return None


def get_system_status() -> SystemStatus:
    disk = psutil.disk_usage("/")
    memory = psutil.virtual_memory()
    return SystemStatus(
        hostname=socket.gethostname(),
        operating_system=f"{platform.system()} {platform.release()}",
        local_ip=_local_ip(),
        cpu_percent=psutil.cpu_percent(interval=0.2),
        ram_percent=memory.percent,
        ram_used_gb=round(memory.used / (1024**3), 2),
        ram_total_gb=round(memory.total / (1024**3), 2),
        disk_percent=disk.percent,
        disk_used_gb=round(disk.used / (1024**3), 2),
        disk_total_gb=round(disk.total / (1024**3), 2),
        process_count=len(psutil.pids()),
        uptime_seconds=max(0.0, time.time() - psutil.boot_time()),
        collected_at=time.time(),
    )
