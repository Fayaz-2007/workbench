"""Application configuration, loaded from environment variables.

Segment 3 adds config for real local inference (Ollama), local RAG
(embeddings + ChromaDB), document storage, OCR, sandboxed code execution,
and the bounded agentic loop. Every one of these defaults to either "off"
or a purely local/offline behavior — nothing here can reach an external
service unless explicitly pointed at one, and every URL is loopback by
default (never hard-coded elsewhere in the codebase).
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # An absolute path, not the bare string ".env" — pydantic-settings
    # resolves a relative `env_file` against the *process's* current
    # working directory, not this file's location. A backend launched
    # from anywhere other than `backend/` (a different cwd, a launcher
    # script, an IDE run configuration) would then silently find no .env
    # at all and fall back to every field's default — including
    # `model_provider="mock"` — with no error. Anchoring to `_BACKEND_ROOT`
    # (already used below for upload/documents/chroma paths) makes .env
    # discovery independent of cwd, the same way those already are.
    model_config = SettingsConfigDict(env_file=_BACKEND_ROOT / ".env", extra="ignore")

    app_name: str = "Sovereign AI Workbench"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # Comma-separated list of allowed origins for the frontend dev server /
    # LAN deployment. Never "*" — see app/main.py for how this is applied.
    cors_origins: str = "http://localhost:5173"

    # This machine's resource tier (tiny/small/medium/large). The current
    # dev box (4c/8t, ~12GB RAM, no CUDA GPU) is deliberately "small" — the
    # model router uses this to prefer models that actually fit.
    server_resource_class: str = "small"

    # ---- Real local model inference (Phase A) ------------------------
    # "mock" (default) registers only the Segment 2 mock dev models — the
    # test suite runs against this so it's fully deterministic regardless
    # of what happens to be running on the host. Set to "ollama" to also
    # register real, Ollama-served models (see app/models/registry.py).
    model_provider: str = "mock"
    model_base_url: str = "http://localhost:11434"
    model_request_timeout_seconds: float = 60.0
    ollama_model: str = "qwen2.5:1.5b-instruct"

    # ---- Real local vision inference (Vision Agent) --------------------
    # Deliberately separate from `model_provider`/`ollama_model` above: the
    # text model has no multimodal capability, so Vision Agent needs its own
    # provider switch and its own model identifier. "mock" (default) keeps
    # Vision Agent on the metadata-only dev model (`vision-small`) so the
    # test suite stays deterministic. Set to "ollama" for real local image
    # understanding via a vision-capable Ollama model — reuses
    # `model_base_url` above (same Ollama server, different model).
    vision_model_provider: str = "mock"
    vision_model: str = "qwen2.5vl:3b"

    # ---- RAG / local knowledge base (Phase B) -------------------------
    # "mock" (default) keeps the RAG test suite deterministic and offline
    # regardless of what's running on the host — same pattern as
    # `model_provider`. Set to "ollama" for real local embeddings.
    embedding_provider: str = "mock"
    embedding_model: str = "nomic-embed-text"
    chroma_path: str = "./data/chroma"
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 120
    rag_top_k: int = 4
    # Below this score (cosine similarity — see vector_store.py's cosine-
    # space query), a retrieved chunk is treated as "not actually relevant"
    # rather than forced into the prompt. Calibrated empirically against
    # real Ollama embeddings (nomic-embed-text): unrelated queries against
    # an indexed policy document scored ~0.33-0.39, genuinely relevant ones
    # ~0.51-0.75 — 0.45 sits in that gap. The mock embedding provider's
    # coarser bag-of-words vectors score lower even for relevant matches;
    # lower this via env var if running against the mock provider.
    rag_relevance_threshold: float = 0.45

    # ---- Storage (Phase B/G) ------------------------------------------
    upload_dir: str = "./data/uploads"
    documents_dir: str = "./data/documents"
    generated_dir: str = "./data/generated"
    max_upload_mb: int = 25

    # ---- OCR (Phase C) --------------------------------------------------
    ocr_provider: str = "tesseract"  # "tesseract" | "none"

    # ---- Sandboxed code execution (Phase F) ----------------------------
    sandbox_provider: str = "subprocess"  # "subprocess" | "none"
    max_execution_seconds: int = 15

    # ---- Bounded agentic loop (Code Agent) -----------------------------
    max_agent_steps: int = 8

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else (_BACKEND_ROOT / p)

    @property
    def upload_path(self) -> Path:
        return self._resolve(self.upload_dir)

    @property
    def documents_path(self) -> Path:
        return self._resolve(self.documents_dir)

    @property
    def generated_path(self) -> Path:
        return self._resolve(self.generated_dir)

    @property
    def chroma_resolved_path(self) -> Path:
        return self._resolve(self.chroma_path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
