"""Deterministic local embedding provider for development."""

from __future__ import annotations

import hashlib

from providers.embeddings.base import EmbeddingProvider


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """API-free embedding provider used for local development and tests."""

    def __init__(self, dimensions: int = 1536) -> None:
        self._dimensions = dimensions

    @property
    def provider_name(self) -> str:
        """Return the logical provider name."""
        return "deterministic"

    @property
    def model_name(self) -> str:
        """Return the logical model name."""
        return "deterministic-local"

    @property
    def dimensions(self) -> int:
        """Return the embedding vector dimensions."""
        return self._dimensions

    def embed_text(self, text: str) -> list[float]:
        """Return a deterministic embedding vector for one text."""
        values: list[float] = []
        counter = 0
        while len(values) < self._dimensions:
            digest = hashlib.sha256(f"{counter}:{text}".encode("utf-8")).digest()
            values.extend(((byte / 255.0) * 2.0) - 1.0 for byte in digest)
            counter += 1
        return values[: self._dimensions]
