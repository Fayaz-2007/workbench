"""Conversation -> document export pipeline.

    Outline (1 LLM call, strict JSON, retry-then-fallback)
        -> Section writing (1 LLM call per section, sequential — RAM budget)
        -> Deterministic extras (Q&A log, code blocks, references, metadata)
        -> Quality check (expand thin sections, bounded)
        -> Render (docx/pptx/xlsx/pdf — see renderers.py)
        -> Save under GENERATED_DIR

One function, `export_conversation()`, is the single entry point both the
natural-language chat path (`app/api/routes/chat.py`) and the dedicated
`POST /api/conversations/{id}/export` route (`app/api/routes/conversations.py`)
call — no duplicated generation logic between the two triggers.

Grounding rule enforced throughout: every prompt tells the model to use
ONLY the conversation transcript and never invent facts, numbers, or names
— the same discipline `app/agents/document.py` and `app/agents/orchestrator.py`
already apply elsewhere in this codebase.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.agents.base import (
    DeliverableRef,
    ExecutionStep,
    StepStatus,
    development_notice,
    real_inference_notice,
)
from app.agents.loop import LoopBudget, StepOutcome
from app.core.config import Settings
from app.core.exceptions import InvalidRequestError
from app.core.logging import get_logger, log_event
from app.models.base import GenerationResult, ModelInfo, ModelType
from app.models.providers import get_provider
from app.models.router import ModelRouter, RoutingRequest, RoutingResult
from app.services.conversation_export.intent import ExportFormat
from app.services.conversation_export.outline import normalize_outline
from app.services.conversation_export.renderers import TYPE_LABELS, render_document
from app.services.conversation_export.spec import (
    CodeBlock,
    DocumentMetadata,
    DocumentSpec,
    QAEntry,
    ReferenceEntry,
    SectionSpec,
)
from app.tools.fs_utils import resolve_within

logger = get_logger(__name__)

# ---- Tunables --------------------------------------------------------------

_MIN_WORDS_FOR_DOCX_PDF = 1200
_MAX_EXPANSION_CALLS = 3
# A generous bound on the whole outline+section+expansion loop (see
# `app/agents/loop.py`) — realistic runs take ~10-13 steps (1-2 outline
# calls + up to 8 sections + up to 3 expansions), so this almost never
# actually triggers; it exists as a genuine safety net, not a routine limit.
_MAX_LOOP_STEPS = 20
_LOOP_TIMEOUT_SECONDS = 300.0
_NO_CONTENT_FALLBACK = "No specific items were discussed on this topic."
# Conversation transcripts get large fast on an 8k-32k context model; this
# keeps every prompt bounded regardless of how long the chat has run.
_MAX_TRANSCRIPT_CHARS = 6000
_TRANSCRIPT_TRUNCATION_MARKER = "\n\n[... earlier messages omitted for length ...]\n\n"

_DEFAULT_OUTLINE_SECTIONS = [
    {"heading": "Executive Summary", "focus": "a brief high-level summary of the whole conversation"},
    {"heading": "Background & Context", "focus": "what the conversation was about and why it started"},
    {"heading": "Key Discussion Points", "focus": "the main topics and questions raised"},
    {"heading": "Detailed Analysis", "focus": "the substantive reasoning, explanations, or analysis given"},
    {"heading": "Findings / Answers Provided", "focus": "concrete answers, results, or information provided"},
    {"heading": "Decisions & Recommendations", "focus": "any decisions made or recommendations given"},
    {"heading": "Action Items / Next Steps", "focus": "follow-up actions or next steps mentioned"},
    {"heading": "Conclusion", "focus": "a short closing summary"},
]

_CODE_FENCE_RE = re.compile(r"```([\w+-]*)\n(.*?)```", re.DOTALL)
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_SENTENCE_END_RE = re.compile(r"[.!?](?:\s|$)")


@dataclass
class ExportMessage:
    role: str  # "user" | "assistant"
    text: str
    citations: list[str] = field(default_factory=list)


@dataclass
class ExportResult:
    deliverable: DeliverableRef
    steps: list[ExecutionStep]
    routing: RoutingResult
    response_text: str
    is_mock: bool


# ---- Deterministic helpers (no LLM) ----------------------------------------


def _strip_notice(text: str) -> str:
    """Best-effort removal of this app's own response-footer notices
    (`development_notice()` / `real_inference_notice()`, see
    `app/agents/base.py`) before an answer is condensed into the Q&A log —
    the notice is about provenance, not conversation content.
    """
    return text.split("\n\n---\n")[0].strip()


def _truncate_at_sentence(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    window = text[:max_chars]
    matches = list(_SENTENCE_END_RE.finditer(window))
    if matches:
        return window[: matches[-1].end()].strip()
    return window.strip() + "…"


def build_transcript_text(messages: list[ExportMessage]) -> str:
    lines = []
    for msg in messages:
        if not msg.text.strip():
            continue
        speaker = "User" if msg.role == "user" else "Assistant"
        lines.append(f"{speaker}: {_strip_notice(msg.text).strip()}")
    transcript = "\n\n".join(lines)
    if len(transcript) <= _MAX_TRANSCRIPT_CHARS:
        return transcript
    half = _MAX_TRANSCRIPT_CHARS // 2
    return transcript[:half] + _TRANSCRIPT_TRUNCATION_MARKER + transcript[-half:]


def build_qa_log(messages: list[ExportMessage]) -> list[QAEntry]:
    entries: list[QAEntry] = []
    for i, msg in enumerate(messages):
        if msg.role != "user" or not msg.text.strip():
            continue
        answer = next((m for m in messages[i + 1 :] if m.role == "assistant"), None)
        if answer is None or not answer.text.strip():
            continue
        condensed = _truncate_at_sentence(_strip_notice(answer.text), 600)
        entries.append(QAEntry(question=msg.text.strip(), answer=condensed))
    return entries


def extract_code_blocks(messages: list[ExportMessage]) -> list[CodeBlock]:
    blocks: list[CodeBlock] = []
    for msg in messages:
        for match in _CODE_FENCE_RE.finditer(msg.text):
            language, code = match.group(1), match.group(2).strip("\n")
            if code.strip():
                blocks.append(CodeBlock(language=language, code=code))
    return blocks


def build_references(messages: list[ExportMessage]) -> list[ReferenceEntry]:
    seen: dict[str, ReferenceEntry] = {}
    for msg in messages:
        for label in msg.citations:
            if label and label not in seen:
                seen[label] = ReferenceEntry(label=label)
    return list(seen.values())


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return (slug or "conversation-export")[:60]


def parse_section_text(raw: str) -> tuple[list[str], list[str]]:
    bullets: list[str] = []
    paragraphs: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            paragraphs.append(" ".join(buffer))
            buffer.clear()

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if stripped[0] in "-*•" and len(stripped) > 1:
            bullets.append(stripped.lstrip("-*•").strip())
        else:
            buffer.append(stripped)
    flush()
    return paragraphs, bullets


def _parse_outline_json(raw: str) -> dict | None:
    candidate = raw.strip()
    fence_match = _JSON_FENCE_RE.search(candidate)
    if fence_match:
        candidate = fence_match.group(1).strip()

    for text in (candidate, candidate[candidate.find("{") : candidate.rfind("}") + 1]):
        if not text:
            continue
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        sections = data.get("sections")
        if isinstance(sections, list) and sections and all(
            isinstance(s, dict) and s.get("heading") for s in sections
        ):
            return data
    return None


# ---- LLM-driven steps -------------------------------------------------------


async def _generate_outline(provider, model: ModelInfo, transcript: str) -> tuple[dict, bool, bool]:
    """Returns `(outline_dict, is_mock, used_fallback)`."""
    base_prompt = (
        "You are outlining a document that summarizes the chat conversation transcript below. "
        "Respond with STRICT JSON only — no prose, no markdown code fences — matching exactly "
        'this shape: {"title": str, "subtitle": str, "sections": [{"heading": str, "focus": str}, ...]}. '
        "Aim for 6 to 8 sections that cover what was actually discussed (e.g. background, key points, "
        "findings, decisions, next steps, conclusion — adapted to the real content below). Base the "
        "title, subtitle, and every section only on the transcript; never invent a topic that wasn't "
        "discussed.\n\nConversation transcript:\n"
        f"{transcript}"
    )

    raw: GenerationResult = await provider.generate(model=model, prompt=base_prompt)
    parsed = _parse_outline_json(raw.text)
    if parsed is not None:
        return parsed, raw.is_mock, False

    retry_prompt = base_prompt + "\n\nReturn ONLY valid JSON. No prose before or after it, no markdown fences."
    raw_retry: GenerationResult = await provider.generate(model=model, prompt=retry_prompt)
    parsed_retry = _parse_outline_json(raw_retry.text)
    if parsed_retry is not None:
        return parsed_retry, raw_retry.is_mock, False

    log_event(logger, "outline_json_fallback_used", model_id=model.id)
    return (
        {"title": "Conversation Summary", "subtitle": "", "sections": _DEFAULT_OUTLINE_SECTIONS},
        raw_retry.is_mock,
        True,
    )


async def _write_section(
    provider, model: ModelInfo, heading: str, focus: str, transcript: str, is_padded: bool = False
) -> SectionSpec:
    padded_instruction = (
        " This section was added to round out the document's structure and may have nothing to do "
        f"with what was actually discussed — if the transcript has nothing relevant to '{focus}', "
        f'respond with exactly this one sentence and nothing else: "{_NO_CONTENT_FALLBACK}"'
        if is_padded
        else ""
    )
    prompt = (
        f"You are drafting one section, titled '{heading}', of a document that summarizes the chat "
        f"conversation transcript below. This section's focus: {focus}. Use ONLY information found in "
        "the transcript — never invent facts, numbers, or names that are not present. Write 2-4 short "
        "paragraphs, OR one short paragraph followed by 3-6 bullet points that are each a full sentence "
        f"(never a 3-4 word fragment). Do not repeat the section heading in your answer.{padded_instruction}\n\n"
        f"Conversation transcript:\n{transcript}"
    )
    raw = await provider.generate(model=model, prompt=prompt)
    paragraphs, bullets = parse_section_text(raw.text)
    if not paragraphs and not bullets:
        paragraphs = [_NO_CONTENT_FALLBACK] if is_padded else paragraphs
    return SectionSpec(heading=heading, paragraphs=paragraphs, bullets=bullets)


async def _expand_section(
    provider, model: ModelInfo, section: SectionSpec, focus: str, transcript: str
) -> SectionSpec:
    existing = "\n".join(section.paragraphs + [f"- {b}" for b in section.bullets])
    prompt = (
        f"The section below, titled '{section.heading}' (focus: {focus}), is too short. Using ONLY the "
        "conversation transcript, add 2-3 more full-sentence paragraphs or bullet points that expand on "
        "it — do not repeat what's already written, and do not invent facts.\n\n"
        f"Already written:\n{existing}\n\n"
        f"Conversation transcript:\n{transcript}"
    )
    raw = await provider.generate(model=model, prompt=prompt)
    extra_paragraphs, extra_bullets = parse_section_text(raw.text)
    section.paragraphs += extra_paragraphs
    section.bullets += extra_bullets
    return section


# ---- Orchestration -----------------------------------------------------------


async def export_conversation(
    messages: list[ExportMessage],
    fmt: ExportFormat,
    *,
    model_router: ModelRouter,
    settings: Settings,
    conversation_id: str,
) -> ExportResult:
    real_messages = [m for m in messages if m.text.strip()]
    if not real_messages:
        raise InvalidRequestError("Nothing to export yet — send a few messages first.")

    steps: list[ExecutionStep] = []

    def step(step_id: str, title: str, status: StepStatus, detail: str | None = None) -> None:
        steps.append(ExecutionStep(id=step_id, title=title, status=status, detail=detail))

    step("understanding_request", "Understanding request", StepStatus.COMPLETED)

    routing_request = RoutingRequest(
        agent_id="conversation_export",
        required_capabilities=["reasoning", "summarization", "document_analysis"],
        preferred_type=ModelType.GENERAL,
        task_excerpt=f"Export {len(real_messages)}-message conversation as {fmt}",
    )
    routing = model_router.route(routing_request)
    step("selecting_model", "Selecting local model", StepStatus.COMPLETED, detail=routing.reason)

    provider = get_provider(routing.model.provider)
    model = routing.model
    transcript = build_transcript_text(real_messages)
    budget = LoopBudget(max_steps=_MAX_LOOP_STEPS, timeout_seconds=_LOOP_TIMEOUT_SECONDS)

    outline, is_mock, used_fallback = await _generate_outline(provider, model, transcript)
    budget.take_step("outline", StepOutcome.COMPLETED)
    raw_sections = outline.get("sections") or _DEFAULT_OUTLINE_SECTIONS
    outline_sections, outline_padded = normalize_outline(raw_sections)
    outline_source = "fallback" if used_fallback else ("model+padded" if outline_padded else "model")
    log_event(
        logger,
        "outline_normalized",
        outline_source=outline_source,
        outline_padded=outline_padded,
        section_count=len(outline_sections),
    )
    step(
        "outlining_document",
        "Outlining document",
        StepStatus.COMPLETED,
        detail=f"{len(outline_sections)} section(s) planned ({outline_source}).",
    )

    sections: list[SectionSpec] = []
    for i, entry in enumerate(outline_sections, start=1):
        heading = str(entry.get("heading", f"Section {i}"))
        focus = str(entry.get("focus", heading))
        is_padded = bool(entry.get("padded", False))

        if budget.exhausted:
            section = SectionSpec(heading=heading, paragraphs=[_NO_CONTENT_FALLBACK])
            detail = f"{heading} (loop budget exhausted — used placeholder)"
        else:
            section = await _write_section(provider, model, heading, focus, transcript, is_padded)
            budget.take_step("write_section", StepOutcome.COMPLETED, detail=heading)
            detail = heading
        sections.append(section)
        step(
            f"writing_section_{i}",
            f"Writing section {i}/{len(outline_sections)}",
            StepStatus.COMPLETED,
            detail=detail,
        )

    expansions_used = 0
    if fmt in ("docx", "pdf"):
        total_words = sum(s.word_count() for s in sections)
        while (
            total_words < _MIN_WORDS_FOR_DOCX_PDF
            and expansions_used < _MAX_EXPANSION_CALLS
            and sections
            and not budget.exhausted
        ):
            thinnest = min(sections, key=lambda s: s.word_count())
            focus = next(
                (str(e.get("focus", thinnest.heading)) for e in outline_sections if e.get("heading") == thinnest.heading),
                thinnest.heading,
            )
            before = thinnest.word_count()
            await _expand_section(provider, model, thinnest, focus, transcript)
            budget.take_step("expand_section", StepOutcome.COMPLETED, detail=thinnest.heading)
            expansions_used += 1
            total_words += thinnest.word_count() - before
        if expansions_used:
            step(
                "expanding_sections",
                "Expanding thin sections",
                StepStatus.COMPLETED,
                detail=f"{expansions_used} section(s) expanded ({total_words} words total).",
            )

    metadata = DocumentMetadata(
        conversation_id=conversation_id,
        generated_at=datetime.now(UTC).isoformat(),
        models_used=[model.name],
        message_count=len(real_messages),
        generation_notice=development_notice() if is_mock else real_inference_notice(model),
        outline_source=outline_source,
        outline_padded=outline_padded,
    )

    spec = DocumentSpec(
        title=str(outline.get("title") or "Conversation Summary"),
        subtitle=str(outline.get("subtitle") or ""),
        metadata=metadata,
        sections=sections,
        qa_log=build_qa_log(real_messages),
        references=build_references(real_messages),
    )
    code_blocks = extract_code_blocks(real_messages)
    if code_blocks and spec.sections:
        spec.sections[-1].code_blocks = code_blocks

    filename = f"{_slugify(spec.title)}_{int(time.time())}.{fmt}"
    target = resolve_within(settings.generated_path, filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    render_document(spec, fmt, target)

    deliverable = DeliverableRef(
        id=target.name,
        filename=target.name,
        file_type=TYPE_LABELS[fmt],
        size_bytes=target.stat().st_size,
        status="ready",
    )
    step("building_file", "Building file", StepStatus.COMPLETED, detail=f"{target.name} ({deliverable.size_bytes} bytes)")
    step("completed", "Completed", StepStatus.COMPLETED)

    notice = development_notice() if is_mock else real_inference_notice(model)
    response_text = (
        f"Generated **{target.name}** ({TYPE_LABELS[fmt]}) — a summary of this conversation "
        f"({len(real_messages)} messages, {len(sections)} sections).\n\n{notice}"
    )

    log_event(
        logger,
        "conversation_exported",
        conversation_id=conversation_id,
        format=fmt,
        sections=len(sections),
        expansions=expansions_used,
        is_mock=is_mock,
        outline_source=outline_source,
        outline_padded=outline_padded,
    )

    return ExportResult(
        deliverable=deliverable,
        steps=steps,
        routing=routing,
        response_text=response_text,
        is_mock=is_mock,
    )
