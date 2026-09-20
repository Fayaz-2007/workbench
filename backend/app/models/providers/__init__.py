"""Model provider implementations and a small name → instance factory.

Each `ModelInfo.provider` value (`"local"` or `"ollama"` today) resolves to
one `BaseModelProvider` instance here. Adding a new backend later
(llama.cpp, vLLM) means adding one more entry to `_build_providers` —
nothing in `app.agents` or `app.models.router` needs to change.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.exceptions import ModelUnavailableError
from app.models.base import BaseModelProvider
from app.models.providers.local import LocalModelProvider
from app.models.providers.ollama import OllamaProvider
from app.models.providers.ollama_vision import OllamaVisionProvider

_providers: dict[str, BaseModelProvider] | None = None


def _build_providers() -> dict[str, BaseModelProvider]:
    settings = get_settings()
    return {
        "local": LocalModelProvider(),
        "ollama": OllamaProvider(
            base_url=settings.model_base_url,
            timeout_seconds=settings.model_request_timeout_seconds,
        ),
        "ollama_vision": OllamaVisionProvider(
            base_url=settings.model_base_url,
            timeout_seconds=settings.model_request_timeout_seconds,
        ),
    }


def get_provider(name: str) -> BaseModelProvider:
    global _providers
    if _providers is None:
        _providers = _build_providers()
    try:
        return _providers[name]
    except KeyError as exc:
        raise ModelUnavailableError(f"No provider registered for '{name}'.", provider=name) from exc


__all__ = ["get_provider", "LocalModelProvider", "OllamaProvider", "OllamaVisionProvider"]
