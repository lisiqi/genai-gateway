"""Unit tests for retrieval-mode selection and hybrid fusion."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from genai_gateway.retrieval.retriever import RetrievalService
from genai_gateway.retrieval.query_builders import DefaultLexicalQueryBuilder
from apps.legal_doc_qa.backend.retrieval import LegalDocQALexicalQueryBuilder


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.embed_calls: list[str] = []

    def embedding_config(self) -> dict[str, str | int]:
        return {"provider": "tei", "model": "test-embed", "dimensions": 3}

    def embed_text(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        return [0.1, 0.2, 0.3]


class FakeRepository:
    lexical_results: list[dict] = []
    dense_results: list[dict] = []

    def __init__(self, session: object) -> None:
        self.session = session
        self.validated_configs: list[dict[str, str | int]] = []

    def validate_embedding_config(self, *, task: str, active_embedding_config: dict[str, str | int]) -> None:
        self.validated_configs.append(active_embedding_config)

    def search_lexical_chunks(
        self,
        *,
        task: str,
        query_text: str | None,
        article_number: str | None = None,
        clause_number: str | None = None,
        limit: int,
    ) -> list[dict]:
        return self.lexical_results[:limit]

    def search_dense_chunks(self, *, task: str, query_embedding: list[float], limit: int) -> list[dict]:
        return self.dense_results[:limit]


class DummySessionLocal:
    def __call__(self) -> SimpleNamespace:
        class _SessionContext:
            def __enter__(self) -> object:
                return object()

            def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
                return False

        return _SessionContext()


@pytest.fixture
def retrieval_service(monkeypatch: pytest.MonkeyPatch) -> RetrievalService:
    import genai_gateway.retrieval.retriever as retriever_module

    monkeypatch.setattr(retriever_module, "SessionLocal", DummySessionLocal())
    monkeypatch.setattr(retriever_module, "RetrievalRepository", FakeRepository)

    service = RetrievalService()
    service.embedding_provider = FakeEmbeddingProvider()
    service.settings.retrieval_top_k = 4
    service.settings.retrieval_dense_top_k = 6
    service.settings.retrieval_lexical_top_k = 6
    service.settings.retrieval_rrf_k = 60
    service.settings.retrieval_query_builders_json = ""
    return service


class TestRetrievalService:
    def test_default_lexical_query_builder_is_generic(self) -> None:
        lexical_query = DefaultLexicalQueryBuilder().build(
            "What is the primary aim of the Digital Services Act according to Article 1?"
        )

        assert lexical_query.article_number == "1"
        assert lexical_query.clause_number is None
        assert lexical_query.tsquery_text == "primary | aim | digital | services | act | according"

    def test_legal_qa_lexical_query_builder_relaxes_natural_language_question(self) -> None:
        lexical_query = LegalDocQALexicalQueryBuilder().build(
            "What is the primary aim of the Digital Services Act according to Article 1?"
        )

        assert lexical_query.article_number == "1"
        assert lexical_query.clause_number is None
        assert lexical_query.tsquery_text == "primary | aim"

    def test_legal_qa_lexical_query_builder_extracts_article_and_clause_filters(self) -> None:
        lexical_query = LegalDocQALexicalQueryBuilder().build(
            "What types of services are excluded from the scope of this Regulation according to Article 2, Clause 2?"
        )

        assert lexical_query.article_number == "2"
        assert lexical_query.clause_number == "2"
        assert lexical_query.tsquery_text == "types | are | excluded | from | scope"

    def test_task_specific_query_builder_is_loaded_from_settings(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        retrieval_service.settings.retrieval_query_builders_json = (
            '{"legal_qa":"apps.legal_doc_qa.backend.retrieval:LegalDocQALexicalQueryBuilder"}'
        )

        lexical_query = retrieval_service.build_lexical_query(
            question="What is the primary aim of the Digital Services Act according to Article 1?",
            task="legal_qa",
        )

        assert lexical_query.tsquery_text == "primary | aim"

    def test_lexical_mode_does_not_call_embedding_provider(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        retrieval_service.settings.retrieval_mode = "lexical"
        FakeRepository.lexical_results = [{"chunk_id": "doc::chunk::1", "retrieval_sources": ["lexical"]}]
        FakeRepository.dense_results = []

        result = retrieval_service.retrieve(question="article 5", task="legal_qa")

        assert result == [{"chunk_id": "doc::chunk::1", "retrieval_sources": ["lexical"]}]
        assert retrieval_service.embedding_provider.embed_calls == []

    def test_dense_mode_uses_embedding_provider(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        retrieval_service.settings.retrieval_mode = "dense"
        FakeRepository.dense_results = [{"chunk_id": "doc::chunk::2", "retrieval_sources": ["dense"]}]
        FakeRepository.lexical_results = []

        result = retrieval_service.retrieve(question="article 5", task="legal_qa")

        assert result == [{"chunk_id": "doc::chunk::2", "retrieval_sources": ["dense"]}]
        assert retrieval_service.embedding_provider.embed_calls == ["article 5"]

    def test_request_level_override_can_force_lexical_mode(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        retrieval_service.settings.retrieval_mode = "hybrid"
        FakeRepository.lexical_results = [{"chunk_id": "doc::chunk::3", "retrieval_sources": ["lexical"]}]
        FakeRepository.dense_results = [{"chunk_id": "doc::chunk::9", "retrieval_sources": ["dense"]}]

        result = retrieval_service.retrieve(
            question="article 6",
            task="legal_qa",
            retrieval_mode="lexical",
        )

        assert result == [{"chunk_id": "doc::chunk::3", "retrieval_sources": ["lexical"]}]
        assert retrieval_service.embedding_provider.embed_calls == []

    def test_hybrid_mode_fuses_dense_and_lexical_rankings(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        retrieval_service.settings.retrieval_mode = "hybrid"
        FakeRepository.dense_results = [
            {
                "chunk_id": "doc::chunk::1",
                "content": "dense only",
                "dense_score": 0.91,
                "score": 0.91,
                "retrieval_sources": ["dense"],
            },
            {
                "chunk_id": "doc::chunk::2",
                "content": "shared",
                "dense_score": 0.83,
                "score": 0.83,
                "retrieval_sources": ["dense"],
            },
        ]
        FakeRepository.lexical_results = [
            {
                "chunk_id": "doc::chunk::2",
                "content": "shared",
                "lexical_score": 0.42,
                "score": 0.42,
                "retrieval_sources": ["lexical"],
            },
            {
                "chunk_id": "doc::chunk::3",
                "content": "lexical only",
                "lexical_score": 0.31,
                "score": 0.31,
                "retrieval_sources": ["lexical"],
            },
        ]

        result = retrieval_service.retrieve(question="digital services coordinators", task="legal_qa", top_k=3)

        assert [chunk["chunk_id"] for chunk in result] == [
            "doc::chunk::2",
            "doc::chunk::1",
            "doc::chunk::3",
        ]
        assert result[0]["retrieval_sources"] == ["dense", "lexical"]
        assert result[0]["dense_score"] == 0.83
        assert result[0]["lexical_score"] == 0.42
        assert result[0]["fusion_score"] > result[1]["fusion_score"]

    def test_invalid_retrieval_mode_raises_clear_error(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        with pytest.raises(ValueError, match="dense, lexical, hybrid"):
            retrieval_service.retrieve(question="article 5", task="legal_qa", retrieval_mode="unknown")
