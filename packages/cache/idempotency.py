"""Redis-backed idempotency and dedup helpers."""

from __future__ import annotations

import json

from redis import Redis

from packages.config import get_settings


class IdempotencyManager:
    def __init__(self, redis_client: Redis | None = None) -> None:
        settings = get_settings()
        self._ttl = settings.idempotency_ttl_seconds
        self._dedup_ttl = settings.dedup_ttl_seconds
        self._redis = redis_client or Redis.from_url(settings.redis_url, decode_responses=True)

    def register_idempotency(self, key: str, task_id: str) -> bool:
        return bool(self._redis.set(f"idem:{key}", task_id, ex=self._ttl, nx=True))

    def get_task_for_idempotency(self, key: str) -> str | None:
        return self._redis.get(f"idem:{key}")

    def register_dedup(self, dedup_key: str, payload: dict) -> bool:
        value = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return bool(self._redis.set(f"dedup:{dedup_key}", value, ex=self._dedup_ttl, nx=True))
