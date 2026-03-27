"""Capability execution for controlled runtime plans."""

from __future__ import annotations

from typing import Any

from genai_gateway.runtime.agent.state import AgentExecutionState
from genai_gateway.tools import AnswerQuestionCapability, DraftEmailCapability, RetrieveContextCapability


class ToolExecutor:
    """Dispatch plan steps to typed capabilities."""

    def __init__(self) -> None:
        self.capabilities: dict[str, Any] = {
            "retrieve_context": RetrieveContextCapability(),
            "answer_question": AnswerQuestionCapability(),
            "draft_email": DraftEmailCapability(),
        }

    def execute(self, *, capability_name: str, inputs: dict[str, Any], state: AgentExecutionState) -> dict[str, Any]:
        """Run the selected capability."""
        capability = self.capabilities.get(capability_name)
        if capability is None:
            raise ValueError(f"Unknown capability '{capability_name}'.")
        return capability.execute(inputs=inputs, state=state)
