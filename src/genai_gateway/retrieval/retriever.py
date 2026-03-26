"""Database-backed retrieval orchestration for the gateway MVP."""

from __future__ import annotations

from collections.abc import Iterable
import importlib
import json

from genai_gateway.config.settings import get_settings
from database.repositories import RetrievalRepository
from database.session import SessionLocal
from genai_gateway.providers.embeddings import get_embedding_provider
from genai_gateway.retrieval.query_builders import (
    DefaultLexicalQueryBuilder,
    LexicalQuery,
    LexicalQueryBuilder,
)


class RetrievalService:
    """Retrieval layer supporting dense, lexical, and hybrid search."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.embedding_provider = get_embedding_provider()
        self._lexical_query_builders: dict[str, LexicalQueryBuilder] = {}

    def retrieve(
        self,
        question: str,
        task: str,
        top_k: int | None = None,
        retrieval_mode: str | None = None,
    ) -> list[dict]:
        """Return the top-k similar chunks for the configured task."""
        k = top_k or self.settings.retrieval_top_k
        resolved_retrieval_mode = self.resolve_retrieval_mode(retrieval_mode)
        lexical_query = self.build_lexical_query(question=question, task=task)
        with SessionLocal() as session:
            repository = RetrievalRepository(session)
            if resolved_retrieval_mode == "lexical":
                return repository.search_lexical_chunks(
                    task=task,
                    query_text=lexical_query.tsquery_text,
                    article_number=lexical_query.article_number,
                    clause_number=lexical_query.clause_number,
                    limit=k,
                )

            active_embedding_config = self.embedding_provider.embedding_config()
            repository.validate_embedding_config(
                task=task,
                active_embedding_config=active_embedding_config,
            )
            query_embedding = self.embedding_provider.embed_text(question)
            if resolved_retrieval_mode == "dense":
                return repository.search_dense_chunks(
                    task=task,
                    query_embedding=query_embedding,
                    limit=k,
                )

            if resolved_retrieval_mode == "hybrid":
                dense_chunks = repository.search_dense_chunks(
                    task=task,
                    query_embedding=query_embedding,
                    limit=max(k, self.settings.retrieval_dense_top_k),
                )
                lexical_chunks = repository.search_lexical_chunks(
                    task=task,
                    query_text=lexical_query.tsquery_text,
                    article_number=lexical_query.article_number,
                    clause_number=lexical_query.clause_number,
                    limit=max(k, self.settings.retrieval_lexical_top_k),
                )
                return self._fuse_reciprocal_rank(
                    dense_chunks=dense_chunks,
                    lexical_chunks=lexical_chunks,
                    limit=k,
                    rrf_k=self.settings.retrieval_rrf_k,
                )

        raise ValueError(
            f"Unsupported retrieval mode '{resolved_retrieval_mode}'. "
            "Expected one of: dense, lexical, hybrid."
        )

    def resolve_retrieval_mode(self, override: str | None = None) -> str:
        """Resolve and normalize the retrieval mode for a request."""
        return (override or self.settings.retrieval_mode).strip().lower()

    def build_lexical_query(self, *, question: str, task: str) -> LexicalQuery:
        """Build a lexical query using the task-specific or default builder."""
        return self._get_lexical_query_builder(task).build(question)

    def _get_lexical_query_builder(self, task: str) -> LexicalQueryBuilder:
        """Resolve the lexical query builder for one task."""
        if task in self._lexical_query_builders:
            return self._lexical_query_builders[task]

        builder_mapping: dict[str, str] = {}
        if self.settings.retrieval_query_builders_json.strip():
            builder_mapping = json.loads(self.settings.retrieval_query_builders_json)

        import_path = builder_mapping.get(task)
        if import_path:
            module_name, class_name = import_path.split(":", maxsplit=1)
            module = importlib.import_module(module_name)
            builder = getattr(module, class_name)()
        else:
            builder = DefaultLexicalQueryBuilder()

        self._lexical_query_builders[task] = builder
        return builder

    @staticmethod
    def _fuse_reciprocal_rank(
        *,
        dense_chunks: Iterable[dict],
        lexical_chunks: Iterable[dict],
        limit: int,
        rrf_k: int,
    ) -> list[dict]:
        """Fuse dense and lexical rankings with reciprocal rank fusion."""
        dense_chunks = list(dense_chunks)
        lexical_chunks = list(lexical_chunks)
        fused_by_id: dict[str, dict] = {}
        fused_scores: dict[str, float] = {}
        dense_ranks = {chunk["chunk_id"]: index + 1 for index, chunk in enumerate(dense_chunks)}
        lexical_ranks = {chunk["chunk_id"]: index + 1 for index, chunk in enumerate(lexical_chunks)}

        for chunk_id, rank in dense_ranks.items():
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
        for chunk_id, rank in lexical_ranks.items():
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)

        for chunk in dense_chunks + lexical_chunks:
            chunk_id = chunk["chunk_id"]
            existing = fused_by_id.get(chunk_id)
            if existing is None:
                merged = dict(chunk)
                merged["retrieval_sources"] = list(chunk.get("retrieval_sources", []))
                fused_by_id[chunk_id] = merged
                continue

            existing_sources = set(existing.get("retrieval_sources", []))
            existing_sources.update(chunk.get("retrieval_sources", []))
            existing["retrieval_sources"] = sorted(existing_sources)
            for score_key in ("dense_score", "lexical_score"):
                if existing.get(score_key) is None and chunk.get(score_key) is not None:
                    existing[score_key] = chunk[score_key]

        ranked = sorted(
            fused_by_id.values(),
            key=lambda chunk: (
                -fused_scores[chunk["chunk_id"]],
                dense_ranks.get(chunk["chunk_id"], 10**9),
                lexical_ranks.get(chunk["chunk_id"], 10**9),
            ),
        )
        for chunk in ranked:
            chunk["score"] = fused_scores[chunk["chunk_id"]]
            chunk["fusion_score"] = fused_scores[chunk["chunk_id"]]
        return ranked[:limit]
