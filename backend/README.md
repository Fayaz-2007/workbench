# Backend — Sovereign AI Workbench

FastAPI service hosting the AI core: automatic task routing, agent
orchestration, model routing, real local inference, local RAG, OCR, tools,
sandboxed code execution, and document generation. **All of the above are
real and tested** — not scaffolding. Deferred: network/system/audit
telemetry, real authentication, external integrations.

## Architecture

```
Browser Client
     │  HTTP (fetch/multipart), CORS-restricted to the frontend origin
     ▼
FastAPI  (app/main.py)
     │  /api/agents, /api/chat, /api/models, /api/documents, /api/tools,
     │  /api/files, /api/deliverables, /api/admin/*
     ▼
Task Router  (app/agents/task_router.py) — Auto mode only
     │  decides WHO handles the request (an independent decision from
     │  the Model Router below); manual mode skips this entirely
     ▼
Agent Manager  (app/agents/manager.py)
     │  agent_id -> BaseAgent instance
     ▼
Selected Agent  (app/agents/{general,code,document,vision,data}.py)
     │  declares required_capabilities; never names a model
     ▼
Model Router  (app/models/router.py) ──> Model Registry (app/models/registry.py)
     │  decides WHICH MODEL that agent uses — scores every eligible,
     │  available model; independent of the Task Router above
     ▼
Model Provider  (app/models/providers/{local,ollama}.py)
     │  mock, or real local inference via Ollama
     ▼
finalize_response() hook — agent-specific extension of the pipeline:
     • CodeAgent    -> Sandbox (app/sandbox/) -> verify/revise -> result
     • DocumentAgent -> RAG (app/rag/) -> grounded answer + citations
     • DataAgent     -> CSV Analysis Tool (app/tools/) -> real statistics
     ▼
ChatResponse (response + task_routing + routing + execution steps + citations + deliverables)
     ▼
Browser Client
```

**Task Router and Model Router are independent and must never be
conflated**: Task Router decides *who* (which agent); Model Router decides
*which model* that agent then uses. Task Router only runs in Auto mode —
manual mode (the frontend sends a concrete `agent_id`) never touches it,
and behaves exactly as Segment 2 shipped.

**The model is not the agent.** An agent declares `capabilities`
(`["coding", "debugging", ...]`); the Model Router scores every
registered, available model against them and picks the best fit — no
agent ever names a model. This is what let Segment 3 add three real,
Ollama-served models into the exact same registry the Segment 2 mock
models live in, with zero agent code changes (see "Real local models"
below).

### Hardware constraint driving every choice in this segment

4-core/8-thread Intel i5-1135G7, ~12GB RAM, no CUDA GPU. Every real piece
added in Segment 3 was chosen to run on that:

- **Inference**: a quantized 1.5B model (`qwen2.5:1.5b-instruct`, Q4_K_M)
  served by Ollama — CPU-only, ~1GB resident.
- **Embeddings**: `nomic-embed-text` (137M) — same story.
- **Vector store**: ChromaDB's embedded/local mode — no server process.
- **OCR**: Tesseract — CPU, no GPU dependency (when the binary is
  installed; gracefully reports unavailable otherwise, see Phase C below).
- **Sandbox**: a subprocess, not a container runtime (Docker isn't
  installed on this machine — see Phase F).

Nothing here is a ceiling: `ModelInfo.resource_class` and
`Settings.server_resource_class` exist precisely so a stronger production
server can register `medium`/`large` models later and have the router
prefer them automatically.

## Task Router / Auto Mode

`TaskRouter` (`app/agents/task_router.py`) answers *"which agent should
handle this?"* — a decision kept strictly separate from the Model Router's
*"which model?"*. It only runs when `ChatRequest.agent_id` is omitted or
the literal `"auto"`; a concrete id (manual mode) skips it entirely and
behaves exactly like Segment 2.

Not a keyword dictionary — two small, explainable signals, always falling
back to General rather than crashing or guessing wildly:

1. **Attachment file type** (strongest, deterministic): an image →
   Vision, a `.csv`/`.xlsx` → Data.
2. **Phrase-overlap scoring**: a short (~10-item), per-agent phrase list
   scored against the message text — a `.pdf`/`.docx`/`.txt` attachment
   nudges toward Document. Below a confidence floor, or with no signal at
   all, it falls back to `general` — General Agent is always registered,
   so Auto mode never has nothing to fall back to.

