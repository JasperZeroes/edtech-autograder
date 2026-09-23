from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GradingSettings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    judge0_base_url: str = "http://localhost:2358"
    judge0_python_language_id: int = Field(default=71, gt=0)
    judge0_request_timeout_seconds: float = Field(default=20.0, gt=0)

    openai_api_key: str | None = None
    openai_feedback_model: str = "gpt-5.6-luna"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_request_timeout_seconds: float = Field(default=20.0, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_grading_settings() -> GradingSettings:
    return GradingSettings()
