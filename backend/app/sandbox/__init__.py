"""Sandboxed code execution for the Code Agent.

    Code Agent -> generated code -> Sandbox -> execution
        -> stdout/stderr/exit code -> Agent -> verify/revise -> result

See `base.py` (the `SandboxProvider` interface — and an honest note on what
"development sandbox" does and doesn't isolate) and
`subprocess_provider.py` (the only implementation today).
"""

from app.sandbox.base import ExecutionResult, ExecutionStatus, SandboxProvider
from app.sandbox.subprocess_provider import get_sandbox_provider

__all__ = ["ExecutionResult", "ExecutionStatus", "SandboxProvider", "get_sandbox_provider"]
