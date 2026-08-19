from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_path: str = Field(default="state.db", description="SQLite database file path")
    log_level: str = Field(default="INFO", description="Logging level")
    fts5_query_limit: int = Field(default=10, ge=1, le=100, description="Max FTS5 search results")
    retrieval_keyword_limit: int = Field(default=5, ge=1, le=50, description="Keyword search limit")
    retrieval_recent_limit: int = Field(default=10, ge=1, le=100, description="Recent facts limit")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def ensure_db_dir(settings: Settings) -> None:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)