from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentSettings(BaseSettings):
    """Shared environment-file behaviour for application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class DatabaseSettings(EnvironmentSettings):
    database_url: str = Field(alias="DATABASE_URL")


class AuthSettings(EnvironmentSettings):
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY", min_length=32)
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_minutes: int = Field(
        default=30,
        alias="JWT_ACCESS_TOKEN_MINUTES",
        gt=0,
    )
    jwt_refresh_token_days: int = Field(
        default=7,
        alias="JWT_REFRESH_TOKEN_DAYS",
        gt=0,
    )


@lru_cache
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings()
