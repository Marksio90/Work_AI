"""Modele polityki wykonania zadania."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StrictnessLevel(str, Enum):
    """Poziom rygoru walidacyjnego i wykonawczego."""

    LENIENT = "lenient"
    STANDARD = "standard"
    STRICT = "strict"


class PipelineMode(str, Enum):
    """Tryb działania pipeline."""

    SERIAL = "serial"
    PARALLEL = "parallel"
    MAP_REDUCE = "map_reduce"


class RetryPolicy(BaseModel):
    """Konfiguracja ponowień."""

    model_config = ConfigDict(extra="forbid")

    max_attempts: int = Field(default=1, ge=1, le=20)
    backoff_seconds: float = Field(default=0.0, ge=0.0)
    exponential_backoff: bool = Field(default=True)


class TimeoutPolicy(BaseModel):
    """Timeouty poszczególnych etapów."""

    model_config = ConfigDict(extra="forbid")

    queue_timeout_seconds: float = Field(default=30.0, ge=0.0)
    execution_timeout_seconds: float = Field(default=120.0, gt=0.0)
    total_timeout_seconds: float = Field(default=300.0, gt=0.0)


class ExecutionPolicy(BaseModel):
    """Polityka wykonania obejmująca timeouty, retry i tryb pipeline."""

    model_config = ConfigDict(extra="forbid")

    timeouts: TimeoutPolicy = Field(default_factory=TimeoutPolicy)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    strictness: StrictnessLevel = Field(default=StrictnessLevel.STANDARD)
    abstain_allowed: bool = Field(default=True)
    pipeline_mode: PipelineMode = Field(default=PipelineMode.SERIAL)
