"""Application settings."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "genai-gateway"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    chat_provider: str = "openai"
    model_routing_rules_json: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4.1-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_http_referer: str = ""
    openrouter_title: str = "genai-gateway"
    embedding_provider: str = "deterministic"
    embedding_model: str = "text-embedding-3-small"
    tei_base_url: str = "http://localhost:8080/v1"
    tei_model: str = "Qwen/Qwen3-Embedding-0.6B"
    tei_embedding_dimensions: int = 1024
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/genai_gateway"
    database_echo: bool = False
    prompt_root: str = "apps/legal_doc_qa/backend/prompts"
    default_task: str = "legal_qa"
    default_prompt_version: str = "v1"
    retrieval_query_builders_json: str = ""
    retrieval_mode: str = "hybrid"
    retrieval_top_k: int = 4
    retrieval_dense_top_k: int = 12
    retrieval_lexical_top_k: int = 12
    retrieval_rrf_k: int = 60
    guardrails_enabled: bool = True
    reranker_type: str = "pass_through"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_top_k: int | None = None

    @field_validator("reranker_top_k", mode="before")
    @classmethod
    def _normalize_empty_top_k(cls, value: object) -> object:
        """Treat empty env values as `None` for optional integer settings."""
        if value == "":
            return None
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object."""
    return Settings()
