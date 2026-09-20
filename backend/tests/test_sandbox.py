"""SubprocessSandboxProvider: success, stderr/non-zero-exit, and timeout
paths — the three outcomes the Code Agent's verify/revise loop needs to
tell apart.
"""

from __future__ import annotations

import pytest

from app.sandbox.base import ExecutionStatus
from app.sandbox.subprocess_provider import NullSandboxProvider, SubprocessSandboxProvider


@pytest.mark.asyncio
async def test_sandbox_runs_successful_code() -> None:
    provider = SubprocessSandboxProvider()
    result = await provider.run_python("print(2 + 2)", timeout_seconds=10)
    assert result.status == ExecutionStatus.COMPLETED
    assert result.succeeded
    assert result.stdout.strip() == "4"
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_sandbox_captures_stderr_and_nonzero_exit() -> None:
    provider = SubprocessSandboxProvider()
    result = await provider.run_python("raise ValueError('boom')", timeout_seconds=10)
    assert result.status == ExecutionStatus.COMPLETED
    assert not result.succeeded
    assert result.exit_code != 0
    assert "ValueError" in result.stderr


@pytest.mark.asyncio
async def test_sandbox_enforces_timeout() -> None:
    provider = SubprocessSandboxProvider()
    result = await provider.run_python("import time; time.sleep(10)", timeout_seconds=1)
    assert result.status == ExecutionStatus.TIMEOUT
    assert result.timed_out
    assert not result.succeeded


@pytest.mark.asyncio
async def test_sandbox_isolated_mode_blocks_host_env_pythonpath(monkeypatch) -> None:
    """`-I` should mean a host PYTHONPATH pointing at a fake module is
    ignored inside the sandboxed process."""
    monkeypatch.setenv("PYTHONPATH", "/definitely/not/a/real/path")
    provider = SubprocessSandboxProvider()
    result = await provider.run_python("import sys; print('PYTHONPATH' in ''.join(sys.path))", timeout_seconds=10)
    assert result.succeeded
    assert result.stdout.strip() == "False"


@pytest.mark.asyncio
async def test_null_sandbox_reports_unavailable_cleanly() -> None:
    result = await NullSandboxProvider().run_python("print(1)", timeout_seconds=5)
    assert result.status == ExecutionStatus.ERROR
    assert "disabled" in result.stderr.lower()
