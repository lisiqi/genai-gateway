"""Embedding provider abstractions and implementations."""

from genai_gateway.providers.embeddings.base import EmbeddingProvider
from genai_gateway.providers.embeddings.deterministic import DeterministicEmbeddingProvider
from genai_gateway.providers.embeddings.factory import get_embedding_provider
from genai_gateway.providers.embeddings.openai_provider import OpenAIEmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "DeterministicEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "get_embedding_provider",
]
