"""Unit tests for the controlled agent runtime."""

from __future__ import annotations

from typing import Any

from genai_gateway.runtime.agent.orchestrator import AgentOrchestrator
from genai_gateway.runtime.agent.planner import AgentPlanner
from genai_gateway.runtime.agent.schemas import AgentTaskRequest, RunStatus, StepType
from genai_gateway.runtime.agent.state import AgentExecutionState


class FakeExecutor:
    """Small fake executor for orchestrator tests."""

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
            state.answer_metadata = {"provider": "openrouter", "model": "demo-model"}
            return {
                "answer": state.answer,
                "provider": "openrouter",
                "model": "demo-model",
            }
        if capability_name == "draft_email":
            state.email_draft = {
                "subject": "Legal QA summary",
                "body": "Here is the summary.",
                "recipient_email": inputs.get("recipient_email"),
            }
            return state.email_draft
        raise AssertionError(f"unexpected capability {capability_name}")


def test_planner_builds_three_step_plan() -> None:
    planner = AgentPlanner()
    plan = planner.plan(
        AgentTaskRequest(
            instruction="Answer the question and draft an email.",
            question="What does Article 12 say?",
        )
    )

    assert [step.step_type for step in plan] == [
        StepType.retrieve_context,
        StepType.answer_question,
        StepType.draft_email,
    ]
    assert plan[1].depends_on == ["step_1"]
    assert plan[2].depends_on == ["step_2"]


def test_orchestrator_aborts_off_topic_request() -> None:
    orchestrator = AgentOrchestrator(executor=FakeExecutor())

    report = orchestrator.run(
        AgentTaskRequest(
            instruction="Answer the question and draft an email.",
            question="What is the weather in Amsterdam today?",
        )
    )

    assert report.status == RunStatus.aborted
    assert report.steps == []
    assert "off-topic" in (report.stop_reason or "")


def test_orchestrator_completes_happy_path() -> None:
    orchestrator = AgentOrchestrator(executor=FakeExecutor())

    report = orchestrator.run(
        AgentTaskRequest(
            instruction="Answer the question and draft an email.",
            question="What does Article 12 say?",
            recipient_email="legal@example.com",
        )
    )

    assert report.status == RunStatus.completed
    assert len(report.steps) == 3
    assert report.final_output["answer"] == "Article 12 requires the provider to keep records."
    assert report.final_output["email_draft"]["recipient_email"] == "legal@example.com"
