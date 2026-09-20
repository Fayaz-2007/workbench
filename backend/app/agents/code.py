"""Code Agent — programming, debugging, and code explanation.

When real inference is active and a sandbox is configured,
`finalize_response` runs a bounded generate -> sandbox -> observe -> revise
-> re-run loop (see `app/agents/loop.py` for the step/timeout budget and
`app/sandbox/` for the execution abstraction) instead of just returning
raw model text. The mock-provider path (`format_response`) is unchanged
from Segment 2.
"""

from __future__ import annotations

import re

from app.agents.base import (
    AgentTask,
    BaseAgent,
    ExecutionContext,
    FinalizedResponse,
    StepStatus,
    response_notice,
)
from app.agents.loop import LoopBudget, StepOutcome
from app.models.base import GenerationResult, ModelInfo, ModelType
from app.models.providers import get_provider
from app.sandbox.base import ExecutionResult

_CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def extract_python_code(text: str) -> str | None:
    match = _CODE_BLOCK_RE.search(text)
    if not match:
        return None
    code = match.group(1).strip()
    return code or None


class CodeAgent(BaseAgent):
    id = "code"
    name = "Code Agent"
    description = "Programming, debugging, code explanation, and coding tasks."
    capabilities = ["coding", "debugging", "code_generation", "code_reasoning"]
    model_type = ModelType.CODE

    async def build_prompt(self, task: AgentTask, context: ExecutionContext) -> str:
        return (
            "You are a precise coding assistant running entirely on local "
            "infrastructure. Prefer Python unless another language is clearly "
            "requested. Return a fenced code block plus a one- or two-sentence "
            "explanation.\n\n"
            f"Request: {task.message}"
        )

    def format_response(self, task: AgentTask, model: ModelInfo, raw: GenerationResult) -> str:
        if raw.is_mock:
            return (
                f"**Code Agent** ({model.name})\n\n"
                f"{response_notice(model, raw)}\n\n"
                f"Request received:\n\n> {task.message.strip() or '(empty message)'}\n\n"
                "Once connected to real inference, this agent will return working code "
                "here instead of a placeholder, e.g.:\n\n"
                "```python\n"
                "def placeholder() -> str:\n"
                '    """Stand-in for real Code Agent output."""\n'
                '    return "real code generation lands in a later segment"\n'
                "```\n\n"
                f"Routed model output:\n\n{raw.text}"
            )
        return f"{raw.text}\n\n---\n{response_notice(model, raw)}"

    async def finalize_response(
        self, task: AgentTask, model: ModelInfo, raw: GenerationResult, context: ExecutionContext, record
    ) -> FinalizedResponse:
        no_sandbox = context.sandbox is None or context.sandbox.name == "none"
        if raw.is_mock or no_sandbox:
            return FinalizedResponse(text=self.format_response(task, model, raw))

        code = extract_python_code(raw.text)
        if not code:
            # Real inference, but nothing that looks like runnable code —
            # return the model's answer as-is rather than forcing a sandbox run.
            return FinalizedResponse(text=f"{raw.text}\n\n---\n{response_notice(model, raw)}")

        settings = context.settings
        timeout = settings.max_execution_seconds if settings else 15
        max_steps = settings.max_agent_steps if settings else 8
        budget = LoopBudget(max_steps=max_steps, timeout_seconds=timeout * 4)

        exec_result = await context.sandbox.run_python(code, timeout_seconds=timeout)
        budget.take_step("run_sandbox", StepOutcome.COMPLETED if exec_result.succeeded else StepOutcome.FAILED)
        record("running_sandbox", StepStatus.COMPLETED if not exec_result.timed_out else StepStatus.FAILED)

        revised = False
        if not exec_result.succeeded and not exec_result.timed_out and not budget.exhausted:
            revised_code = await self._revise(model, code, exec_result)
            budget.take_step("revise_code", StepOutcome.COMPLETED if revised_code else StepOutcome.FAILED)
            record("revising_code", StepStatus.COMPLETED if revised_code else StepStatus.FAILED)

            if revised_code and not budget.exhausted:
                code = revised_code
                exec_result = await context.sandbox.run_python(code, timeout_seconds=timeout)
                budget.take_step("run_sandbox_retry", StepOutcome.COMPLETED if exec_result.succeeded else StepOutcome.FAILED)
                revised = True

        record("verifying_output", StepStatus.COMPLETED if exec_result.succeeded else StepStatus.FAILED)
        return FinalizedResponse(text=self._compose_result(model, raw, code, exec_result, revised, context))

    async def _revise(self, model: ModelInfo, code: str, exec_result: ExecutionResult) -> str | None:
        provider = get_provider(model.provider)
        prompt = (
            "The following Python code failed when run in a sandbox. Fix it.\n\n"
            f"Code:\n```python\n{code}\n```\n\n"
            f"stderr:\n{exec_result.stderr[:2000]}\n\n"
            "Return only a corrected, complete version in a single fenced python code block."
        )
        revised_raw = await provider.generate(model=model, prompt=prompt)
        return extract_python_code(revised_raw.text)

    def _compose_result(
        self,
        model: ModelInfo,
        raw: GenerationResult,
        code: str,
        exec_result: ExecutionResult,
        revised: bool,
        context: ExecutionContext,
    ) -> str:
        if exec_result.timed_out:
            status_line = f"⏱️ Timed out after {exec_result.duration_seconds:.1f}s"
        elif exec_result.succeeded:
            status_line = f"✅ Ran successfully (exit code 0, {exec_result.duration_seconds:.2f}s)"
        else:
            status_line = f"❌ Failed (exit code {exec_result.exit_code}, {exec_result.duration_seconds:.2f}s)"

        parts = [f"**Code Agent** ({model.name})", response_notice(model, raw)]
        if revised:
            parts.append(
                "_The first attempt failed in the sandbox; the code below was "
                "automatically revised once and re-run._"
            )
        parts.append(f"```python\n{code}\n```")
        parts.append(f"**Sandbox result** — {status_line}")
        if exec_result.stdout.strip():
            parts.append(f"stdout:\n```\n{exec_result.stdout.strip()[:4000]}\n```")
        if exec_result.stderr.strip():
            parts.append(f"stderr:\n```\n{exec_result.stderr.strip()[:4000]}\n```")

        isolation = context.sandbox.isolation_level if context.sandbox else "unknown"
        parts.append(f"_Sandbox: `{context.sandbox.name}` — {isolation}._")
        return "\n\n".join(parts)
