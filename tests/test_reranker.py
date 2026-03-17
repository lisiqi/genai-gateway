"""Unit tests for retrieval rerankers."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from genai_gateway.retrieval.reranker import CrossEncoderReranker, PassThroughReranker


def _make_chunks(*contents: str) -> list[dict]:
    return [{"chunk_id": f"chunk-{index}", "content": content} for index, content in enumerate(contents)]


class TestPassThroughReranker:
    def test_returns_chunks_unchanged(self) -> None:
        reranker = PassThroughReranker()
        chunks = _make_chunks("a", "b", "c")

        result = reranker.rerank("query", chunks)

        assert result == chunks


class TestCrossEncoderReranker:
    def test_empty_list_returns_empty(self) -> None:
        reranker = CrossEncoderReranker("cross-encoder/ms-marco-MiniLM-L-6-v2")

        assert reranker.rerank("query", []) == []

    def test_reranks_by_descending_score(self) -> None:
        chunks = _make_chunks("low", "high", "medium")
        reranker = CrossEncoderReranker("cross-encoder/ms-marco-MiniLM-L-6-v2")
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.1, 0.9, 0.5]
        reranker._model = mock_model

        result = reranker.rerank("query", chunks)

        assert [chunk["content"] for chunk in result] == ["high", "medium", "low"]
        assert result[0]["rerank_score"] == 0.9

    def test_top_k_truncates_results(self) -> None:
        chunks = _make_chunks("a", "b", "c", "d")
        reranker = CrossEncoderReranker("cross-encoder/ms-marco-MiniLM-L-6-v2", top_k=2)
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.2, 0.8, 0.6, 0.4]
        reranker._model = mock_model

        result = reranker.rerank("query", chunks)

        assert len(result) == 2
        assert [chunk["content"] for chunk in result] == ["b", "c"]

    def test_predict_receives_query_content_pairs(self) -> None:
        chunks = _make_chunks("chunk A", "chunk B")
        reranker = CrossEncoderReranker("cross-encoder/ms-marco-MiniLM-L-6-v2")
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.5, 0.7]
        reranker._model = mock_model

        reranker.rerank("what is article 5", chunks)

        assert mock_model.predict.call_args[0][0] == [
            ("what is article 5", "chunk A"),
            ("what is article 5", "chunk B"),
        ]

    def test_missing_sentence_transformers_raises_helpful_error(self) -> None:
        reranker = CrossEncoderReranker("cross-encoder/ms-marco-MiniLM-L-6-v2")

        with patch.dict(sys.modules, {"sentence_transformers": None}):
            with pytest.raises(ImportError, match="uv sync --extra reranking"):
                reranker._get_model()
