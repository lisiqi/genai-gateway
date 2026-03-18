"""TEI embedding provider."""

from __future__ import annotations

from collections.abc import Callable

from openai import OpenAI

from genai_gateway.providers.embeddings.base import EmbeddingProvider


class TEIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by a local TEI service."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        dimensions: int,
        max_batch_size: int = 32,
    ) -> None:
        self._model = model
        self._dimensions = dimensions
        self._max_batch_size = max_batch_size
        normalized_base_url = base_url.rstrip("/")
        self._client = OpenAI(
            api_key="tei-local",
            base_url=normalized_base_url,
        )

    @property
    def provider_name(self) -> str:
        """Return the logical provider name."""
        return "tei"

    @property
    def model_name(self) -> str:
        """Return the logical model name."""
        return self._model

    @property
    def dimensions(self) -> int:
        """Return the embedding vector dimensions."""
        return self._dimensions

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text using the TEI OpenAI-compatible endpoint."""
        response = self._client.embeddings.create(
            model=self._model,
            input=text,
        )
        return list(response.data[0].embedding)

    def embed_texts(
        self,
        texts: list[str],
        *,
        progress_callback: Callable[[int, int, int], None] | None = None,
    ) -> list[list[float]]:
        """Embed a batch of texts using the TEI OpenAI-compatible endpoint."""
        if not texts:
            return []

        embeddings: list[list[float]] = []
        for start in range(0, len(texts), self._max_batch_size):
            batch = texts[start : start + self._max_batch_size]
            response = self._client.embeddings.create(
                model=self._model,
                input=batch,
            )
            embeddings.extend(list(item.embedding) for item in response.data)
            if progress_callback is not None:
                progress_callback(min(start + len(batch), len(texts)), len(texts), len(batch))
        return embeddings
