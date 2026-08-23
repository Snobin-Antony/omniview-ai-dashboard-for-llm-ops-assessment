from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://omniview:omniview@localhost:5432/omniview"
    database_url_sync: str = "postgresql://omniview:omniview@localhost:5432/omniview"
    redis_url: str = "redis://localhost:6379/0"
    blob_root: str = "data/blobs"
    job_queue_key: str = "omniview:jobs"
    job_dlq_key: str = "omniview:jobs:dlq"
    lease_seconds: int = 60
    max_job_retries: int = 3
    mock_llm_delay_seconds: float = 2.0
    mock_llm_failure_rate: float = 0.0
    cors_origins: str = "http://localhost:5173"

    @property
    def resolved_blob_root(self) -> Path:
        p = Path(self.blob_root)
        if not p.is_absolute():
            p = ROOT / p
        return p

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
