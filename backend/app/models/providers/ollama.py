"""Real local inference via a running Ollama server.

Ollama (https://ollama.com) serves open-weight models over a local HTTP
API — no cloud SDK, no API key, and (per `MODEL_BASE_URL`) no address
other than the organization's own machine/LAN. Every failure mode
(unreachable, timeout, bad response) becomes a `ModelUnavailableError` —
never an unhandled exception, never a crash, never a stack trace to the
client (see app/core/exceptions.py).
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

import httpx

from app.core.exceptions import ModelUnavailableError
from app.core.logging import get_logger, log_event
from app.models.base import BaseModelProvider, GenerationResult, ModelInfo, ProviderHealth

logger = get_logger(__name__)


class OllamaProvider(BaseModelProvider):
    """Talks to Ollama's `/api/generate` for real, local text generation."""

    name = "ollama"

    def __init__(self, base_url: str, timeout_seconds: float = 60.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    async def generate(
        self, *, model: ModelInfo, prompt: str, images: list[bytes] | None = None
    ) -> GenerationResult:
        # `images` is accepted for interface parity with `BaseModelProvider`
        # but intentionally unused: this provider only ever serves the
        # text model (see `OllamaVisionProvider` for the image-carrying path).
        started = time.perf_counter()
        payload = {"model": model.identifier, "prompt": prompt, "stream": False}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(f"{self._base_url}/api/generate", json=payload)
        except httpx.ConnectError as exc:
            raise ModelUnavailableError(
                f"Could not reach Ollama at {self._base_url}. Is `ollama serve` running?",
                model_id=model.id,
            ) from exc
        except httpx.TimeoutException as exc:
            raise ModelUnavailableError(
                f"Ollama did not respond within {self._timeout:.0f}s.", model_id=model.id
            ) from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(f"Ollama request failed: {exc}", model_id=model.id) from exc

        if response.status_code == 404:
            raise ModelUnavailableError(
                f"Model '{model.identifier}' is not pulled in Ollama. Run `ollama pull {model.identifier}`.",
                model_id=model.id,
            )
        if response.status_code != 200:
            raise ModelUnavailableError(
                f"Ollama returned HTTP {response.status_code} for '{model.identifier}'.", model_id=model.id
            )

        body = response.json()
        text = (body.get("response") or "").strip()
        if not text:
            raise ModelUnavailableError(
                f"Ollama returned an empty response for '{model.identifier}'.", model_id=model.id
            )

        latency_ms = (time.perf_counter() - started) * 1000
        log_event(logger, "ollama_generation_completed", model_id=model.id, latency_ms=round(latency_ms))
        return GenerationResult(text=text, model_id=model.id, is_mock=False, latency_ms=latency_ms)

    async def stream(self, *, model: ModelInfo, prompt: str) -> AsyncIterator[str]:
        payload = {"model": model.identifier, "prompt": prompt, "stream": True}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream("POST", f"{self._base_url}/api/generate", json=payload) as response:
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        chunk = json.loads(line)
                        if chunk.get("response"):
                            yield chunk["response"]
                        if chunk.get("done"):
                            break
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(f"Ollama streaming failed: {exc}", model_id=model.id) from exc

    async def health_check(self) -> ProviderHealth:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
        except httpx.HTTPError as exc:
            return ProviderHealth(healthy=False, detail=f"Ollama unreachable at {self._base_url}: {exc}")

        if response.status_code == 200:
            return ProviderHealth(healthy=True, detail=f"Ollama reachable at {self._base_url}")
        return ProviderHealth(healthy=False, detail=f"Ollama returned HTTP {response.status_code}")
