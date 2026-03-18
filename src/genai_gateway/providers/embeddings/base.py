"""Embedding provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the logical provider name."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the logical model name."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding vector dimensions."""

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string."""

    def embed_texts(
        self,
        texts: list[str],
        *,
        progress_callback: Callable[[int, int, int], None] | None = None,
    ) -> list[list[float]]:
        """Embed a batch of texts.

        Providers may override this for more efficient batching.
        """
        embeddings: list[list[float]] = []
        total = len(texts)
        for index, text in enumerate(texts, start=1):
            embeddings.append(self.embed_text(text))
            if progress_callback is not None:
                progress_callback(index, total, 1)
        return embeddings

    def embedding_config(self) -> dict[str, str | int]:
        """Return the embedding configuration fingerprint for stored corpora."""
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "dimensions": self.dimensions,
        }
