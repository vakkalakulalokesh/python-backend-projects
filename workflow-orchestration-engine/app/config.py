from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/workflow_db"
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    MAX_CONCURRENT_TASKS: int = 10
    TASK_DEFAULT_TIMEOUT: int = 300
    MAX_RETRY_ATTEMPTS: int = 3
    SCHEDULE_CHECK_INTERVAL: int = 60
    WS_REDIS_CHANNEL: str = "workflow:execution_events"


settings = Settings()
