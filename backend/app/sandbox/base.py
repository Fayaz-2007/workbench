"""Sandboxed code execution — the abstraction.

    Code Agent -> generated code -> Sandbox -> execution
        -> stdout / stderr / exit code -> Agent -> verify/revise -> result

**No generated code is ever run directly on the host.** Every execution
goes through a `SandboxProvider`. `SubprocessSandboxProvider` (the only
implementation today — see `subprocess_provider.py`) is a *development*
sandbox: a timeout-bounded, resource-limited-on-a-best-effort-basis
subprocess in an isolated temp directory. That is a real safety boundary,
but it is **not** container/VM isolation — it shares the host kernel and
cannot be treated as a hard security boundary against a truly adversarial
payload. A container-backed `SandboxProvider` (Docker/gVisor/Firecracker)
belongs here later, behind the same interface, once that runtime is
available — nothing above this abstraction would need to change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum

from pydantic import BaseModel


class ExecutionStatus(StrEnum):
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"


class ExecutionResult(BaseModel):
    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_seconds: float = 0.0
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        return self.status == ExecutionStatus.COMPLETED and self.exit_code == 0


class SandboxProvider(ABC):
    """Runs untrusted, agent-generated code and reports what happened —
    never raises for a failing *program* (non-zero exit, exception,
    timeout are all normal `ExecutionResult`s); only raises for a sandbox
    infrastructure failure itself.
    """

    name: str = "base"
    # Honest self-description of the isolation strength — surfaced to the
    # frontend/API so it is never confused with a hardened container
    # sandbox. See module docstring.
    isolation_level: str = "none"

    @abstractmethod
    async def run_python(self, code: str, *, timeout_seconds: int, stdin: str = "") -> ExecutionResult:
        raise NotImplementedError
