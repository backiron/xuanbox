from functools import cached_property

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "XuanBox"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "xuanbox"
    POSTGRES_USER: str = "xuanbox"
    POSTGRES_PASSWORD: str = "xuanbox_dev_password"

    REDIS_URL: str = "redis://redis:6379/0"

    JWT_SECRET_KEY: str = Field(
        default="change-me-in-production",
        min_length=16,
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    STORAGE_ROOT: str = "/data/xuanbox/storage"
    MASTER_KEY: str = Field(
        default="dev-only-change-this-master-key",
        min_length=24,
    )
    BACKUP_SCHEDULE_HOURS: int = Field(default=24, ge=0)

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8080,http://127.0.0.1:5173"
    CORS_ALLOW_ORIGIN_REGEX: str | None = (
        r"https?://(localhost|127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|"
        r"192\.168\.\d{1,3}\.\d{1,3})(:\d+)?"
    )

    RECEIPT_AI_ASSIST_ENABLED: bool = False
    RECEIPT_AI_MODEL: str = "qwen2.5:3b"
    RECEIPT_AI_BASE_URL: str = "http://host.docker.internal:11434"
    RECEIPT_AI_TIMEOUT_SECONDS: int = Field(default=20, ge=1, le=120)
    RECEIPT_AI_MAX_CHARS: int = Field(default=6000, ge=500, le=20000)

    DOCUMENT_AI_ENABLED: bool = False
    DOCUMENT_AI_MODEL: str = "qwen2.5:3b"
    DOCUMENT_AI_BASE_URL: str = "http://host.docker.internal:11434"
    DOCUMENT_AI_TIMEOUT_SECONDS: int = Field(default=30, ge=1, le=120)
    DOCUMENT_AI_MAX_CHARS: int = Field(default=6000, ge=500, le=20000)
    DOCUMENT_AI_CONCURRENCY: int = Field(default=1, ge=1, le=4)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        return value.strip()

    @field_validator("CORS_ALLOW_ORIGIN_REGEX")
    @classmethod
    def validate_cors_regex(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @cached_property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @cached_property
    def sync_database_url(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @cached_property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
