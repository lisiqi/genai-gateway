"""Reranking implementations for retrieval results."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from genai_gateway.config.settings import get_settings


class Reranker(ABC):
    """Common reranker interface."""

    @abstractmethod
    def rerank(self, question: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return reranked chunks for a user question."""

    @property
    @abstractmethod
    def config_summary(self) -> dict[str, Any]:
        """Return a serializable reranker summary."""


class PassThroughReranker(Reranker):
    """Default reranker that preserves retrieval order."""

    def rerank(self, question: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return chunks unchanged."""
        return chunks

    @property
    def config_summary(self) -> dict[str, Any]:
        """Return pass-through reranker config."""
        return {
            "reranker_type": "pass_through",
            "reranker_model": None,
            "reranker_top_k": None,
        }


class CrossEncoderReranker(Reranker):
    """Rerank chunks with a sentence-transformers cross-encoder."""

    def __init__(self, model_name: str, top_k: int | None = None) -> None:
        self.model_name = model_name
        self.top_k = top_k
        self._model: Any | None = None

    def rerank(self, question: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Score `(question, chunk)` pairs and sort descending."""
        if not chunks:
            return chunks

        model = self._get_model()
        pairs = [(question, str(chunk.get("content", ""))) for chunk in chunks]
        scores = model.predict(pairs)

        reranked: list[dict[str, Any]] = []
        for score, chunk in sorted(zip(scores, chunks), key=lambda item: item[0], reverse=True):
            updated_chunk = dict(chunk)
            updated_chunk["rerank_score"] = float(score)
            reranked.append(updated_chunk)

        limit = self.top_k if self.top_k is not None else len(reranked)
        return reranked[:limit]

    def _get_model(self) -> Any:
        """Load the cross-encoder lazily."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise ImportError(
                    "sentence-transformers is required for cross-encoder reranking. "
                    "Install with: uv sync --extra reranking"
                ) from exc
            self._model = CrossEncoder(self.model_name)
        return self._model

    @property
    def config_summary(self) -> dict[str, Any]:
        """Return cross-encoder reranker config."""
        return {
            "reranker_type": "cross_encoder",
            "reranker_model": self.model_name,
            "reranker_top_k": self.top_k,
        }


def get_reranker() -> Reranker:
    """Build the configured reranker."""
    settings = get_settings()
    reranker_type = settings.reranker_type.strip().lower()
    if reranker_type == "pass_through":
        return PassThroughReranker()
    if reranker_type == "cross_encoder":
        return CrossEncoderReranker(
            model_name=settings.reranker_model,
            top_k=settings.reranker_top_k,
        )
    raise ValueError(
        f"Unsupported reranker type '{settings.reranker_type}'. "
        "Expected one of: pass_through, cross_encoder."
    )
