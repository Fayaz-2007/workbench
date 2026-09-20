"""Real local vision inference via a running Ollama server.

Separate from `OllamaProvider` (the text-only provider) on purpose: a
vision-capable Ollama model (e.g. `qwen2.5vl:3b`) takes an extra `images`
field in the `/api/generate` payload — base64-encoded image bytes, sent
alongside the text prompt — and the text provider must never grow that
concern just to support Vision Agent. Every failure mode (unreachable
Ollama, missing model, bad response) becomes a `ModelUnavailableError`
with a message that tells the operator exactly what to do — never a
silent fallback to mock/placeholder output (see `app/agents/vision.py`).
"""

from __future__ import annotations

import base64
import time
from collections.abc import AsyncIterator

import httpx

from app.core.exceptions import ModelUnavailableError
from app.core.logging import get_logger, log_event
from app.models.base import BaseModelProvider, GenerationResult, ModelInfo, ProviderHealth

logger = get_logger(__name__)


class OllamaVisionProvider(BaseModelProvider):
    """Talks to Ollama's `/api/generate` with an `images` payload for real,
    local multimodal generation.
    """

    name = "ollama_vision"

    def __init__(self, base_url: str, timeout_seconds: float = 60.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    async def generate(
        self, *, model: ModelInfo, prompt: str, images: list[bytes] | None = None
    ) -> GenerationResult:
        started = time.perf_counter()
        payload: dict[str, object] = {"model": model.identifier, "prompt": prompt, "stream": False}
        if images:
            payload["images"] = [base64.b64encode(image).decode("ascii") for image in images]

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(f"{self._base_url}/api/generate", json=payload)
        except httpx.ConnectError as exc:
            raise ModelUnavailableError(
                f"Local vision model unavailable. Start Ollama and ensure {model.identifier} is installed.",
                model_id=model.id,
            ) from exc
        except httpx.TimeoutException as exc:
            raise ModelUnavailableError(
                f"Ollama did not respond within {self._timeout:.0f}s for vision model '{model.identifier}'.",
                model_id=model.id,
            ) from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(f"Ollama vision request failed: {exc}", model_id=model.id) from exc

        if response.status_code == 404:
            raise ModelUnavailableError(
                f"Local vision model unavailable. Start Ollama and ensure {model.identifier} is installed "
                f"(run `ollama pull {model.identifier}`).",
                model_id=model.id,
            )
        if response.status_code != 200:
            raise ModelUnavailableError(
                f"Ollama returned HTTP {response.status_code} for vision model '{model.identifier}'.",
                model_id=model.id,
            )

        body = response.json()
        text = (body.get("response") or "").strip()
        if not text:
            raise ModelUnavailableError(
                f"Ollama returned an empty response for vision model '{model.identifier}'.", model_id=model.id
            )

        latency_ms = (time.perf_counter() - started) * 1000
        log_event(
            logger,
            "ollama_vision_generation_completed",
            model_id=model.id,
            latency_ms=round(latency_ms),
            image_count=len(images or []),
        )
        return GenerationResult(text=text, model_id=model.id, is_mock=False, latency_ms=latency_ms)

    async def stream(self, *, model: ModelInfo, prompt: str, images: list[bytes] | None = None) -> AsyncIterator[str]:
        # Not wired to an API route yet — same as the text provider's
        # documented status (see `BaseModelProvider.stream`). Implemented
        # via `generate()` rather than duplicating request/error handling
        # for a path nothing currently calls.
        result = await self.generate(model=model, prompt=prompt, images=images)
        for chunk in result.text.split(" "):
            yield chunk + " "

    async def health_check(self) -> ProviderHealth:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
        except httpx.HTTPError as exc:
            return ProviderHealth(healthy=False, detail=f"Ollama unreachable at {self._base_url}: {exc}")

        if response.status_code == 200:
            return ProviderHealth(healthy=True, detail=f"Ollama reachable at {self._base_url}")
        return ProviderHealth(healthy=False, detail=f"Ollama returned HTTP {response.status_code}")
