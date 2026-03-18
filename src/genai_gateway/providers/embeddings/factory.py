"""Factory for selecting the active embedding provider."""

from __future__ import annotations

from functools import lru_cache

from genai_gateway.config.settings import get_settings
from genai_gateway.providers.embeddings.base import EmbeddingProvider
from genai_gateway.providers.embeddings.deterministic import DeterministicEmbeddingProvider
from genai_gateway.providers.embeddings.openai_provider import OpenAIEmbeddingProvider
from genai_gateway.providers.embeddings.tei_provider import TEIEmbeddingProvider


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    """Return the configured embedding provider."""
    settings = get_settings()

    if settings.embedding_provider == "deterministic":
        return DeterministicEmbeddingProvider()

    if settings.embedding_provider == "openai":
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
        )

    if settings.embedding_provider == "tei":
        return TEIEmbeddingProvider(
            base_url=settings.tei_base_url,
            model=settings.tei_model,
            dimensions=settings.tei_embedding_dimensions,
        )

    raise ValueError(
        f"Unsupported embedding provider: {settings.embedding_provider}. "
        "Expected one of: deterministic, openai, tei."
    )
