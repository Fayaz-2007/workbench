"""Document Agent — document analysis and summarization, grounded in the
local knowledge base when one exists.

`build_prompt` searches `RAGService` (see `app/rag/`) *before* generation
so the model answers from retrieved context rather than guessing;
`finalize_response` turns whatever was retrieved into citations the
frontend's existing `CitationList` component already knows how to render.
"""

from __future__ import annotations

from app.agents.base import (
    AgentTask,
    BaseAgent,
    CitationRef,
    ExecutionContext,
    FinalizedResponse,
    StepStatus,
    response_notice,
)
from app.core.exceptions import InvalidRequestError
from app.core.logging import get_logger, log_event
from app.models.base import GenerationResult, ModelInfo, ModelType
from app.tools.fs_utils import PathEscapeError, resolve_within

logger = get_logger(__name__)

_TOP_K = 4
_INGESTIBLE_SUFFIXES = (".txt", ".md", ".pdf", ".docx", ".csv", ".xlsx", ".png", ".jpg", ".jpeg")


class DocumentAgent(BaseAgent):
    id = "document"
    name = "Document Agent"
    description = "Document analysis, summarization, and document-related reasoning."
    capabilities = ["document_analysis", "summarization", "information_extraction"]
    # No dedicated "document" model type exists yet — the general-purpose
    # model is the expected match; capability overlap does the real work.
    model_type = ModelType.GENERAL

    async def _ingest_new_attachments(self, task: AgentTask, context: ExecutionContext) -> None:
        """Ingests any attached, RAG-supported file that hasn't been indexed
        yet, so "attach a document and ask about it" works in one turn.
        Unsupported/unreadable attachments are skipped, not fatal.
        """
        if context.rag_service is None or context.settings is None:
            return
        for attachment in task.attachments:
            if not attachment.path:
                continue
            if not attachment.filename.lower().endswith(_INGESTIBLE_SUFFIXES):
                continue
            try:
                resolved = resolve_within(context.settings.upload_path, attachment.path)
                await context.rag_service.ingest_document(resolved, display_filename=attachment.filename)
            except (InvalidRequestError, PathEscapeError, OSError) as exc:
                log_event(logger, "attachment_ingest_skipped", filename=attachment.filename, error=str(exc))

    async def build_prompt(self, task: AgentTask, context: ExecutionContext) -> str:
        context.retrieved_chunks = []
        await self._ingest_new_attachments(task, context)

        if context.rag_service is None or not task.message.strip():
            return (
                "You are a document analysis assistant running entirely on local "
                f"infrastructure.\n\nUser: {task.message}"
            )

        if context.rag_service.chunk_count == 0:
            return (
                "You are a document analysis assistant running entirely on local "
                "infrastructure. No documents have been indexed yet — tell the user "
                "that plainly (they can upload one via the composer's attachment "
                "button) rather than answering from general knowledge as if it were "
                "organizational knowledge.\n\n"
                f"User: {task.message}"
            )

        threshold = context.settings.rag_relevance_threshold if context.settings else 0.0
        context.retrieved_chunks = await context.rag_service.search(task.message, top_k=_TOP_K, min_score=threshold)

        if context.retrieved_chunks:
            context_block = "\n\n".join(
                f"[Source: {r.chunk.filename}"
                f"{f', page {r.chunk.page_number}' if r.chunk.page_number else ''}]\n{r.chunk.text}"
                for r in context.retrieved_chunks
            )
            return (
                "You are a document analysis assistant running entirely on local "
                "infrastructure. Answer using ONLY the context below; if it doesn't "
                "answer the question, say so plainly rather than inventing an answer.\n\n"
                f"Context:\n{context_block}\n\n"
                f"User: {task.message}"
            )

        return (
            "You are a document analysis assistant running entirely on local "
            "infrastructure. Tell the user plainly that the answer was not found in "
            "the organization's indexed knowledge base — do not guess or answer from "
            "general knowledge as if it were organizational knowledge.\n\n"
            f"User: {task.message}"
        )

    def format_response(self, task: AgentTask, model: ModelInfo, raw: GenerationResult) -> str:
        attachment_note = (
            f" across {len(task.attachments)} attached file(s)" if task.attachments else ""
        )
        if raw.is_mock:
            return (
                f"**Document Agent** ({model.name})\n\n"
                f"{response_notice(model, raw)}\n\n"
                f"Request received{attachment_note}:\n\n> {task.message.strip() or '(empty message)'}\n\n"
                "Local knowledge-base retrieval already ran for this request (see the "
                "execution steps and citations below for what was found, if anything) "
                "— only this response's language-model generation step is mocked. Set "
                "MODEL_PROVIDER=ollama for a real answer grounded in that retrieved "
                "content.\n\n"
                f"Routed model output:\n\n{raw.text}"
            )
        return f"{raw.text}\n\n---\n{response_notice(model, raw)}"

    async def finalize_response(
        self, task: AgentTask, model: ModelInfo, raw: GenerationResult, context: ExecutionContext, record
    ) -> FinalizedResponse:
        # Whether retrieval happened is a fact about `build_prompt()`
        # (which runs regardless of which model provider ends up
        # generating), never about `raw.is_mock` — a mock/real generation
        # step must not hide or fabricate a step/citations for what the
        # knowledge base search actually did. `build_prompt()` only calls
        # `.search()` (populating `retrieved_chunks`, possibly empty) when
        # the knowledge base has at least one indexed chunk; an empty KB
        # short-circuits before ever searching, so no step is recorded
        # then — matching "only show a step if it actually happened".
        searched_knowledge_base = (
            context.rag_service is not None and task.message.strip() and context.rag_service.chunk_count > 0
        )
        if searched_knowledge_base:
            record("retrieving_context", StepStatus.COMPLETED)

        citations = [
            CitationRef(
                id=r.chunk.chunk_id,
                label=f"{r.chunk.filename}" + (f" (p.{r.chunk.page_number})" if r.chunk.page_number else ""),
                source=r.chunk.source_path,
            )
            for r in context.retrieved_chunks
        ]

        if raw.is_mock:
            return FinalizedResponse(text=self.format_response(task, model, raw), citations=citations)

        text = f"{raw.text}\n\n---\n{response_notice(model, raw)}"
        return FinalizedResponse(text=text, citations=citations)
