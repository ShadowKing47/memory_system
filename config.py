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

    # OpenRouter
    openrouter_api_key: str = Field(default="", description="OpenRouter API key")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", description="OpenRouter base URL")

    # Consolidation
    consolidation_model: str = Field(default="nvidia/nemotron-3-ultra-550b-a55b:free", description="Consolidation model")
    consolidation_max_tokens: int = Field(default=1024, ge=100, le=4096, description="Max tokens for consolidation")
    consolidation_temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="Temperature for consolidation")
    consolidation_prompt_version: str = Field(default="latest", description="Prompt version for consolidation")

    # Worker
    dream_interval_minutes: int = Field(default=60, ge=1, le=1440, description="Dream interval in minutes")
    dream_batch_size: int = Field(default=50, ge=1, le=500, description="Batch size for consolidation")
    dream_min_messages: int = Field(default=10, ge=1, le=100, description="Minimum messages for consolidation")

    # Prompts directory
    prompts_dir: str = Field(default="src/memory/prompts", description="Prompts directory path")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def ensure_db_dir(settings: Settings) -> None:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)