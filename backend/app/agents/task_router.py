"""Task Router / Agent Selector — decides **who/what** handles a request
in Auto mode: a specialist agent, a deterministic local-data read (system/
network/security status), or the bounded orchestrator for compound
requests spanning more than one of those.

Strictly separate from the Model Router (`app/models/router.py`), which
decides which *model* a chosen agent uses. The two must never be
conflated — see `backend/README.md`:

    Task Router  -> WHO/WHAT handles the task
    Model Router -> WHICH model an agent uses (only relevant when target == "agent")

Manual mode (the frontend sends a concrete `agent_id`) never touches this
module at all — see `api/routes/chat.py`. Auto mode (no `agent_id`, or the
literal `"auto"`) calls `TaskRouter.select()` once, before dispatch.

Deliberately not a giant keyword dictionary: attachment file type and a
short, explainable phrase list per target are the only signals. Below a
confidence floor, or when nothing matches, it falls back to the General
agent — never crashes, never guesses wildly, and the returned `reason` is
always one plain sentence, never internal scores or chain-of-thought.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.agents.base import AttachmentRef
from app.agents.manager import AgentManager
from app.core.logging import get_logger, log_event

logger = get_logger(__name__)

RoutingTarget = Literal["agent", "system_monitor", "network_monitor", "security_status", "orchestrator"]

_FALLBACK_AGENT_ID = "general"
_CONFIDENCE_FLOOR = 0.15

_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")
_DATA_SUFFIXES = (".csv", ".xlsx")
_DOCUMENT_SUFFIXES = (".pdf", ".docx", ".txt", ".md")

# Compound/assessment phrasing checked first — these combine multiple
# local data sources (system + network + policy) via the orchestrator,
# rather than a single deterministic read.
_ORCHESTRATOR_PHRASES = [
    "security assessment", "assess the security", "assess whether",
    "anything unusual", "security posture", "is everything normal",
    "evaluate security", "check the security status and",
]

# Single-purpose deterministic reads — never routed through an LLM (see
# app/agents/monitor_responses.py).
_SYSTEM_MONITOR_PHRASES = [
    "cpu usage", "ram usage", "memory usage", "disk usage", "system status",
    "uptime", "how much memory", "system information", "cpu and ram", "disk space",
]
_NETWORK_MONITOR_PHRASES = [
    "network activity", "network status", "network connections", "connections",
    "reachable", "is this device reachable", "ip address", "who is connected",
]
_SECURITY_STATUS_PHRASES = [
    "security status", "sovereignty", "is this system sovereign", "where does my data go",
    "data sovereignty", "is my data local", "sovereign status",
]

# Short, explainable phrase lists — enough signal to justify a one-sentence
# reason, not an exhaustive dictionary. Only scored against agents that are
# actually registered (see `select()`).
_AGENT_PHRASES: dict[str, list[str]] = {
    "code": [
        "code", "bug", "error", "traceback", "exception", "function",
        "script", "debug", "python", "javascript", "compile", "refactor", "syntax",
    ],
    "document": [
        "document", "report", "summarize", "summary", "pdf", "manual",
        "policy", "memo", "extract", "paragraph", "draft", "sop",
    ],
    "vision": [
        "image", "photo", "picture", "scan", "drawing", "diagram",
        "visual", "inspect", "photograph", "equipment",
    ],
    "data": [
        "csv", "spreadsheet", "average", "calculate", "statistics",
        "column", "dataset", "mean", "chart", "aggregate", "trend", "reading",
    ],
}

_REASONS: dict[str, str] = {
    "code": "The request involves code, debugging, or a programming task.",
    "document": "The request involves document analysis or summarization.",
    "vision": "The request involves an image or visual inspection.",
    "data": "The request involves data or spreadsheet analysis.",
    "general": "No specific signal was detected; using the general-purpose agent.",
}


@dataclass
class TaskRoutingResult:
    target: RoutingTarget
    agent_id: str  # meaningful when target == "agent"; "general" otherwise (for AgentSummary display)
    reason: str
    confidence: float


class TaskRouter:
    """Selects an execution path for Auto mode. Reads the live agent
    registry from `AgentManager` — never a hard-coded agent list — so an
    "agent" target only ever names an agent that's actually registered.
    """

    def __init__(self, agent_manager: AgentManager) -> None:
        self._agent_manager = agent_manager

    def select(self, message: str, attachments: list[AttachmentRef]) -> TaskRoutingResult:
        lowered = message.lower()

        if any(p in lowered for p in _ORCHESTRATOR_PHRASES):
            return self._finish("orchestrator", _FALLBACK_AGENT_ID, "The request spans multiple local data sources (system, network, and policy) — running the orchestrated assessment.", 0.85)
        if any(p in lowered for p in _SYSTEM_MONITOR_PHRASES):
            return self._finish("system_monitor", _FALLBACK_AGENT_ID, "The request asks about this machine's system resources.", 0.85)
        if any(p in lowered for p in _NETWORK_MONITOR_PHRASES):
            return self._finish("network_monitor", _FALLBACK_AGENT_ID, "The request asks about network connections.", 0.85)
        if any(p in lowered for p in _SECURITY_STATUS_PHRASES):
            return self._finish("security_status", _FALLBACK_AGENT_ID, "The request asks about data sovereignty/security status.", 0.85)

        registered_ids = {a.id for a in self._agent_manager.list()}

        # Attachment file type — strongest, deterministic signal for agent selection.
        for attachment in attachments:
            name = attachment.filename.lower()
            if name.endswith(_IMAGE_SUFFIXES) and "vision" in registered_ids:
                return self._finish("agent", "vision", "An image was attached.", 0.9)
            if name.endswith(_DATA_SUFFIXES) and "data" in registered_ids:
                return self._finish("agent", "data", "A spreadsheet/CSV file was attached.", 0.9)

        # Phrase-overlap scoring against the message text. Normalized by a
        # fixed cap (not by each agent's own phrase-list length) — a single
        # confident hit like "report" must score the same regardless of
        # whether that agent's curated list happens to have 5 or 12
        # entries. Dividing by list length instead (the original formula)
        # silently diluted single-keyword queries — e.g. "report" alone
        # scored 1/12 ≈ 0.08 for Document, well under `_CONFIDENCE_FLOOR`,
        # so "say about the report" fell through to General even though
        # "report" is an unambiguous document-intent signal.
        _SCORE_HIT_CAP = 3
        scores: dict[str, float] = {}
        for agent_id, phrases in _AGENT_PHRASES.items():
            if agent_id not in registered_ids:
                continue
            hits = sum(1 for phrase in phrases if phrase in lowered)
            if hits:
                scores[agent_id] = min(1.0, hits / _SCORE_HIT_CAP)

        # A document-type attachment nudges toward Document Agent, but
        # doesn't override a clearer phrase signal elsewhere.
        if any(a.filename.lower().endswith(_DOCUMENT_SUFFIXES) for a in attachments) and "document" in registered_ids:
            scores["document"] = scores.get("document", 0.0) + 0.3

        if not scores:
            return self._finish("agent", _FALLBACK_AGENT_ID, _REASONS["general"], 0.0)

        best_agent_id, best_score = max(scores.items(), key=lambda kv: kv[1])
        if best_score < _CONFIDENCE_FLOOR or best_agent_id not in registered_ids:
            return self._finish("agent", _FALLBACK_AGENT_ID, _REASONS["general"], best_score)

        return self._finish("agent", best_agent_id, _REASONS.get(best_agent_id, _REASONS["general"]), min(best_score, 1.0))

    def _finish(self, target: RoutingTarget, agent_id: str, reason: str, confidence: float) -> TaskRoutingResult:
        confidence = round(confidence, 3)
        log_event(logger, "task_routed", target=target, agent_id=agent_id, confidence=confidence)
        return TaskRoutingResult(target=target, agent_id=agent_id, reason=reason, confidence=confidence)
