"""Local system and network monitoring (Phase F) — read-only, local-only.

Everything here reads from `psutil`/the local OS; nothing makes a network
call to any third party. Two small modules: `system.py` (CPU/RAM/disk/host)
and `network.py` (active connections, classified local vs. external —
never a verdict like "malicious", only neutral observed facts).
"""
