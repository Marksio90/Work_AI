"""Fabryka providerów LLM na bazie konfiguracji."""

from __future__ import annotations

from typing import Any, Mapping

from packages.providers.base import BaseLLMProvider
from packages.providers.mock_provider import MockProvider
from packages.providers.ollama_provider import OllamaProvider


def create_provider(config: Mapping[str, Any]) -> BaseLLMProvider:
    """Zwraca instancję providera na podstawie klucza `provider`.

    Oczekiwane pola:
      - provider: "ollama" | "mock"
      - model: nazwa modelu
      - base_url: opcjonalnie dla Ollama
      - timeout_seconds: opcjonalnie dla Ollama
      - healthy: opcjonalnie dla Mock
    """

    provider_name = str(config.get("provider", "")).strip().lower()
    model = str(config.get("model", "")).strip()

    if provider_name == "ollama":
        if not model:
            raise ValueError("Dla providera 'ollama' wymagane jest pole 'model'.")
        base_url = str(config.get("base_url", "http://localhost:11434"))
        timeout_seconds = float(config.get("timeout_seconds", 30.0))
        return OllamaProvider(model=model, base_url=base_url, timeout_seconds=timeout_seconds)

    if provider_name == "mock":
        if not model:
            model = "mock-model"
        healthy = bool(config.get("healthy", True))
        return MockProvider(model=model, healthy=healthy)

    raise ValueError(f"Nieobsługiwany provider: {provider_name!r}")
