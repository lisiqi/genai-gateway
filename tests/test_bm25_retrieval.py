"""Unit tests for the lexical backend dispatch (FTS vs BM25, ADR 014)."""

from __future__ import annotations

import pytest

from genai_gateway.retrieval.query_builders import DefaultLexicalQueryBuilder, LexicalQuery
from genai_gateway.retrieval.retriever import RetrievalService


class RecordingRepository:
    """Fake repository that records which lexical method was called."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def search_lexical_chunks(self, **kwargs) -> list[dict]:
        self.calls.append(("fts", kwargs))
        return [{"chunk_id": "doc::chunk::0", "content": "fts result"}]

    def search_bm25_chunks(self, **kwargs) -> list[dict]:
        self.calls.append(("bm25", kwargs))
        return [{"chunk_id": "doc::chunk::1", "content": "bm25 result"}]


def _service_with_backend(backend: str) -> RetrievalService:
    service = RetrievalService()
    # model_copy avoids mutating the lru_cached global settings instance.
    service.settings = service.settings.model_copy(update={"retrieval_lexical_backend": backend})
    return service


def test_default_builder_emits_both_tsquery_and_match_text() -> None:
    query = DefaultLexicalQueryBuilder().build("What are the obligations for providers?")
    # FTS uses OR-joined tsquery syntax; BM25 uses the same terms, space-joined.
    assert query.tsquery_text is not None and " | " in query.tsquery_text
    assert query.match_text == query.tsquery_text.replace(" | ", " ")
    assert "obligations" in query.match_text and "providers" in query.match_text


def test_fts_backend_calls_search_lexical_chunks_with_tsquery_text() -> None:
    service = _service_with_backend("fts")
    repository = RecordingRepository()
    query = LexicalQuery(tsquery_text="obligations | providers", match_text="obligations providers")

    result = service._search_lexical(
        repository=repository,
        task="legal_qa",
        lexical_query=query,
        limit=5,
    )

    assert result[0]["chunk_id"] == "doc::chunk::0"
    backend, kwargs = repository.calls[0]
    assert backend == "fts"
    assert kwargs["query_text"] == "obligations | providers"
    assert kwargs["limit"] == 5


def test_bm25_backend_calls_search_bm25_chunks_with_match_text() -> None:
    service = _service_with_backend("bm25")
    repository = RecordingRepository()
    query = LexicalQuery(
        tsquery_text="obligations | providers",
        match_text="obligations providers",
        article_number="5",
    )

    result = service._search_lexical(
        repository=repository,
        task="legal_qa",
        lexical_query=query,
        limit=8,
    )

    assert result[0]["chunk_id"] == "doc::chunk::1"
    backend, kwargs = repository.calls[0]
    assert backend == "bm25"
    assert kwargs["query_text"] == "obligations providers"
    assert kwargs["article_number"] == "5"
    assert kwargs["limit"] == 8


def test_unsupported_backend_raises_clear_error() -> None:
    service = _service_with_backend("elasticsearch")
    with pytest.raises(ValueError, match="Unsupported lexical backend"):
        service._search_lexical(
            repository=RecordingRepository(),
            task="legal_qa",
            lexical_query=LexicalQuery(tsquery_text="x", match_text="x"),
            limit=3,
        )
