"""Unit tests for structured request logging helpers."""

from __future__ import annotations

from typing import Any

from genai_gateway.observability.request_logger import RequestLogger
from genai_gateway.runtime.agent.orchestrator import AgentOrchestrator
from genai_gateway.runtime.agent.schemas import AgentTaskRequest
from genai_gateway.runtime.agent.state import AgentExecutionState


class FakeExecutor:
    """Small fake executor for request-logger tests."""

    def execute(self, *, capability_name: str, inputs: dict[str, Any], state: AgentExecutionState) -> dict[str, Any]:
        if capability_name == "retrieve_context":
            chunks = [
                {
                    "chunk_id": "doc::chunk::0",
                    "source": "doc.pdf",
                    "content": "Article 12 legal text",
                    "metadata": {"article_number": "12"},
                }
            ]
            state.retrieved_chunks = chunks
            return {
                "retrieved_chunks": chunks,
                "retrieval_count": 1,
                "retrieval_mode": "hybrid",
                "reranker_type": "pass_through",
            }
        if capability_name == "answer_question":
            state.answer = "Article 12 requires the provider to keep records."
            state.answer_metadata = {
                "provider": "openrouter",
                "model": "demo-model",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            }
            return {
                "answer": state.answer,
                "provider": "openrouter",
                "model": "demo-model",
                "estimated_cost_usd": 0.001,
                "pricing_source": "test",
            }
        if capability_name == "draft_email":
            state.email_draft = {
                "subject": "Legal QA summary",
                "body": "Here is the summary.",
                "recipient_email": inputs.get("recipient_email"),
            }
            return state.email_draft
        raise AssertionError(f"unexpected capability {capability_name}")


def test_agent_log_helpers_build_dashboard_friendly_trace(tmp_path) -> None:
    logger = RequestLogger(log_path=str(tmp_path / "requests.jsonl"))
    orchestrator = AgentOrchestrator(executor=FakeExecutor())
    report = orchestrator.run(
        AgentTaskRequest(
            instruction="Answer the question and draft an email.",
            question="What does Article 12 say?",
            recipient_email="legal@example.com",
        )
    )

    trace_events = logger._build_agent_trace_events(report)

    assert any(event["stage"] == "retrieval.search" for event in trace_events)
    assert any(event["stage"] == "generation.answer" for event in trace_events)
    assert any(event["stage"] == "generation.draft_email" for event in trace_events)
    assert logger._compute_agent_latency_ms(report) >= 0.0
