"""Application settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "genai-gateway"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    embedding_provider: str = "deterministic"
    embedding_model: str = "text-embedding-3-small"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/genai_gateway"
    database_echo: bool = False
    prompt_root: str = "apps/legal_doc_qa/backend/prompts"
    default_task: str = "legal_qa"
    default_prompt_version: str = "v1"
    retrieval_top_k: int = 4


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object."""
    return Settings()
