"""Offline retrieval evaluation harness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from genai_gateway.evaluation.retrieval.datasets import EvaluationDataset
from genai_gateway.evaluation.retrieval.metrics import compute_all
from genai_gateway.retrieval.retriever import RetrievalService


@dataclass
class RetrievalEvaluationResult:
    """Per-sample retrieval evaluation output."""

    question: str
    relevant_chunk_ids: list[str]
    retrieved_ids: list[str]
    metrics: dict[str, float]


@dataclass
class RetrievalEvaluationReport:
    """Aggregated retrieval evaluation report."""

    results: list[RetrievalEvaluationResult]
    aggregate: dict[str, float]
    n_samples: int
    k_values: list[int]
    config: dict[str, Any]


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
    ) -> RetrievalEvaluationReport:
        if k_values is None:
            k_values = [1, 3, 5, 10]

        top_k = max(k_values)
        results: list[RetrievalEvaluationResult] = []
        for sample in dataset:
            retrieved = self.retrieval_service.retrieve(sample.question, task=task, top_k=top_k)
            retrieved_ids = [row["chunk_id"] for row in retrieved]
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
        return RetrievalEvaluationReport(
            results=results,
            aggregate=aggregate,
            n_samples=len(results),
            k_values=k_values,
            config={"task": task, "top_k": top_k},
        )


def _aggregate_metrics(results: list[RetrievalEvaluationResult]) -> dict[str, float]:
    if not results:
        return {}
    keys = list(results[0].metrics.keys())
    return {
        key: sum(result.metrics[key] for result in results) / len(results)
        for key in keys
    }
