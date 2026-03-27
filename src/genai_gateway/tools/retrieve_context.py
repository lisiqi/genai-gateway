"""Retrieve and rerank legal document context."""

from __future__ import annotations

from typing import Any

from genai_gateway.retrieval.reranker import get_reranker
from genai_gateway.retrieval.retriever import RetrievalService
from genai_gateway.runtime.agent.state import AgentExecutionState
from genai_gateway.tools.base import AgentCapability


class RetrieveContextCapability(AgentCapability):
    """Capability for retrieval-backed context acquisition."""

    name = "retrieve_context"

    def __init__(self, retrieval_service: RetrievalService | None = None) -> None:
        self.retrieval_service = retrieval_service or RetrievalService()

    def execute(self, *, inputs: dict[str, Any], state: AgentExecutionState) -> dict[str, Any]:
        """Retrieve and rerank chunks for the requested question."""
        question = str(inputs["question"])
        task = str(inputs.get("task") or state.task)
        top_k = inputs.get("top_k")
        retrieval_mode = inputs.get("retrieval_mode")
        reranker_type = inputs.get("reranker_type")
        retrieved = self.retrieval_service.retrieve(
            question=question,
            task=task,
            top_k=top_k,
            retrieval_mode=retrieval_mode,
        )
        reranker = get_reranker(reranker_type=reranker_type)
        reranked = reranker.rerank(question, retrieved)
        state.retrieved_chunks = reranked
        return {
            "retrieved_chunks": reranked,
            "retrieval_count": len(reranked),
            "retrieval_mode": self.retrieval_service.resolve_retrieval_mode(retrieval_mode),
            "reranker_type": reranker.config_summary["reranker_type"],
        }
