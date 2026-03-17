"""Indexing helpers for retrieval ingestion."""

from genai_gateway.providers.embeddings import get_embedding_provider


def get_active_embedding_config() -> dict[str, str | int]:
    """Return the embedding configuration used for indexing and retrieval."""
    provider = get_embedding_provider()
    return provider.embedding_config()
