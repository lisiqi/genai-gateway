"""Typed plan construction for controlled agent workflows."""

from __future__ import annotations

from genai_gateway.runtime.agent.schemas import AgentTaskRequest, PlanStep, StepType


class AgentPlanner:
    """Compile a task request into a bounded sequential plan."""

    def plan(self, request: AgentTaskRequest) -> list[PlanStep]:
        """Return a typed execution plan for the requested workflow."""
        if request.task_type.value == "answer_and_draft_email":
            return [
                PlanStep(
                    step_id="step_1",
                    step_type=StepType.retrieve_context,
                    title="Retrieve legal context",
                    capability_name="retrieve_context",
                    inputs={
                        "question": request.question,
                        "task": request.task,
                        "top_k": request.top_k,
                        "retrieval_mode": request.retrieval_mode,
                        "reranker_type": request.reranker_type,
                    },
                ),
                PlanStep(
                    step_id="step_2",
                    step_type=StepType.answer_question,
                    title="Answer from retrieved context",
                    capability_name="answer_question",
                    inputs={
                        "question": request.question,
                        "task": request.task,
                        "quality_mode": request.quality_mode,
                        "prompt_version": request.prompt_version,
                    },
                    depends_on=["step_1"],
                ),
                PlanStep(
                    step_id="step_3",
                    step_type=StepType.draft_email,
                    title="Draft follow-up email",
                    capability_name="draft_email",
                    inputs={
                        "recipient_email": request.recipient_email,
                        "question": request.question,
                    },
                    depends_on=["step_2"],
                ),
            ]
        raise ValueError(f"Unsupported task type '{request.task_type}'.")
