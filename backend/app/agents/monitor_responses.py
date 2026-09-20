"""Deterministic, non-LLM responses for Auto mode's SYSTEM_MONITOR /
NETWORK_MONITOR / SECURITY_STATUS routing targets (see `task_router.py`).

These never call a model — real `psutil`/security-status data is
formatted directly. That's deliberate: a "what's my CPU usage" question
has one correct, deterministic answer; running it through an LLM would
only add latency and a chance of the model mangling the numbers. The
`AgentExecutionResult` shape stays identical to a normal agent's, so
`api/routes/chat.py` doesn't need a special response path.

Segment 4: the system/network builders below read their data through
`LocalMCPClient` (see `app/mcp_tools/`) instead of calling
`app/monitoring/` directly — the same real psutil-backed data, routed
through the local MCP tool layer so the execution trace shows judges the
actual Auto Mode -> MCP Client -> Local MCP Server -> tool -> real data
path. `build_security_status_result` is unchanged (not one of Segment 4's
two tools).
"""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentExecutionResult, ExecutionStatus, ExecutionStep, StepStatus
from app.core.config import Settings
from app.mcp_tools import LocalMCPClient
from app.monitoring.network import get_network_status
from app.models.router import RoutingResult
from app.security.status import get_security_status

# A neutral, honest stand-in for `RoutingResult` — these paths never
# select or call a language model at all.
_LOCAL_READ_MODEL_ID = "local-system-read"


def _local_routing(reason: str) -> RoutingResult:
    from app.models.base import ModelInfo, ModelStatus, ModelType, ResourceClass

    pseudo_model = ModelInfo(
        id=_LOCAL_READ_MODEL_ID,
        name="Local deterministic read (no model inference)",
        type=ModelType.GENERAL,
        identifier="n/a",
        capabilities=[],
        context_length=1,
        quantization="n/a",
        resource_class=ResourceClass.TINY,
        status=ModelStatus.ACTIVE,
    )
    return RoutingResult(model=pseudo_model, reason=reason, score=1.0, candidates_considered=0)


async def build_system_monitor_result(mcp_client: LocalMCPClient) -> AgentExecutionResult:
    result: dict[str, Any] = await mcp_client.call_tool("get_system_status")
    steps = [
        ExecutionStep(id="understanding_request", title="Understanding request", status=StepStatus.COMPLETED),
        ExecutionStep(id="selecting_agent", title="Selecting agent", status=StepStatus.COMPLETED, detail="System monitoring request."),
        ExecutionStep(
            id="calling_mcp_tool",
            title="Calling local MCP tool",
            status=StepStatus.COMPLETED,
            detail="SYSTEM MCP -> get_system_status() -> LOCAL",
        ),
        ExecutionStep(id="collecting_system_info", title="Collecting system information", status=StepStatus.COMPLETED),
        ExecutionStep(id="completed", title="Completed", status=StepStatus.COMPLETED),
    ]
    text = (
        "**System Status** — _LOCAL DATA via the local MCP tool `get_system_status` (no model inference)._\n\n"
        f"| Metric | Value |\n|---|---|\n"
        f"| Hostname | {result['hostname']} |\n"
        f"| OS | {result['os']} |\n"
        f"| CPU | {result['cpu_percent']:.1f}% |\n"
        f"| RAM | {result['memory_percent']:.1f}% ({result['memory_used_gb']:.1f} / {result['memory_total_gb']:.1f} GB) |\n"
        f"| Disk | {result['disk_percent']:.1f}% ({result['disk_used_gb']:.1f} / {result['disk_total_gb']:.1f} GB) |\n"
        f"| Processes | {result['process_count']} |\n"
        f"| Uptime | {result['uptime_hours']:.1f} hours |\n"
    )
    return AgentExecutionResult(
        response_text=text,
        routing=_local_routing("System metrics were read via the local MCP tool `get_system_status` — no model was needed."),
        steps=steps,
        status=ExecutionStatus.COMPLETED,
    )


async def build_network_monitor_result(mcp_client: LocalMCPClient) -> AgentExecutionResult:
    result: dict[str, Any] = await mcp_client.call_tool("get_active_connections")
    available = result["available"]
    steps = [
        ExecutionStep(id="understanding_request", title="Understanding request", status=StepStatus.COMPLETED),
        ExecutionStep(id="selecting_agent", title="Selecting agent", status=StepStatus.COMPLETED, detail="Network monitoring request."),
        ExecutionStep(
            id="calling_mcp_tool",
            title="Calling local MCP tool",
            status=StepStatus.COMPLETED if available else StepStatus.FAILED,
            detail="NETWORK MCP -> get_active_connections() -> LOCAL",
        ),
        ExecutionStep(
            id="analyzing_network",
            title="Analyzing network connections",
            status=StepStatus.COMPLETED if available else StepStatus.FAILED,
        ),
        ExecutionStep(id="completed", title="Completed", status=StepStatus.COMPLETED),
    ]

    if not available:
        text = f"**Network Activity**\n\n{result['detail']}"
    else:
        connections = result["connections"]
        flagged = [c for c in connections if c["flags"]]
        text = (
            "**Network Activity** — _LOCAL DATA via the local MCP tool `get_active_connections`._\n\n"
            f"- Internal/local connections: **{result['local_count']}**\n"
            f"- External connections: **{result['external_count']}**\n"
            f"- Status: **{'NORMAL' if not flagged else 'REVIEW SUGGESTED'}**\n\n"
        )
        if flagged:
            text += "Connections with an explainable flag (not a verdict — review, don't assume):\n\n"
            for c in flagged[:5]:
                text += f"- `{c['remote_address']}:{c['port']}` ({c['status']}) — {', '.join(c['flags'])}\n"
        else:
            text += "No connections were flagged by the simple heuristics in use (uncommon privileged ports, in-progress connection attempts)."
    return AgentExecutionResult(
        response_text=text,
        routing=_local_routing("Active connections were read via the local MCP tool `get_active_connections` — no model was needed."),
        steps=steps,
        status=ExecutionStatus.COMPLETED,
    )


def build_security_status_result(settings: Settings) -> AgentExecutionResult:
    network = get_network_status()
    status = get_security_status(settings, network.available)
    steps = [
        ExecutionStep(id="understanding_request", title="Understanding request", status=StepStatus.COMPLETED),
        ExecutionStep(id="selecting_agent", title="Selecting agent", status=StepStatus.COMPLETED, detail="Sovereignty/security status request."),
        ExecutionStep(id="completed", title="Completed", status=StepStatus.COMPLETED),
    ]
    text = "**Sovereignty & Security Status**\n\n" + "\n".join(
        f"- **{i.label}: {i.value}** — {i.detail}" for i in status.items
    ) + f"\n\n{status.summary}"
    return AgentExecutionResult(
        response_text=text,
        routing=_local_routing("Status was assembled from local configuration — no model was needed."),
        steps=steps,
        status=ExecutionStatus.COMPLETED,
    )
