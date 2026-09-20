"""EmbeddingProvider — turns text into vectors for the vector store.

Two implementations, same pattern as `app/models/providers/`:

- `MockEmbeddingProvider` (default): a deterministic, dependency-free
  hash-based embedding. Not semantically meaningful, but stable and fully
  offline — it's what keeps the RAG test suite deterministic without
  requiring Ollama, exactly like `model_provider="mock"`.
- `OllamaEmbeddingProvider`: real local embeddings via Ollama's
  `/api/embeddings` (e.g. `nomic-embed-text`). Opt in with
  `EMBEDDING_PROVIDER=ollama` in `.env`.

Nothing here calls an external service — `EMBEDDING_MODEL_BASE_URL`
(falling back to `MODEL_BASE_URL`) must always be a local/LAN address.
"""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod

import httpx

from app.core.exceptions import ModelUnavailableError
from app.core.logging import get_logger, log_event

logger = get_logger(__name__)

_MOCK_DIMENSIONS = 256


class EmbeddingProvider(ABC):
    name: str = "base"
    dimensions: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic, offline, dependency-free — no model, no network."""

    name = "mock"
    dimensions = _MOCK_DIMENSIONS

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Real local embeddings via a running Ollama server."""

    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout_seconds: float = 30.0, dimensions: int = 768) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds
        self.dimensions = dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                for text in texts:
                    response = await client.post(
                        f"{self._base_url}/api/embeddings", json={"model": self._model, "prompt": text}
                    )
                    if response.status_code != 200:
                        raise ModelUnavailableError(
                            f"Ollama embeddings returned HTTP {response.status_code} for '{self._model}'.",
                            model=self._model,
                        )
                    body = response.json()
                    embedding = body.get("embedding")
                    if not embedding:
                        raise ModelUnavailableError(
                            f"Ollama returned no embedding for '{self._model}'.", model=self._model
                        )
                    vectors.append(embedding)
        except httpx.ConnectError as exc:
            raise ModelUnavailableError(
                f"Could not reach Ollama at {self._base_url} for embeddings. Is `ollama serve` running?",
                model=self._model,
            ) from exc
        except httpx.TimeoutException as exc:
            raise ModelUnavailableError(
                f"Ollama embeddings request timed out after {self._timeout:.0f}s.", model=self._model
            ) from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(f"Ollama embeddings request failed: {exc}", model=self._model) from exc

        log_event(logger, "embeddings_generated", provider="ollama", count=len(vectors))
        return vectors


_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    global _provider
    if _provider is not None:
        return _provider

    from app.core.config import get_settings

    settings = get_settings()
    if settings.embedding_provider == "ollama":
        _provider = OllamaEmbeddingProvider(
            base_url=settings.model_base_url,
            model=settings.embedding_model,
            timeout_seconds=settings.model_request_timeout_seconds,
        )
    else:
        _provider = MockEmbeddingProvider()
    return _provider
