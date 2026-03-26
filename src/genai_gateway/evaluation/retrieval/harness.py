"""Offline retrieval evaluation harness."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from genai_gateway.evaluation.retrieval.datasets import EvaluationDataset
from genai_gateway.evaluation.retrieval.metrics import compute_all
from genai_gateway.retrieval.reranker import get_reranker
from genai_gateway.retrieval.retriever import RetrievalService


@dataclass
class RetrievalEvaluationResult:
    """Per-sample retrieval evaluation output."""

    question: str
    relevant_chunk_ids: list[str]
    retrieved_ids: list[str]
    metrics: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "relevant_chunk_ids": self.relevant_chunk_ids,
            "retrieved_ids": self.retrieved_ids,
            "metrics": self.metrics,
        }


@dataclass
class RetrievalEvaluationReport:
    """Aggregated retrieval evaluation report."""

    results: list[RetrievalEvaluationResult]
    aggregate: dict[str, float]
    n_samples: int
    k_values: list[int]
    config: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": [result.to_dict() for result in self.results],
            "aggregate": self.aggregate,
            "n_samples": self.n_samples,
            "k_values": self.k_values,
            "config": self.config,
        }


class RetrievalEvaluationRunner:
    """Run retrieval evaluation for a task corpus using the gateway retrieval service."""

    def __init__(self, retrieval_service: RetrievalService | None = None) -> None:
        self.retrieval_service = retrieval_service or RetrievalService()

    def run(
        self,
        dataset: EvaluationDataset,
        *,
        task: str,
        k_values: list[int] | None = None,
        reranker_type: str | None = None,
        reranker_model: str | None = None,
        reranker_top_k: int | None = None,
        extra_config: dict[str, Any] | None = None,
    ) -> RetrievalEvaluationReport:
        if k_values is None:
            k_values = [1, 3, 5, 10]

        top_k = max(k_values)
        reranker = get_reranker(
            reranker_type=reranker_type,
            model_name=reranker_model,
            top_k=reranker_top_k,
        )
        results: list[RetrievalEvaluationResult] = []
        for sample in dataset:
            retrieved = self.retrieval_service.retrieve(sample.question, task=task, top_k=top_k)
            reranked = reranker.rerank(sample.question, retrieved)
            retrieved_ids = [row["chunk_id"] for row in reranked]
            metrics = compute_all(retrieved_ids, set(sample.relevant_chunk_ids), k_values)
            results.append(
                RetrievalEvaluationResult(
                    question=sample.question,
                    relevant_chunk_ids=sample.relevant_chunk_ids,
                    retrieved_ids=retrieved_ids,
                    metrics=metrics,
                )
            )

        aggregate = _aggregate_metrics(results)
        embedding_config: dict[str, Any] = {}
        embedding_provider = getattr(self.retrieval_service, "embedding_provider", None)
        if embedding_provider is not None and hasattr(embedding_provider, "embedding_config"):
            embedding_config = embedding_provider.embedding_config()
        settings = getattr(self.retrieval_service, "settings", None)
        retrieval_mode = (
            self.retrieval_service.resolve_retrieval_mode()
            if hasattr(self.retrieval_service, "resolve_retrieval_mode")
            else None
        )
        config = {
            "task": task,
            "top_k": top_k,
            "k_values": k_values,
            "retrieval_mode": retrieval_mode,
            "retrieval_dense_top_k": getattr(settings, "retrieval_dense_top_k", None),
            "retrieval_lexical_top_k": getattr(settings, "retrieval_lexical_top_k", None),
            "retrieval_rrf_k": getattr(settings, "retrieval_rrf_k", None),
            "embedding_provider": embedding_config.get("provider"),
            "embedding_model": embedding_config.get("model"),
            "embedding_dimensions": embedding_config.get("dimensions"),
            "reranker_type": reranker.config_summary.get("reranker_type"),
            "reranker_model": reranker.config_summary.get("reranker_model"),
            "reranker_top_k": reranker.config_summary.get("reranker_top_k"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        if extra_config:
            config.update(extra_config)
        return RetrievalEvaluationReport(
            results=results,
            aggregate=aggregate,
            n_samples=len(results),
            k_values=k_values,
            config=config,
        )


def _aggregate_metrics(results: list[RetrievalEvaluationResult]) -> dict[str, float]:
    if not results:
        return {}
    keys = list(results[0].metrics.keys())
    return {
        key: sum(result.metrics[key] for result in results) / len(results)
        for key in keys
    }
