"""Schemas for the controlled agent runtime."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from genai_gateway.config.settings import get_settings


settings = get_settings()


class AgentTaskType(str, Enum):
    """Supported controlled-runtime task types."""

    answer_and_draft_email = "answer_and_draft_email"


class StepType(str, Enum):
    """Supported step types in a compiled execution plan."""

    retrieve_context = "retrieve_context"
    answer_question = "answer_question"
    draft_email = "draft_email"


class RunStatus(str, Enum):
    """Status for one controlled-runtime execution."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    aborted = "aborted"


class StepStatus(str, Enum):
    """Status for one plan step."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"
    aborted = "aborted"


class CheckpointDecision(str, Enum):
    """Post-step checkpoint outcome."""

    allow = "allow"
    retry = "retry"
    abort = "abort"


class AgentTaskRequest(BaseModel):
    """Request for one controlled multi-step workflow execution."""

    task_type: AgentTaskType = Field(default=AgentTaskType.answer_and_draft_email)
    instruction: str = Field(min_length=1, description="Natural-language task instruction.")
    question: str = Field(min_length=1, description="Primary question to answer.")
    task: str = Field(default=settings.default_task, description="Logical corpus task name.")
    recipient_email: str | None = Field(default=None, description="Optional target recipient for the email draft.")
    quality_mode: str = Field(default="default")
    prompt_version: str = Field(default=settings.default_prompt_version)
    retrieval_mode: str | None = Field(default=None)
    top_k: int | None = Field(default=None, ge=1, le=20)
    reranker_type: str | None = Field(default=None)


class PlanStep(BaseModel):
    """One typed step in the compiled execution plan."""

    step_id: str
    step_type: StepType
    title: str
    capability_name: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)


class CheckpointResult(BaseModel):
    """Checkpoint decision and metrics for a completed step."""

    decision: CheckpointDecision
    reason: str
    metrics: dict[str, float] = Field(default_factory=dict)


class StepResult(BaseModel):
    """Execution result for one plan step."""

    step_id: str
    step_type: StepType
    title: str
    capability_name: str
    status: StepStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    latency_ms: float | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    checkpoint: CheckpointResult | None = None
    error: str | None = None


class AgentExecutionReport(BaseModel):
    """Top-level execution report for a controlled runtime run."""

    run_id: str
    task_type: AgentTaskType
    status: RunStatus
    created_at: datetime
    completed_at: datetime | None = None
    request: AgentTaskRequest
    plan: list[PlanStep] = Field(default_factory=list)
    steps: list[StepResult] = Field(default_factory=list)
    final_output: dict[str, Any] = Field(default_factory=dict)
    stop_reason: str | None = None
