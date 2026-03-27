"""Structured request logging."""

import json
from datetime import UTC, datetime
from pathlib import Path

from database.models import Evaluation, QueryLog
from database.session import SessionLocal
from genai_gateway.runtime.agent import AgentExecutionReport, AgentTaskRequest
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
                request_kind="query",
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
                    provider_reported_cost_usd=response.evaluation.provider_reported_cost_usd,
                    provider_generation_id=response.evaluation.provider_generation_id,
                    provider_usage_source=response.evaluation.provider_usage_source,
                    latency_ms=response.latency_ms,
                    prompt_tokens=response.token_usage.prompt_tokens,
                    completion_tokens=response.token_usage.completion_tokens,
                    total_tokens=response.token_usage.total_tokens,
                    notes=response.evaluation.routing_notes,
                )
            )
            session.commit()

        self._append_jsonl(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "request_kind": "query",
                "request": request.model_dump(),
                "response": response.model_dump(),
            }
        )

    def log_agent_run(self, request: AgentTaskRequest, report: AgentExecutionReport) -> None:
        """Persist a controlled agent runtime execution record."""
        final_output = report.final_output or {}
        answer_metadata = final_output.get("answer_metadata") or {}
        retrieved_chunks = final_output.get("retrieved_chunks") or []
        retrieved_chunk_ids = [
            chunk.get("chunk_id")
            for chunk in retrieved_chunks
            if isinstance(chunk, dict) and chunk.get("chunk_id")
        ]
        trace_json = self._build_agent_trace_events(report)
        latency_ms = self._compute_agent_latency_ms(report)
        retrieval_step = self._find_step(report=report, step_type="retrieve_context")
        answer_step = self._find_step(report=report, step_type="answer_question")
        answer_checkpoint = answer_step.get("checkpoint") if answer_step else None
        answer_output = answer_step.get("output") if answer_step else {}

        with SessionLocal() as session:
            query_log = QueryLog(
                request_kind="agent_run",
                task=request.task,
                quality_mode=request.quality_mode,
                prompt_version=request.prompt_version,
                agent_run_id=report.run_id,
                agent_task_type=report.task_type.value,
                instruction=request.instruction,
                agent_status=report.status.value,
                agent_stop_reason=report.stop_reason,
                agent_step_count=len(report.steps),
                agent_report_json=report.model_dump(mode="json"),
                selected_provider=answer_metadata.get("provider"),
                model_name=answer_metadata.get("model"),
                reranker_type=(
                    (retrieval_step or {}).get("output", {}).get("reranker_type")
                    or request.reranker_type
                ),
                reranker_top_k=None,
                fallback_used=bool(answer_metadata.get("fallback_used")),
                routing_reason=report.stop_reason,
                question=request.question,
                answer=str(final_output.get("answer") or ""),
                latency_ms=latency_ms,
                prompt_tokens=int(answer_metadata.get("prompt_tokens") or 0),
                completion_tokens=int(answer_metadata.get("completion_tokens") or 0),
                total_tokens=int(answer_metadata.get("total_tokens") or 0),
                retrieved_chunk_ids=retrieved_chunk_ids,
                trace_json=trace_json,
                status=report.status.value,
            )
            session.add(query_log)
            session.flush()

            if answer_checkpoint is not None:
                checkpoint_metrics = answer_checkpoint.get("metrics") or {}
                session.add(
                    Evaluation(
                        query_log_id=query_log.id,
                        groundedness_score=float(checkpoint_metrics.get("groundedness") or 0.0),
                        answer_relevance_score=float(
                            checkpoint_metrics.get("answer_relevance") or 0.0
                        ),
                        citation_score=float(checkpoint_metrics.get("citation_score") or 0.0),
                        completeness_score=float(
                            checkpoint_metrics.get("completeness") or 0.0
                        ),
                        estimated_cost_usd=float(answer_output.get("estimated_cost_usd") or 0.0),
                        input_cost_usd=0.0,
                        output_cost_usd=0.0,
                        pricing_source=answer_output.get("pricing_source"),
                        cost_is_estimated=answer_output.get("provider_reported_cost_usd") is None,
                        provider_reported_cost_usd=answer_output.get(
                            "provider_reported_cost_usd"
                        ),
                        provider_generation_id=answer_output.get("provider_generation_id"),
                        provider_usage_source=answer_output.get("provider_usage_source"),
                        latency_ms=float(answer_step.get("latency_ms") or latency_ms),
                        prompt_tokens=int(answer_metadata.get("prompt_tokens") or 0),
                        completion_tokens=int(answer_metadata.get("completion_tokens") or 0),
                        total_tokens=int(answer_metadata.get("total_tokens") or 0),
                        notes=answer_checkpoint.get("reason"),
                    )
                )
            session.commit()

        self._append_jsonl(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "request_kind": "agent_run",
                "request": request.model_dump(mode="json"),
                "response": report.model_dump(mode="json"),
            }
        )

    def _append_jsonl(self, record: dict) -> None:
        """Append one structured record to the local JSONL log."""
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def _find_step(self, *, report: AgentExecutionReport, step_type: str) -> dict | None:
        """Return the first step of the requested type from a report."""
        for step in report.model_dump(mode="json").get("steps", []):
            if step.get("step_type") == step_type:
                return step
        return None

    def _compute_agent_latency_ms(self, report: AgentExecutionReport) -> float:
        """Compute run latency in milliseconds from the report timestamps."""
        if report.completed_at is None:
            return 0.0
        return round((report.completed_at - report.created_at).total_seconds() * 1000, 2)

    def _build_agent_trace_events(self, report: AgentExecutionReport) -> list[dict]:
        """Build lightweight trace events from agent step execution for dashboard use."""
        trace_events: list[dict] = []
        report_dump = report.model_dump(mode="json")
        for step in report_dump.get("steps", []):
            step_type = step.get("step_type")
            metadata = {
                "step_id": step.get("step_id"),
                "status": step.get("status"),
            }
            output = step.get("output") or {}
            checkpoint = step.get("checkpoint") or {}
            if step_type == "retrieve_context":
                stage = "retrieval.search"
                metadata["retrieval_mode"] = output.get("retrieval_mode")
                metadata["retrieval_count"] = output.get("retrieval_count")
                metadata["reranker_type"] = output.get("reranker_type")
            elif step_type == "answer_question":
                stage = "generation.answer"
                metadata["provider"] = output.get("provider")
                metadata["model"] = output.get("model")
            elif step_type == "draft_email":
                stage = "generation.draft_email"
            else:
                stage = f"agent.{step_type}"
            trace_events.append(
                {
                    "stage": stage,
                    "duration_ms": float(step.get("latency_ms") or 0.0),
                    "metadata": metadata,
                }
            )
            if checkpoint:
                trace_events.append(
                    {
                        "stage": f"checkpoint.{step_type}",
                        "duration_ms": 0.0,
                        "metadata": {
                            "decision": checkpoint.get("decision"),
                            "reason": checkpoint.get("reason"),
                            "metrics": checkpoint.get("metrics") or {},
                        },
                    }
                )
        return trace_events
