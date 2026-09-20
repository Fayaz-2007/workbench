# Sovereign AI Workbench

A self-hosted, air-gapped, multimodal agentic AI workbench for confidential
industrial work — built for environments like refineries, PSUs,
defence-linked manufacturing units, and government organizations where data
cannot leave the organization's own infrastructure.

## Purpose

Sovereign AI Workbench gives teams a private alternative to cloud AI
assistants: the same day-to-day usefulness — chat, document drafting, code
help, image and data analysis — running entirely on hardware the
organization controls, with **no external AI API calls** in its final
deployment.

## High-level architecture

```
   Browser Client
        │
        ▼
  FastAPI Backend
        │
        ▼
   Agent Manager
        │
        ▼
   Selected Agent  (General · Code · Document · Vision · Data)
        │              declares required capabilities, never a model name
        ▼
   Model Router  ── scores every approved, available model
        │
        ▼
Local Model Provider  (mock today — see models/README.md)
        │
        ▼
   Agent Execution
        │
        ▼
      Response
        │
        ▼
   Browser Client
```

- **Browser Client** — the frontend in [`frontend/`](frontend/): the chat
  interface, agent selection, file upload, and admin dashboard. UI only; no
  business logic or model access.
- **FastAPI Backend** — the service in [`backend/`](backend/): owns business
  logic, request handling, and orchestration. This is the only layer the
  frontend talks to.
- **Agent Manager** — turns an `agent_id` from the frontend into a
  concrete agent and runs it (`backend/app/agents/manager.py`).
- **Selected Agent** — task-oriented behavior (General, Code, Document,
  Vision, Data), each declaring the *capabilities* it needs — never a
  model name (`backend/app/agents/`).
- **Model Router** — scores every registered, available model against the
  agent's required capabilities and picks the best fit; an internal
  routing score, not a benchmark (`backend/app/models/router.py`).
- **Local Model Provider** — the inference abstraction models run through.
  A metadata-labeled mock (`.../providers/local.py`) and a real provider
  backed by [Ollama](https://ollama.com) (`.../providers/ollama.py`) both
  exist today, behind the same interface — llama.cpp/vLLM can be added the
  same way, without touching agents or the router. Real weights live
  outside Git on the organization's server (see [`models/`](models/)).
- **Deliverables** — real generated files (DOCX/XLSX/PDF/Markdown), written
  locally and handed back to the user through the browser client (see
  `backend/app/tools/document_generation.py`).

This repository is organized so each layer can be developed and deployed
independently:

| Layer | Responsibility | Location |
|---|---|---|
| Frontend | User interface only | [`frontend/`](frontend/) |
| Backend | Business logic and AI orchestration | [`backend/`](backend/) |
| Agents | Task-oriented behavior, capability-declared | `backend/app/agents/` |
| Model Registry / Router | Model metadata + selection scoring | `backend/app/models/` |
| Local Models | Inference | [`models/`](models/) |
| RAG | Local knowledge retrieval | `backend/app/rag/` |
| Tools | File/document/data operations | `backend/app/tools/` |
| Sandbox | Isolated code execution | `backend/app/sandbox/` |
| Security | Network monitoring, audit logging, access control | `backend/app/security/` |

## Project status

This repository currently contains:

- **Segment 1 (complete):** the frontend client/user-experience layer —
  User Workbench, Admin Dashboard shell, agent selection, chat, file
  upload UI, execution-progress UI, deliverable UI, and a stable API
  abstraction.
- **Segment 2 (complete):** the AI core / orchestration backend — FastAPI,
  five agents, a Model Registry, and a capability-scoring Model Router,
  proven correct behind a mock provider.
- **Segment 3 (complete):** the mock provider became real, and the system
  gained automatic task routing. Local inference via Ollama, a **Task
  Router** for Auto mode (kept strictly independent from the Model
  Router — see below), local RAG (ChromaDB + local embeddings) with
  document ingestion and citations, OCR (Tesseract-backed, honest about
  what's not wired up yet), seven local tools behind a Tool Registry,
  sandboxed Python execution with a bounded generate → run → verify →
  revise loop, and real deliverable generation (DOCX/XLSX/PDF/Markdown) —
  all running on the 4c/8t, ~12GB-RAM, no-GPU dev machine this project
  targets. See [`backend/README.md`](backend/README.md) for the full
  architecture and what's honestly still mock (Vision Agent — no local
  vision model is installed yet) or deferred.

**Task Router vs. Model Router** — two independent decisions, never
conflated: the Task Router (Auto mode only) decides *which agent*
handles a request; the Model Router (every request) decides *which
model* that agent uses.

Real authentication, network/system/audit telemetry, external API
integrations, and a container-backed sandbox are **not implemented yet** —
they belong to a later segment. The Admin Network, System, and Audit Logs
pages still show frontend mock data accordingly.

## Repository layout

```
sovereign-ai-workbench/
├── frontend/     # React + Vite + TypeScript + Tailwind client
├── backend/      # FastAPI service (structural foundation only)
├── models/       # Local model docs/config — weights are never committed
├── docs/         # Architecture and deployment documentation
├── scripts/      # Setup/deployment/helper scripts (added as needed)
├── docker-compose.yml
└── README.md
```

## Running the project

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173/` (User Workbench) and
`http://localhost:5173/admin` (Admin Dashboard). The dev server binds to
all interfaces, so it's also reachable at `http://SERVER-IP:5173` from
another machine on the same LAN.

See [`frontend/`](frontend/) for the frontend's API base URL configuration
(`VITE_API_BASE_URL`).

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Runs fully offline against the mock provider by default. For real local
inference and RAG, install [Ollama](https://ollama.com), pull
`qwen2.5:1.5b-instruct` and `nomic-embed-text`, and set
`MODEL_PROVIDER=ollama` / `EMBEDDING_PROVIDER=ollama` in `.env`.

Binding to `0.0.0.0` makes the API reachable from another machine on the
LAN once the frontend's `VITE_API_BASE_URL` points at this server's IP
(e.g. `http://SERVER-IP:8000`) — the client machine needs neither Python
nor any model installed. See [`backend/README.md`](backend/README.md) for
the full endpoint list and architecture.

## Design principles

- **No external AI APIs, ever.** Every model call happens against
  infrastructure the organization controls.
- **No secrets in Git.** Configuration is environment-variable driven;
  `.env` files are gitignored, and `.env.example` files document the shape
  without real values.
- **No model weights in Git.** Large binary weight files live on the
  deployment server's disk under `models/`, excluded via `.gitignore`.
- **Strict layer separation.** The frontend never talks to a model
  directly; the backend never renders UI. Each concern (RAG, tools,
  sandbox, security) owns its own package so segments can land
  independently without destabilizing what already works.
- **Agents never name a model.** An agent declares the capabilities it
  needs; the Model Router picks the best currently-registered match. New
  local models can be added without touching agent code.
- **CORS is origin-restricted, never `"*"`.** The backend only accepts
  requests from the configured frontend origin(s) (`CORS_ORIGINS`).
- **Mock and real output are never conflated.** Every agent response is
  labeled with which it is; a "development sandbox" is never described as
  container-grade isolation; OCR/vision responses say plainly when the
  underlying capability isn't wired up yet, instead of faking a result.
