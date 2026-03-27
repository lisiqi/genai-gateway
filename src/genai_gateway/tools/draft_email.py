"""Draft a follow-up email from the generated answer."""

from __future__ import annotations

from typing import Any

from genai_gateway.runtime.agent.state import AgentExecutionState
from genai_gateway.tools.base import AgentCapability


class DraftEmailCapability(AgentCapability):
    """Capability for deterministic follow-up email drafting."""

    name = "draft_email"

    def execute(self, *, inputs: dict[str, Any], state: AgentExecutionState) -> dict[str, Any]:
        """Draft a concise email around the grounded answer."""
        question = str(inputs["question"])
        recipient_email = inputs.get("recipient_email")
        answer = (state.answer or "").strip()
        subject = f"Legal QA summary: {question[:60]}".strip()
        greeting = f"Hi {recipient_email}," if recipient_email else "Hello,"
        body = (
            f"{greeting}\n\n"
            "Here is the requested summary based on the legal document corpus:\n\n"
            f"{answer or 'No answer was generated.'}\n\n"
            "Best regards,\n"
            "GenAI Gateway"
        )
        draft = {
            "recipient_email": recipient_email,
            "subject": subject,
            "body": body,
        }
        state.email_draft = draft
        return draft
