# Local Models

This directory is where local, open-weight model files live on the
organization's server. **No model weights are stored in this repository.**

## What goes here (on a deployed server, not in Git)

```
models/
├── general/       # e.g. a Llama/Mistral-class instruction model
├── code/          # e.g. a Qwen2.5-Coder-class model
├── vision/        # e.g. a LLaVA-class multimodal model
├── embedding/     # e.g. a BGE/E5-class embedding model for RAG
└── manifest.json  # (future) local registry the backend model router reads
```

Weight files (`.gguf`, `.bin`, `.safetensors`, `.pt`, `.onnx`, etc.) are
excluded from Git via the root [`.gitignore`](../.gitignore) — they are
multi-gigabyte binary artifacts that belong on the deployment server's disk,
not in version control.

## Why local, open-weight models

The Sovereign AI Workbench is designed to run fully air-gapped: every model
that powers an agent is hosted on infrastructure the organization controls,
with no calls to external AI APIs. The architecture is built to support
**multiple** local models side by side — a general-purpose model, a coding
model, a vision model, an embedding model for retrieval, and so on — selected
per-agent by the backend's model router (see
[`backend/app/models/`](../backend/app/models/)).

## Segment 2: the router exists; Segment 3: real models run through it

Segment 2 built the Model Registry and capability-scoring Model Router
(`backend/app/models/registry.py`, `.../router.py`) against four
metadata-only mock registrations (`general-small`, `code-small`,
`vision-small`, `data-small`) — no weight file behind any of them.

Segment 3 added a real provider, `OllamaProvider`
(`backend/app/models/providers/ollama.py`), and proved the whole thing
end-to-end against a genuinely small, CPU-only model:
**`qwen2.5:1.5b-instruct`** (Q4_K_M, ~1GB resident) served by
[Ollama](https://ollama.com), plus **`nomic-embed-text`** (137M) for real
local RAG embeddings — both well within the current dev hardware's budget
(4c/8t, ~12GB RAM, no CUDA GPU). Neither model's weights live in this
directory or in Git; Ollama manages its own model cache
(`~/.ollama/models`) entirely outside this repository. This is opt-in via
`MODEL_PROVIDER=ollama` / `EMBEDDING_PROVIDER=ollama` in `backend/.env` —
the default (`mock`) still requires nothing installed.

No real vision-capable model is registered yet, so `VisionAgent` stays on
its clearly-labeled mock path — see `backend/README.md`'s Phase D section.

## What's not here yet

A persisted `manifest.json` the registry loads from disk (today's registry
is in-memory, rebuilt from code at every startup), and any model files
actually placed in this directory — Ollama's own cache is the only "real
weights on disk" this project touches so far. Until then, "registering a
model" via the Admin Models page only adds a metadata record to the
in-memory registry — never a download, and the same is true for
Ollama-backed models: this repo never downloads them, `ollama pull` does.
