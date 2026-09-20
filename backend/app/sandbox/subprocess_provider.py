"""Development sandbox: a timeout-bounded subprocess in a throwaway
working directory.

**Honest about what this is not:** this isolates *working directory* and
*wall-clock time*, and runs Python in isolated mode (`-I`, ignoring the
host's `PYTHONPATH`/site config). It does **not** enforce OS-level
filesystem or network restriction — a sufficiently determined payload can
still see the rest of the filesystem and reach the network, because doing
either safely and portably (Windows + Linux, no Docker) is a real,
separate engineering problem, not something to fake with a comment. This
provider exists to make the *architecture* (Code Agent -> Sandbox ->
result -> verify/revise) real and testable now; a container-backed
provider (Docker/gVisor/Firecracker) implementing the same
`SandboxProvider` interface is what should carry real untrusted workloads
in production. See `SandboxProvider.isolation_level`.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from app.core.logging import get_logger, log_event
from app.sandbox.base import ExecutionResult, ExecutionStatus, SandboxProvider

logger = get_logger(__name__)

_MAX_OUTPUT_CHARS = 20_000

# A minimal environment — deliberately does not forward the host's own
# PYTHONPATH/env so the executed script can't quietly import host-installed
# packages or read unrelated environment variables.
_MINIMAL_ENV_KEYS = ("SYSTEMROOT", "PATH", "TEMP", "TMP") if os.name == "nt" else ("PATH",)


class SubprocessSandboxProvider(SandboxProvider):
    name = "subprocess"
    isolation_level = "process-only — isolated cwd + timeout; filesystem/network are NOT OS-restricted (see module docstring)"

    async def run_python(self, code: str, *, timeout_seconds: int, stdin: str = "") -> ExecutionResult:
        work_dir = Path(tempfile.gettempdir()) / "sovereign-ai-sandbox" / uuid4().hex
        work_dir.mkdir(parents=True, exist_ok=True)
        script_path = work_dir / "main.py"
        script_path.write_text(code, encoding="utf-8")

        env = {k: os.environ[k] for k in _MINIMAL_ENV_KEYS if k in os.environ}
        started = time.perf_counter()

        # Run via a blocking `subprocess.run` on a worker thread rather than
        # `asyncio.create_subprocess_exec`. Uvicorn's `--reload` supervisor
        # sets `WindowsSelectorEventLoopPolicy` for its worker process on
        # Windows, and the selector event loop does not implement subprocess
        # transports there (`NotImplementedError` on every launch attempt).
        # `subprocess.run` in a thread sidesteps the event loop entirely, so
        # it works the same under any policy/platform.
        def _run_blocking() -> subprocess.CompletedProcess[bytes]:
            return subprocess.run(
                [
                    sys.executable,
                    "-I",  # isolated mode: ignore PYTHONPATH / user site packages
                    "-B",  # don't write .pyc files
                    str(script_path),
                ],
                cwd=str(work_dir),
                env=env,
                input=stdin.encode("utf-8") if stdin else None,
                capture_output=True,
                timeout=timeout_seconds,
            )

        exit_code: int | None = None
        timed_out = False
        try:
            completed = await asyncio.to_thread(_run_blocking)
            stdout_bytes, stderr_bytes = completed.stdout, completed.stderr
            exit_code = completed.returncode
            duration = time.perf_counter() - started
            status = ExecutionStatus.COMPLETED
        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - started
            stdout_bytes, stderr_bytes = exc.stdout or b"", exc.stderr or b""
            status = ExecutionStatus.TIMEOUT
            timed_out = True
        except OSError as exc:
            log_event(logger, "sandbox_launch_failed", error=str(exc))
            self._cleanup(work_dir)
            return ExecutionResult(status=ExecutionStatus.ERROR, stderr=f"Could not start sandbox process: {exc}")
        finally:
            self._cleanup(work_dir)

        stdout = stdout_bytes.decode("utf-8", errors="replace")[:_MAX_OUTPUT_CHARS]
        stderr = stderr_bytes.decode("utf-8", errors="replace")[:_MAX_OUTPUT_CHARS]

        log_event(
            logger,
            "sandbox_execution_completed",
            status=status.value,
            exit_code=exit_code,
            duration_seconds=round(duration, 3),
            timed_out=timed_out,
        )
        return ExecutionResult(
            status=status,
            stdout=stdout,
            stderr=stderr or ("Execution timed out." if timed_out else ""),
            exit_code=exit_code,
            duration_seconds=duration,
            timed_out=timed_out,
        )

    @staticmethod
    def _cleanup(work_dir: Path) -> None:
        try:
            for child in work_dir.iterdir():
                child.unlink(missing_ok=True)
            work_dir.rmdir()
        except OSError:
            pass  # best-effort cleanup only


class NullSandboxProvider(SandboxProvider):
    """Used when `SANDBOX_PROVIDER=none` — reports unavailable, cleanly."""

    name = "none"
    isolation_level = "disabled"

    async def run_python(self, code: str, *, timeout_seconds: int, stdin: str = "") -> ExecutionResult:
        return ExecutionResult(status=ExecutionStatus.ERROR, stderr="Sandboxed execution is disabled (SANDBOX_PROVIDER=none).")


_provider: SandboxProvider | None = None


def get_sandbox_provider() -> SandboxProvider:
    global _provider
    if _provider is not None:
        return _provider

    from app.core.config import get_settings

    settings = get_settings()
    _provider = SubprocessSandboxProvider() if settings.sandbox_provider == "subprocess" else NullSandboxProvider()
    return _provider
