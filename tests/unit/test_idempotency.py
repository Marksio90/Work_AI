import pytest

pytest.importorskip("pydantic_settings")

from packages.cache.idempotency import IdempotencyManager


class FakeRedis:
    def __init__(self) -> None:
        self.store = {}

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    def get(self, key):
        return self.store.get(key)


def test_idempotency_and_dedup_registration():
    manager = IdempotencyManager(redis_client=FakeRedis())

    assert manager.register_idempotency("req-1", "task-1") is True
    assert manager.register_idempotency("req-1", "task-2") is False
    assert manager.get_task_for_idempotency("req-1") == "task-1"

    assert manager.register_dedup("dedup-1", {"a": 1}) is True
    assert manager.register_dedup("dedup-1", {"a": 1}) is False
