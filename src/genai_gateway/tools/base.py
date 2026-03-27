"""Base interface for typed runtime capabilities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from genai_gateway.runtime.agent.state import AgentExecutionState


class AgentCapability(ABC):
    """Executable capability contract for one plan step."""

    name: str

    @abstractmethod
    def execute(self, *, inputs: dict[str, Any], state: AgentExecutionState) -> dict[str, Any]:
        """Execute one typed capability and return a serializable output."""
