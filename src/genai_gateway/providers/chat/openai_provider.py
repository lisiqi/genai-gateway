"""OpenAI-backed chat provider."""

from openai import OpenAI

from genai_gateway.config.settings import get_settings
from genai_gateway.providers.chat.base import ChatProvider
from genai_gateway.schemas.response_schema import TokenUsage


class OpenAIChatProvider(ChatProvider):
    """Wrap model invocation behind the runtime's chat provider interface."""

    def __init__(self, model_name: str | None = None) -> None:
        self.settings = get_settings()
        self._model_name = model_name or self.settings.openai_model
        self.client = OpenAI(api_key=self.settings.openai_api_key) if self.settings.openai_api_key else None

    @property
    def model_name(self) -> str | None:
        """Return the configured model for this provider."""
        return self._model_name or None

    def generate(self, prompt: str, question: str) -> tuple[str, TokenUsage]:
        """Generate an answer and token usage information.

        Falls back to a deterministic stub when no API key is configured so the
        scaffold stays runnable from day one.
        """
        if self.client is None:
            answer = (
                "Model client is not configured yet. "
                f"Question received: {question}"
            )
            return answer, TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)

        response = self.client.responses.create(
            model=self._model_name,
            input=prompt,
        )
        usage = getattr(response, "usage", None)
        answer = response.output_text or "No response returned."
        return answer, TokenUsage(
            prompt_tokens=getattr(usage, "input_tokens", 0) or 0,
            completion_tokens=getattr(usage, "output_tokens", 0) or 0,
            total_tokens=getattr(usage, "total_tokens", 0) or 0,
        )
