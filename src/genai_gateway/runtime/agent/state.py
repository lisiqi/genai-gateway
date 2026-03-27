"""Short-term execution state for the controlled agent runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from genai_gateway.runtime.agent.schemas import AgentTaskRequest


@dataclass(slots=True)
class AgentExecutionState:
    """Mutable state carried across plan steps."""

    request: AgentTaskRequest
    retrieved_chunks: list[dict[str, Any]] = field(default_factory=list)
    answer: str | None = None
    answer_metadata: dict[str, Any] = field(default_factory=dict)
    email_draft: dict[str, Any] = field(default_factory=dict)

    @property
    def task(self) -> str:
        """Expose the logical task name."""
        return self.request.task
