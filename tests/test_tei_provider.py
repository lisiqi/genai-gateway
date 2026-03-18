"""Unit tests for the TEI embedding provider."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from genai_gateway.providers.embeddings.tei_provider import TEIEmbeddingProvider


def _response_for(batch: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        data=[SimpleNamespace(embedding=[float(index), float(index) + 0.5]) for index, _ in enumerate(batch)]
    )


class TestTEIEmbeddingProvider:
    def test_embed_texts_splits_requests_by_batch_size(self) -> None:
        provider = TEIEmbeddingProvider(
            base_url="http://localhost:8080/v1",
            model="test-model",
            dimensions=2,
            max_batch_size=2,
        )
        create = MagicMock(side_effect=lambda *, model, input: _response_for(input))
        provider._client = SimpleNamespace(embeddings=SimpleNamespace(create=create))

        texts = ["one", "two", "three", "four", "five"]
        result = provider.embed_texts(texts)

        assert create.call_count == 3
        assert [call.kwargs["input"] for call in create.call_args_list] == [
            ["one", "two"],
            ["three", "four"],
            ["five"],
        ]
        assert result == [
            [0.0, 0.5],
            [1.0, 1.5],
            [0.0, 0.5],
            [1.0, 1.5],
            [0.0, 0.5],
        ]

    def test_embed_texts_returns_empty_without_api_call(self) -> None:
        provider = TEIEmbeddingProvider(
            base_url="http://localhost:8080/v1",
            model="test-model",
            dimensions=2,
        )
        create = MagicMock()
        provider._client = SimpleNamespace(embeddings=SimpleNamespace(create=create))

        result = provider.embed_texts([])

        assert result == []
        create.assert_not_called()
