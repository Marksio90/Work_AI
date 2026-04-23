"""Bazowy interfejs dla providerów LLM.

Provider nie powinien znać warstwy domenowej ani orchestratora.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping


class BaseLLMProvider(ABC):
    """Kontrakt dla wszystkich providerów modeli językowych."""

    @abstractmethod
    async def generate_text(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> str:
        """Wygeneruj odpowiedź tekstową na podstawie promptu."""

    @abstractmethod
    async def generate_structured(
        self,
        *,
        prompt: str,
        schema: Mapping[str, Any],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Wygeneruj odpowiedź ustrukturyzowaną zgodną ze schematem JSON."""

    @abstractmethod
    async def healthcheck(self) -> bool:
        """Sprawdź dostępność i podstawową gotowość providera."""

    @abstractmethod
    async def model_info(self) -> dict[str, Any]:
        """Zwróć metadane o modelu i konfiguracji providera."""
