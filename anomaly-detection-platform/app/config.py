from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@postgres:5432/anomaly_db"
    )
    REDIS_URL: str = "redis://redis:6379/0"
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"

    DETECTION_WINDOW_SIZE: int = 100
    ZSCORE_THRESHOLD: float = 3.0
    IQR_MULTIPLIER: float = 1.5
    EWMA_SPAN: int = 20
    ANOMALY_COOLDOWN_SECONDS: int = 300

    METRICS_RETENTION_DAYS: int = 90
    RESOLVED_ANOMALY_ARCHIVE_DAYS: int = 365


settings = Settings()
