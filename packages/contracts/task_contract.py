"""Model wejściowego kontraktu zadania."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from packages.contracts.enums import TaskType
from packages.contracts.execution_policy import ExecutionPolicy


class TaskContract(BaseModel):
    """Opis zadania przekazywanego do wykonania."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    task_type: TaskType
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    execution_policy: ExecutionPolicy = Field(default_factory=ExecutionPolicy)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def deterministic_json(self) -> str:
        """Zwraca deterministyczny JSON (sortowane klucze) użyteczny m.in. do fingerprintu."""

        payload = self.model_dump(mode="json", exclude_none=False, by_alias=True)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def fingerprint(self) -> str:
        """Zwraca stabilny fingerprint SHA-256 dla kontraktu."""

        return hashlib.sha256(self.deterministic_json().encode("utf-8")).hexdigest()
