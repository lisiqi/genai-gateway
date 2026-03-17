"""Structured request logging."""

import json
from datetime import UTC, datetime
from pathlib import Path

from database.models import Evaluation, QueryLog
from database.session import SessionLocal
from app.schemas.request_schema import QueryRequest
from app.schemas.response_schema import QueryResponse


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
                prompt_version=request.prompt_version,
                model_name=response.model_name,
                question=request.question,
                answer=response.answer,
                latency_ms=response.latency_ms,
                prompt_tokens=response.token_usage.prompt_tokens,
                completion_tokens=response.token_usage.completion_tokens,
                total_tokens=response.token_usage.total_tokens,
                retrieved_chunk_ids=retrieved_chunk_ids,
                status="completed",
            )
            session.add(query_log)
            session.flush()

            session.add(
                Evaluation(
                    query_log_id=query_log.id,
                    groundedness_score=response.evaluation.groundedness_score,
                    estimated_cost_usd=response.evaluation.estimated_cost_usd,
                    latency_ms=response.latency_ms,
                    prompt_tokens=response.token_usage.prompt_tokens,
                    completion_tokens=response.token_usage.completion_tokens,
                    total_tokens=response.token_usage.total_tokens,
                    notes=None,
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