The result — `{agent_id, reason, confidence}` — never exposes internal
scores or chain-of-thought to the client: `reason` is always one plain
sentence ("The request involves code, debugging, or a programming task.").
It's returned two ways in `ChatResponse`: as a structured `task_routing`
field (`null` in manual mode), and folded into the `detail` of the
existing `"selecting_agent"` execution step — the frontend's execution UI
(`frontend/src/components/execution/ExecutionSteps.tsx`) already renders
per-step detail text, so Auto mode's reasoning is visible with zero new UI.

## Running locally

Requires Python 3.11, and — for real inference/embeddings —
[Ollama](https://ollama.com) running locally with the models below pulled.
Without Ollama, the backend still runs fully offline against the mock
provider (`MODEL_PROVIDER=mock`, the default).

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
copy .env.example .env        # Windows: copy, macOS/Linux: cp

# Optional, for real local inference + RAG (see .env for the flags):
ollama pull qwen2.5:1.5b-instruct
ollama pull nomic-embed-text
# then set MODEL_PROVIDER=ollama and EMBEDDING_PROVIDER=ollama in .env

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Binding to `0.0.0.0` makes the API reachable from another machine on the
LAN once the frontend's `VITE_API_BASE_URL` points at this server's IP —
no Python, no Ollama, and no model install is required on the client
machine.

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/agents` | Agent catalog |
| GET / POST | `/api/models` | List / register models (metadata only) |
| DELETE | `/api/models/{id}` | Remove a model from the registry |
| POST | `/api/chat` | Run the full pipeline; omit `agent_id` (or send `"auto"`) for automatic agent selection |
| POST | `/api/files/upload` | Save an uploaded file locally |
| GET | `/api/files/{id}` | Download an uploaded file |
| POST | `/api/documents/ingest` | Ingest an uploaded file into the local knowledge base |
| GET | `/api/documents` | List ingested documents |
| POST | `/api/documents/search` | Search the local knowledge base |
| DELETE | `/api/documents/{id}` | Remove a document (and its chunks) |
| GET | `/api/tools` | List available tools + their risk/network metadata |
| POST | `/api/tools/execute` | Run one registered tool |
| GET | `/api/deliverables` | List generated deliverable files |
| GET | `/api/deliverables/{id}` | Download a generated deliverable |
| GET | `/api/admin/overview` | Model counts + this session's activity feed |
| GET | `/api/admin/models` | Same data as `/api/models`, for the Admin UI |

Every error is `{"error": {"code", "message"}}` — never a traceback. New
in Segment 3: `not_found` (files/documents/deliverables) and
`tool_not_found`, alongside Segment 2's `invalid_request`,
`agent_not_found`, `model_not_found`, `no_suitable_model`,
`model_unavailable`, `agent_execution_failed`.

## Real local models (Phase A)

`OllamaProvider` (`app/models/providers/ollama.py`) implements the same
`BaseModelProvider` interface as the mock (`generate`/`stream`/
`health_check`) — agents and the router cannot tell the difference except
through `GenerationResult.is_mock`. When `MODEL_PROVIDER=ollama`, three
registry entries are added at startup (`app/models/registry.py:
ollama_dev_models`), all backed by the *same* pulled model but scoped to
different capabilities so they compete fairly for General, Code, and Data
agent requests:

| id | type | capabilities |
|---|---|---|
| `ollama-general` | general | reasoning, text_generation, question_answering, document_analysis, summarization, information_extraction |
| `ollama-code` | code | coding, debugging, code_generation, code_reasoning |
| `ollama-data` | data | data_analysis, tabular_reasoning, statistics |

No vision entry: this is a text-only model, and Segment 3 never labels a
text model as vision-capable (see Phase D). This registration is
config-gated, not live-probed, so the automated test suite (which runs
with the `mock` default) never depends on Ollama actually running — an
unreachable Ollama surfaces as a clean `ModelUnavailableError` on the
first request that needs it, never a boot failure or a crash.

Every agent response is honestly labeled: mock output carries
`development_notice()`; real output carries `real_inference_notice()`
naming the actual model and provider (see `app/agents/base.py`).

## RAG / local knowledge base (Phase B)

```
Document -> DocumentLoader -> DocumentChunker -> EmbeddingProvider
    -> VectorStore (ChromaDB) -> Retriever -> RAGService
```

Each piece is independently replaceable (`app/rag/loaders.py`,
`chunker.py`, `embeddings.py`, `vector_store.py`, `retriever.py`) behind
one entry point, `RAGService` (`service.py`) — nothing outside `app/rag/`
touches a loader or the vector store directly.

- **Loaders**: `.txt` `.md` `.pdf` `.docx` `.csv` `.xlsx` `.png` `.jpg`
  `.jpeg`. A PDF page with almost no extractable text is flagged
  `needs_ocr=True` rather than guessed at (see Phase C).
- **Chunking**: character-window with overlap (`RAG_CHUNK_SIZE` /
  `RAG_CHUNK_OVERLAP`), preserving filename/page/document id/chunk
  id/source path/ingestion timestamp on every chunk — what the frontend's
  citation UI needs.
- **Embeddings**: `MockEmbeddingProvider` (deterministic, offline, default)
  or `OllamaEmbeddingProvider` (real, via `nomic-embed-text`).
- **Vector store**: `ChromaVectorStore` — local, persistent
  (`CHROMA_PATH`), no external vector database, no cloud embeddings.

`DocumentAgent.build_prompt` (`app/agents/document.py`) auto-ingests any
attached, RAG-supported file before searching, so "attach a document, ask
about it" works in one chat turn — retrieved chunks become both grounding
context for the prompt and citations on the response
(`frontend`'s existing `CitationList` renders them unmodified).

## OCR (Phase C)

`OCRProvider` (`app/multimodal/ocr.py`): `generate`/`stream`-shaped
interface → `extract(image_path) -> OCRResult` with `text`, a best-effort
`confidence`, and `errors` (OCR is never assumed perfect).
`TesseractOCRProvider` requires the **`tesseract` binary** on PATH (not
just the `pytesseract` package) — `health_check()` and every `extract()`
call report a clean "unavailable" result when it's missing, rather than
crashing. Standalone image uploads (PNG/JPG) run through OCR on ingestion;
rasterizing *scanned PDF pages* to images (needed for OCR on scans) isn't
implemented — it needs an additional dependency (PyMuPDF/pdf2image, not
included) and is a documented, honest gap, not a fake result.

## Vision (Phase D)

No real vision-capable model is registered on this hardware, so
`VisionAgent` always takes the clearly-labeled mock path — **the router
still genuinely evaluates any model tagged `image_understanding` /
`multimodal` / `visual_reasoning`**; there just isn't a real one yet.
Registering one (e.g. a small LLaVA-class GGUF via Ollama) needs one more
registry entry, same as Phase A — no agent code changes.

## Local tools (Phase E)

`BaseTool` (`app/tools/base.py`): `name`, `description`, `capabilities`,
`risk` (low/medium/high), `network` (always `False` here), `input_schema`,
`execute()`. `ToolRegistry` mirrors `AgentManager`/`ModelRegistry`'s
register/get/list shape. Every filesystem-touching tool is confined to
this app's own data directories via `resolve_within()`
(`app/tools/fs_utils.py`) — path traversal and absolute paths are
rejected before any file operation runs.

| Tool | Risk | What it does |
|---|---|---|
| `file_read` | low | Reads a text file from `uploads`/`documents`/`generated` |
| `file_write` | medium | Writes a text file into `generated` |
| `list_files` | low | Lists files in one of the three data directories |
| `calculator` | low | AST-based safe arithmetic — no `eval()` |
| `csv_analysis` | low | Real pandas statistics (Phase H) |
| `document_generation` | medium | Real DOCX/XLSX/PDF/Markdown/text files (Phase G) |
| `knowledge_search` | low | Wraps `RAGService.search` |

## Sandboxed code execution (Phase F)

```
Code Agent -> generated code -> Sandbox -> stdout/stderr/exit code
    -> Agent -> verify/revise (bounded) -> final result
```

**Honest about what "development sandbox" means**: `SubprocessSandboxProvider`
(`app/sandbox/subprocess_provider.py`) runs generated Python in an isolated
throwaway working directory, in isolated interpreter mode (`-I`, ignoring
the host's `PYTHONPATH`), under a hard wall-clock timeout
(`MAX_EXECUTION_SECONDS`) that kills the process on expiry. It does
**not** enforce OS-level filesystem or network restriction — building that
safely and portably (Windows + Linux, no Docker) is a separate, real
engineering problem, not something to fake with a comment
(`SandboxProvider.isolation_level` says so explicitly, and the frontend
surfaces that string verbatim). A container-backed provider implementing
the same `SandboxProvider` interface is what should carry real untrusted
workloads in production.

`CodeAgent.finalize_response` (`app/agents/code.py`) runs a **bounded**
loop via `LoopBudget` (`app/agents/loop.py` — a small, generic
max-steps-and-timeout budget, not Code-Agent-specific): generate → run →
if it failed (and budget remains), ask the model to fix it once → re-run →
verify. It always terminates — reaching the step or time budget stops it
safely rather than looping.

## Document generation (Phase G)

`DocumentGenerationTool` writes real files — `.docx` (python-docx),
`.xlsx` (openpyxl), `.pdf` (fpdf2), `.md`/`.txt` — into `GENERATED_DIR`,
returning the metadata the frontend's existing `DeliverableCard` needs
(filename, type, size, timestamp, download id). `GET /api/deliverables`
lists them; `GET /api/deliverables/{id}` streams one back.

## Data Agent (Phase H)

`DataAgent.build_prompt` runs `CSVAnalysisTool` (real pandas: row/column
counts, per-column mean/median/std/min/max, missing-value counts, optional
group-by aggregation) against any attached CSV/XLSX **before**
generation — the model explains real, computed numbers; it never performs
the arithmetic itself. The response is explicitly prefixed noting the
statistics were computed deterministically, not estimated.

## Bounded agentic execution

`app/agents/loop.py`'s `LoopBudget` is the one small, reusable piece
behind "agentic execution" in this segment: a hard `max_steps` (`MAX_AGENT_STEPS`)
*and* wall-clock timeout, whichever is hit first stops the loop safely.
Today only `CodeAgent` drives a real multi-step loop with it (see Phase
F); the abstraction has no Code-Agent-specific concept in it, so any
future multi-step agent can reuse it directly. This is deliberately not a
generic PLAN/ACT/OBSERVE/DECIDE framework or a LangGraph dependency — per
the brief, the core interfaces come first.

## Tests

```bash
python -m pytest -q
```

101 tests. Segment 2's 31 unchanged, plus: tools + path-safety (22), RAG
pipeline (10), sandbox (5), CSV/document-generation/knowledge-search tools
(8), the new API surface — files, documents, tools, deliverables (12), and
the Task Router — phrase/attachment signals, low-confidence fallback, and
`/api/chat` in both Auto and manual mode (13). Every test that boots the
app gets its own throwaway data directory
(`tests/conftest.py`'s `isolate_data_dirs`, autouse) — nothing under test
ever touches the real `backend/data/` directory, and `MODEL_PROVIDER`/
`EMBEDDING_PROVIDER` stay at their `mock` defaults throughout, so results
never depend on Ollama actually running on the host.

## Security principles

- **No external AI APIs, no cloud model providers, no telemetry.** Every
  provider added in Segment 3 (Ollama, ChromaDB, Tesseract) talks only to
  `localhost`/the local filesystem.
- **CORS is origin-restricted**, never `"*"`.
- **No secrets in the repo.** `.env` is gitignored.
- **No stack traces reach the client.** Structured `{"error": {...}}`
  bodies only; full detail logged server-side.
- **File tools can't escape their directory.** `resolve_within()` rejects
  `..` and absolute paths before any read/write.
- **Sandboxed code never runs on the host process.** Always through
  `SandboxProvider` — see Phase F's honesty note above.
- **Structured, redaction-aware logging** feeding the security/audit layer
  a later segment will add (`app/core/logging.py`).

## Intentionally not implemented yet

Real authentication, network/system/audit telemetry (the Admin Network,
System, and Audit Logs pages stay on frontend mock data), external API
integrations, a container-backed sandbox, PDF-page-to-image rasterization
for scanned-PDF OCR, and a generic multi-agent PLAN/ACT/OBSERVE/DECIDE
framework. Each has a clear extension point already built (see the
per-phase sections above) rather than a placeholder package.
