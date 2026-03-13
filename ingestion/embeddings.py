"""Embedding helpers.

This module remains as a thin compatibility layer while the project moves to
provider-based embeddings.
"""

from __future__ import annotations

from providers.embeddings import get_embedding_provider


def embed_text(text: str) -> list[float]:
    """Embed a single text using the configured provider."""
    return get_embedding_provider().embed_text(text)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using the configured provider."""
    return get_embedding_provider().embed_texts(texts)
