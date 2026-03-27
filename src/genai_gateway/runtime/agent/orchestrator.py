"""Controlled sequential orchestrator for Phase 1 agent execution."""

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from genai_gateway.evaluation.response import (
    score_answer_relevance,
    score_citation_presence,
    score_completeness,
    score_groundedness,
)
from genai_gateway.runtime.agent.executor import ToolExecutor
from genai_gateway.runtime.agent.planner import AgentPlanner
from genai_gateway.runtime.agent.schemas import (
    AgentExecutionReport,
    AgentTaskRequest,
    CheckpointDecision,
    CheckpointResult,
    RunStatus,
    StepResult,
    StepStatus,
    StepType,
)
from genai_gateway.runtime.agent.state import AgentExecutionState
from genai_gateway.runtime.guardrails import assess_retrieval_evidence, classify_request_scope


class AgentOrchestrator:
    """Run a bounded typed workflow with checkpoints after each step."""

    def __init__(
        self,
        *,
        planner: AgentPlanner | None = None,
        executor: ToolExecutor | None = None,
    ) -> None:
        self.planner = planner or AgentPlanner()
        self.executor = executor or ToolExecutor()

    def run(self, request: AgentTaskRequest) -> AgentExecutionReport:
        """Execute the Phase 1 controlled workflow."""
        created_at = datetime.now(UTC)
        run_id = f"agent_{uuid4().hex[:12]}"
        scope = classify_request_scope(question=request.question, task=request.task)
        plan = self.planner.plan(request)
        if scope.status != "in_scope":
            return AgentExecutionReport(
                run_id=run_id,
                task_type=request.task_type,
                status=RunStatus.aborted,
                created_at=created_at,
                completed_at=datetime.now(UTC),
                request=request,
                plan=plan,
                steps=[],
                final_output={},
                stop_reason=scope.reason,
            )

        state = AgentExecutionState(request=request)
        step_results: list[StepResult] = []
        status = RunStatus.running
        stop_reason: str | None = None

        for step in plan:
            started_at = datetime.now(UTC)
            started = perf_counter()
            try:
                output = self.executor.execute(
                    capability_name=step.capability_name,
                    inputs=step.inputs,
                    state=state,
                )
                latency_ms = round((perf_counter() - started) * 1000, 2)
                checkpoint = self._checkpoint(step_type=step.step_type, state=state, output=output)
                step_status = (
                    StepStatus.completed
                    if checkpoint.decision == CheckpointDecision.allow
                    else StepStatus.aborted
                )
                step_results.append(
                    StepResult(
                        step_id=step.step_id,
                        step_type=step.step_type,
                        title=step.title,
                        capability_name=step.capability_name,
                        status=step_status,
                        started_at=started_at,
                        completed_at=datetime.now(UTC),
                        latency_ms=latency_ms,
                        inputs=step.inputs,
                        output=output,
                        checkpoint=checkpoint,
                    )
                )
                if checkpoint.decision != CheckpointDecision.allow:
                    status = RunStatus.aborted
                    stop_reason = checkpoint.reason
                    break
            except Exception as exc:
                latency_ms = round((perf_counter() - started) * 1000, 2)
                step_results.append(
                    StepResult(
                        step_id=step.step_id,
                        step_type=step.step_type,
                        title=step.title,
                        capability_name=step.capability_name,
                        status=StepStatus.failed,
                        started_at=started_at,
                        completed_at=datetime.now(UTC),
                        latency_ms=latency_ms,
                        inputs=step.inputs,
                        output={},
                        error=str(exc),
                    )
                )
                status = RunStatus.failed
                stop_reason = str(exc)
                break
        else:
            status = RunStatus.completed

        final_output = {}
        if status == RunStatus.completed:
            final_output = {
                "answer": state.answer,
                "email_draft": state.email_draft,
                "answer_metadata": state.answer_metadata,
                "retrieved_chunks": state.retrieved_chunks,
            }

        return AgentExecutionReport(
            run_id=run_id,
            task_type=request.task_type,
            status=status,
            created_at=created_at,
            completed_at=datetime.now(UTC),
            request=request,
            plan=plan,
            steps=step_results,
            final_output=final_output,
            stop_reason=stop_reason,
        )

    def _checkpoint(
        self,
        *,
        step_type: StepType,
        state: AgentExecutionState,
        output: dict,
    ) -> CheckpointResult:
        """Evaluate one step output and decide whether execution continues."""
        if step_type == StepType.retrieve_context:
            retrieved_chunks = output.get("retrieved_chunks", [])
            if not retrieved_chunks:
                return CheckpointResult(
                    decision=CheckpointDecision.abort,
                    reason="No supporting context was retrieved.",
                    metrics={"retrieval_count": 0.0},
                )
            evidence = assess_retrieval_evidence(
                question=state.request.question,
                retrieved_chunks=retrieved_chunks,
            )
            decision = (
                CheckpointDecision.allow
                if evidence.status == "sufficient"
                else CheckpointDecision.abort
            )
            return CheckpointResult(
                decision=decision,
                reason=evidence.reason,
                metrics={"retrieval_count": float(len(retrieved_chunks))},
            )

        if step_type == StepType.answer_question:
            answer = str(output.get("answer", ""))
            groundedness = score_groundedness(answer=answer, retrieved_chunks=state.retrieved_chunks)
            answer_relevance = score_answer_relevance(question=state.request.question, answer=answer)
            citation_score = score_citation_presence(answer=answer)
            completeness = score_completeness(answer=answer, retrieved_chunks=state.retrieved_chunks)
            decision = (
                CheckpointDecision.allow
                if answer.strip() and groundedness >= 1.0
                else CheckpointDecision.abort
            )
            reason = (
                "Answer step produced grounded output."
                if decision == CheckpointDecision.allow
                else "Answer step failed groundedness or returned an empty answer."
            )
            return CheckpointResult(
                decision=decision,
                reason=reason,
                metrics={
                    "groundedness": groundedness,
                    "answer_relevance": answer_relevance,
                    "citation_score": citation_score,
                    "completeness": completeness,
                },
            )

        if step_type == StepType.draft_email:
            body = str(output.get("body", ""))
            subject = str(output.get("subject", ""))
            decision = (
                CheckpointDecision.allow
                if body.strip() and subject.strip()
                else CheckpointDecision.abort
            )
            return CheckpointResult(
                decision=decision,
                reason=(
                    "Email draft generated successfully."
                    if decision == CheckpointDecision.allow
                    else "Email draft was empty."
                ),
                metrics={},
            )

        return CheckpointResult(
            decision=CheckpointDecision.abort,
            reason=f"Unsupported step type '{step_type}'.",
            metrics={},
        )
