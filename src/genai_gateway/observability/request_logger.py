"""Structured request logging."""

import json
from datetime import UTC, datetime
from pathlib import Path

from database.models import Evaluation, QueryLog
from database.session import SessionLocal
from genai_gateway.schemas.request_schema import QueryRequest
from genai_gateway.schemas.response_schema import QueryResponse


class RequestLogger:
    """Persists request/evaluation records to Postgres and a local JSONL log."""

    def __init__(self, log_path: str = "logs/requests.jsonl") -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, request: QueryRequest, response: QueryResponse) -> None:
        """Persist a request record."""
        retrieved_chunk_ids = [chunk.chunk_id for chunk in response.retrieved_chunks]
        with SessionLocal() as session:
            query_log = QueryLog(
                task=request.task,
                quality_mode=request.quality_mode,
                prompt_version=request.prompt_version,
                selected_provider=response.routing.selected_provider,
                model_name=response.model_name,
                reranker_type=response.reranking.reranker_type,
                reranker_model=response.reranking.reranker_model,
                reranker_top_k=response.reranking.reranker_top_k,
                fallback_used=response.routing.fallback_used,
                fallback_provider=response.routing.fallback_provider,
                fallback_model=response.routing.fallback_model,
                routing_reason=response.routing.reason,
                question=request.question,
                answer=response.answer,
                latency_ms=response.latency_ms,
                prompt_tokens=response.token_usage.prompt_tokens,
                completion_tokens=response.token_usage.completion_tokens,
                total_tokens=response.token_usage.total_tokens,
                retrieved_chunk_ids=retrieved_chunk_ids,
                trace_json=response.trace.model_dump()["events"],
                status="completed",
            )
            session.add(query_log)
            session.flush()

            session.add(
                Evaluation(
                    query_log_id=query_log.id,
                    groundedness_score=response.evaluation.groundedness_score,
                    answer_relevance_score=response.evaluation.answer_relevance_score,
                    citation_score=response.evaluation.citation_score,
                    completeness_score=response.evaluation.completeness_score,
                    estimated_cost_usd=response.evaluation.estimated_cost_usd,
                    input_cost_usd=response.evaluation.input_cost_usd,
                    output_cost_usd=response.evaluation.output_cost_usd,
                    pricing_source=response.evaluation.pricing_source,
                    cost_is_estimated=response.evaluation.cost_is_estimated,
                    latency_ms=response.latency_ms,
                    prompt_tokens=response.token_usage.prompt_tokens,
                    completion_tokens=response.token_usage.completion_tokens,
                    total_tokens=response.token_usage.total_tokens,
                    notes=response.evaluation.routing_notes,
                )
            )
            session.commit()

        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "request": request.model_dump(),
            "response": response.model_dump(),
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
