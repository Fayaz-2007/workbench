"""API schemas for system/network/security status."""

from __future__ import annotations

from pydantic import BaseModel


class SystemStatusOut(BaseModel):
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


class ConnectionOut(BaseModel):
    local_address: str
    remote_address: str | None
    status: str
    is_local: bool
    flags: list[str]


class NetworkStatusOut(BaseModel):
    available: bool
    detail: str
    local_count: int
    external_count: int
    connections: list[ConnectionOut]


class SecurityStatusItemOut(BaseModel):
    label: str
    value: str
    detail: str


class SecurityStatusOut(BaseModel):
    items: list[SecurityStatusItemOut]
    summary: str
