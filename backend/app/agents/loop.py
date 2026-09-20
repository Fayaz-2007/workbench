"""A bounded budget for multi-step agent loops (PLAN -> ACT -> OBSERVE ->
DECIDE -> ... -> COMPLETE/FAILED).

Deliberately **not** an unbounded autonomous loop: every loop is built
around a `LoopBudget` with a hard step ceiling *and* a wall-clock timeout.
Reaching either stops the loop safely — the caller gets `exhausted=True`
back and returns whatever it has, never hangs or spins forever. Today only
`CodeAgent` uses this (generate -> sandbox -> observe -> revise -> re-run,
see `app/agents/code.py`), but the abstraction has no Code-Agent-specific
concept in it, so any future multi-step agent can reuse it directly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum


class StepOutcome(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LoopStepRecord:
    step_number: int
    action: str
    outcome: StepOutcome
    detail: str = ""


@dataclass
class LoopBudget:
    max_steps: int
    timeout_seconds: float
    _started_at: float = field(default_factory=time.perf_counter, init=False, repr=False)
    _steps_taken: int = field(default=0, init=False)
    history: list[LoopStepRecord] = field(default_factory=list, init=False)

    @property
    def steps_taken(self) -> int:
        return self._steps_taken

    @property
    def exhausted(self) -> bool:
        return self._steps_taken >= self.max_steps or self._elapsed() > self.timeout_seconds

    def _elapsed(self) -> float:
        return time.perf_counter() - self._started_at

    def take_step(self, action: str, outcome: StepOutcome, detail: str = "") -> None:
        """Records one step. Callers should check `exhausted` *before*
        calling this for the next step — this only records, it doesn't
        enforce (enforcement happens at the call site so the caller can
        decide what "stop safely" means for its own workflow).
        """
        self._steps_taken += 1
        self.history.append(LoopStepRecord(step_number=self._steps_taken, action=action, outcome=outcome, detail=detail))
