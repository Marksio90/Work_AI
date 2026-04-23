"""Runtime configuration with profile support."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from env and `.env` files."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "work-ai"
    env_profile: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "sqlite+pysqlite:///./work_ai.db"
    redis_url: str = "redis://localhost:6379/0"

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_soft_time_limit: int = 90
    celery_task_time_limit: int = 120

    idempotency_ttl_seconds: int = Field(default=24 * 3600, ge=1)
    dedup_ttl_seconds: int = Field(default=3600, ge=1)


    provider_name: str = "mock"
    provider_model: str = "mock-model"

    task_source_name: str = "mock_marketplace"
    task_source_poll_batch_size: int = Field(default=10, ge=1, le=200)
    task_source_poll_interval_seconds: int = Field(default=30, ge=5)

    economics_min_margin_usd: float = Field(default=0.005, ge=0.0)
    economics_default_success_probability: float = Field(default=0.85, ge=0.0, le=1.0)
    economics_infra_cost_per_task_usd: float = Field(default=0.002, ge=0.0)
    economics_token_cost_per_1k_usd: float = Field(default=0.0015, ge=0.0)

    @property
    def is_prod(self) -> bool:
        return self.env_profile == "prod"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Returns memoized settings instance."""

    return Settings()
