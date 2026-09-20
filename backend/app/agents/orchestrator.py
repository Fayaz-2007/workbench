"""Bounded multi-step orchestration for compound requests that span more
than one local data source — e.g. "assess the security status of this
machine". Not LangGraph: a small, explicit, sequential step sequence,
which is all a *bounded* (never autonomous/unbounded) workflow like this
needs. See `app/agents/loop.py` for the same step/timeout-budget
philosophy used elsewhere (Code Agent's sandbox loop).

    collect system info -> analyze network -> retrieve policy (RAG)
        -> evaluate findings -> synthesize via local model -> report

Every step is recorded on the same `ExecutionStep` list agents use, so the
frontend's execution UI needs no special case for "this was an
orchestration, not a single agent call".
"""

from __future__ import annotations

from app.agents.base import (
    AgentExecutionResult,
    AgentTask,
    CitationRef,
    ExecutionContext,
    ExecutionStatus,
    ExecutionStep,
    StepStatus,
    development_notice,
    real_inference_notice,
)
from app.core.exceptions import NoSuitableModelError
from app.core.logging import get_logger, log_event
from app.models.base import ModelType
from app.models.providers import get_provider
from app.models.router import RoutingRequest
from app.monitoring.network import get_network_status
from app.monitoring.system import get_system_status

logger = get_logger(__name__)


async def run_security_assessment(task: AgentTask, context: ExecutionContext) -> AgentExecutionResult:
    steps: list[ExecutionStep] = []

    def record(step_id: str, status: StepStatus, detail: str | None = None) -> None:
        from app.agents.base import STEP_TITLES

        steps.append(ExecutionStep(id=step_id, title=STEP_TITLES[step_id], status=status, detail=detail))

    log_event(logger, "orchestration_started", workflow="security_assessment", conversation_id=context.conversation_id)

    record("understanding_request", StepStatus.COMPLETED)
    record("selecting_agent", StepStatus.COMPLETED, detail="Compound request — running the bounded security-assessment orchestrator.")

    system = get_system_status()
    record(
        "collecting_system_info",
        StepStatus.COMPLETED,
        detail=f"CPU {system.cpu_percent:.0f}%, RAM {system.ram_percent:.0f}%, disk {system.disk_percent:.0f}%.",
    )

    network = get_network_status()
    record(
        "analyzing_network",
        StepStatus.COMPLETED if network.available else StepStatus.FAILED,
        detail=(
            f"{network.local_count} local, {network.external_count} external connection(s)."
            if network.available
            else network.detail
        ),
    )

    citations: list[CitationRef] = []
    policy_context = ""
    if context.rag_service is not None:
        query = task.message.strip() or "security policy"
        results = await context.rag_service.search(query, top_k=3)
        if results:
            policy_context = "\n\n".join(f"[{r.chunk.filename}] {r.chunk.text}" for r in results)
            citations = [
                CitationRef(
                    id=r.chunk.chunk_id,
                    label=f"{r.chunk.filename}" + (f" (p.{r.chunk.page_number})" if r.chunk.page_number else ""),
                    source=r.chunk.source_path,
                )
                for r in results
            ]
            record("retrieving_policy", StepStatus.COMPLETED, detail=f"{len(results)} relevant passage(s) found in the local knowledge base.")
        else:
            record("retrieving_policy", StepStatus.COMPLETED, detail="No relevant policy found in the local knowledge base.")
    else:
        record("retrieving_policy", StepStatus.COMPLETED, detail="No knowledge base configured.")

    flagged = [c for c in network.connections if c.flags] if network.available else []
    record(
        "evaluating_findings",
        StepStatus.COMPLETED,
        detail=f"{len(flagged)} connection(s) with an explainable flag." if network.available else "Network data unavailable.",
    )

    routing_request = RoutingRequest(
        agent_id="orchestrator",
        required_capabilities=["reasoning", "document_analysis"],
        preferred_type=ModelType.GENERAL,
    )
    try:
        routing = context.model_router.route(routing_request)
    except NoSuitableModelError:
        record("generating_report", StepStatus.FAILED, detail="No suitable local model is currently available.")
        raise

    # Whether a metric crosses a concerning level is decided here, in code
    # — not left for the model to eyeball, the same reasoning the CSV/data
    # agent uses for statistics. A small local model asked to compare raw
    # numbers against a policy's stated thresholds is prone to inventing a
    # violation that isn't there; a pre-computed, labeled finding forecloses
    # that failure mode instead of merely warning against it.
    cpu_finding = (
        f"CPU usage is {system.cpu_percent:.0f}%, which IS above a high-load concern level (85%)."
        if system.cpu_percent >= 85
        else f"CPU usage is {system.cpu_percent:.0f}%, which is NOT above a high-load concern level (85%) — this is normal."
    )
    connection_finding = (
        f"{len(flagged)} connection(s) were flagged by the review heuristics — this IS worth noting."
        if flagged
        else "0 connections were flagged by the review heuristics — no unusual connection was found."
    )

    provider = get_provider(routing.model.provider)
    prompt = (
        "You are a security assessment assistant summarizing local findings for a plain-language "
        "report. The findings below are the ONLY facts you may state — they were computed by code, "
        "not by you. Do not invent additional facts, do not claim a threshold was crossed unless the "
        "matching finding below explicitly says so, and do not claim data left this machine — "
        "everything here was read and processed locally.\n\n"
        f"Finding — system load: {cpu_finding} RAM is at {system.ram_percent:.0f}%, disk at {system.disk_percent:.0f}%, "
        f"{system.process_count} processes, uptime {system.uptime_seconds / 3600:.1f}h.\n"
        f"Finding — network: {network.local_count} local and {network.external_count} external connections. {connection_finding}\n"
        f"Relevant organizational policy excerpt: {policy_context or 'none found in the local knowledge base.'}\n\n"
        f"User's request: {task.message or 'Assess whether anything looks unusual.'}\n\n"
        "Write a short assessment (3-5 sentences) grounded only in the findings above."
    )
    raw = await provider.generate(model=routing.model, prompt=prompt)
    record("generating_report", StepStatus.COMPLETED)
    record("completed", StepStatus.COMPLETED)

    notice = development_notice() if raw.is_mock else real_inference_notice(routing.model)
    text = (
        f"**Security Assessment** — _LOCAL DATA: system + network read directly from this machine; "
        f"policy retrieved from the local knowledge base._\n\n{notice}\n\n{raw.text}\n\n---\n"
        f"**Observed data**\n"
        f"- System: CPU {system.cpu_percent:.0f}% · RAM {system.ram_percent:.0f}% · Disk {system.disk_percent:.0f}%\n"
        f"- Network: {network.local_count} local / {network.external_count} external connection(s)"
        + (f", {len(flagged)} flagged" if flagged else "")
    )

    log_event(logger, "orchestration_completed", workflow="security_assessment", conversation_id=context.conversation_id)
    return AgentExecutionResult(
        response_text=text,
        routing=routing,
        steps=steps,
        status=ExecutionStatus.COMPLETED,
        citations=citations,
    )
