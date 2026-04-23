"""Implementacja providera dla Ollama API z obsługą timeoutów."""

from __future__ import annotations

import json
from typing import Any, Mapping

import httpx

from packages.providers.base import BaseLLMProvider


class OllamaProviderError(RuntimeError):
    """Błąd komunikacji lub normalizacji odpowiedzi Ollama."""


class OllamaProvider(BaseLLMProvider):
    """Provider integrujący się z endpointami /api/generate i /api/tags Ollama."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout_seconds)

    async def generate_text(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> str:
        payload = self._build_payload(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=metadata,
        )
        response_payload = await self._request_generate(payload)
        return self._normalize_text_response(response_payload)

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
        payload = self._build_payload(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=metadata,
        )
        payload["format"] = schema

        response_payload = await self._request_generate(payload)
        return self._normalize_structured_response(response_payload)

    async def healthcheck(self) -> bool:
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
                response = await client.get("/api/tags")
                response.raise_for_status()
            return True
        except (httpx.HTTPError, httpx.TimeoutException):
            return False

    async def model_info(self) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
            try:
                response = await client.get("/api/tags")
                response.raise_for_status()
            except httpx.TimeoutException as exc:
                raise OllamaProviderError("Timeout podczas pobierania informacji o modelu") from exc
            except httpx.HTTPError as exc:
                raise OllamaProviderError("Błąd HTTP podczas pobierania informacji o modelu") from exc

        payload = response.json()
        models = payload.get("models", [])
        matched = next((item for item in models if item.get("name") == self._model), None)
        return {
            "provider": "ollama",
            "base_url": self._base_url,
            "model": self._model,
            "model_available": matched is not None,
            "model_details": matched or {},
        }

    def _build_payload(
        self,
        *,
        prompt: str,
        system_prompt: str | None,
        temperature: float | None,
        max_tokens: int | None,
        metadata: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if options:
            payload["options"] = options
        if metadata:
            payload["metadata"] = dict(metadata)
        return payload

    async def _request_generate(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
            try:
                response = await client.post("/api/generate", json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as exc:
                raise OllamaProviderError("Timeout podczas generowania odpowiedzi") from exc
            except httpx.HTTPError as exc:
                raise OllamaProviderError("Błąd HTTP podczas generowania odpowiedzi") from exc
            except ValueError as exc:
                raise OllamaProviderError("Nieprawidłowy JSON w odpowiedzi Ollama") from exc

    @staticmethod
    def _normalize_text_response(payload: Mapping[str, Any]) -> str:
        raw = payload.get("response")
        if not isinstance(raw, str):
            raise OllamaProviderError("Pole 'response' nie jest tekstem")
        return raw.strip()

    @staticmethod
    def _normalize_structured_response(payload: Mapping[str, Any]) -> dict[str, Any]:
        raw = payload.get("response")
        if isinstance(raw, dict):
            return dict(raw)
        if not isinstance(raw, str):
            raise OllamaProviderError("Pole 'response' nie jest prawidłowym JSON-em")

        text = raw.strip()
        if not text:
            raise OllamaProviderError("Pusta odpowiedź dla danych ustrukturyzowanych")

        try:
            normalized = json.loads(text)
        except json.JSONDecodeError as exc:
            raise OllamaProviderError("Nie można zdekodować JSON-a z odpowiedzi modelu") from exc

        if not isinstance(normalized, dict):
            raise OllamaProviderError("Odpowiedź ustrukturyzowana musi być obiektem JSON")
        return normalized
