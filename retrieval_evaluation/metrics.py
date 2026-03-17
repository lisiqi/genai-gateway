"""Pure IR metrics for retrieval evaluation."""

from __future__ import annotations

import math


def hit_rate_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    return 1.0 if any(chunk_id in relevant_ids for chunk_id in retrieved_ids[:k]) else 0.0


def precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    hits = sum(1 for chunk_id in retrieved_ids[:k] if chunk_id in relevant_ids)
    return hits / k


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    hits = sum(1 for chunk_id in retrieved_ids[:k] if chunk_id in relevant_ids)
    return hits / len(relevant_ids)


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids or k <= 0:
        return 0.0

    dcg = sum(
        1.0 / math.log2(index + 1)
        for index, chunk_id in enumerate(retrieved_ids[:k], start=1)
        if chunk_id in relevant_ids
    )
    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def mrr(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for index, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant_ids:
            return 1.0 / index
    return 0.0


def compute_all(retrieved_ids: list[str], relevant_ids: set[str], k_values: list[int]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for k in k_values:
        metrics[f"hit_rate@{k}"] = hit_rate_at_k(retrieved_ids, relevant_ids, k)
        metrics[f"precision@{k}"] = precision_at_k(retrieved_ids, relevant_ids, k)
        metrics[f"recall@{k}"] = recall_at_k(retrieved_ids, relevant_ids, k)
        metrics[f"ndcg@{k}"] = ndcg_at_k(retrieved_ids, relevant_ids, k)
    metrics["mrr"] = mrr(retrieved_ids, relevant_ids)
    return metrics
