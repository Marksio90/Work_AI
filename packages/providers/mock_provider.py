"""Deterministyczny provider mock do testów."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from packages.providers.base import BaseLLMProvider


class MockProvider(BaseLLMProvider):
    """Provider zwracający przewidywalne odpowiedzi bazujące na wejściu."""

    def __init__(self, *, model: str = "mock-model", healthy: bool = True) -> None:
        self._model = model
        self._healthy = healthy

    async def generate_text(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> str:
        key = self._build_key(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=metadata,
        )
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        return f"mock:{digest}"

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
        text = await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=metadata,
        )
        return {
            "mock": True,
            "model": self._model,
            "text": text,
            "schema_keys": sorted(schema.keys()),
        }

    async def healthcheck(self) -> bool:
        return self._healthy

    async def model_info(self) -> dict[str, Any]:
        return {
            "provider": "mock",
            "model": self._model,
            "healthy": self._healthy,
        }

    @staticmethod
    def _build_key(
        *,
        prompt: str,
        system_prompt: str | None,
        temperature: float | None,
        max_tokens: int | None,
        metadata: Mapping[str, Any] | None,
    ) -> str:
        return "|".join(
            [
                prompt,
                system_prompt or "",
                "" if temperature is None else str(temperature),
                "" if max_tokens is None else str(max_tokens),
                "" if metadata is None else str(sorted(metadata.items())),
            ]
        )
