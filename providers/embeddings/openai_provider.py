"""OpenAI embedding provider."""

from __future__ import annotations

from openai import OpenAI

from providers.embeddings.base import EmbeddingProvider


OPENAI_EMBEDDING_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by the OpenAI embeddings API."""

    def __init__(self, *, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set for the OpenAI embedding provider.")
        self._model = model
        self._client = OpenAI(api_key=api_key)
        self._dimensions = OPENAI_EMBEDDING_DIMENSIONS.get(model, 1536)

    @property
    def provider_name(self) -> str:
        """Return the logical provider name."""
        return "openai"

    @property
    def model_name(self) -> str:
        """Return the logical model name."""
        return self._model

    @property
    def dimensions(self) -> int:
        """Return the embedding vector dimensions."""
        return self._dimensions

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text using the OpenAI embeddings API."""
        response = self._client.embeddings.create(
            model=self._model,
            input=text,
        )
        return list(response.data[0].embedding)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts using the OpenAI embeddings API."""
        response = self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [list(item.embedding) for item in response.data]
