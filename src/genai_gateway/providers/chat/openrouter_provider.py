"""OpenRouter-backed chat provider."""

from openai import OpenAI

from genai_gateway.config.settings import get_settings
from genai_gateway.providers.chat.base import ChatProvider
from genai_gateway.schemas.response_schema import ProviderGenerationMetadata, TokenUsage


class OpenRouterChatProvider(ChatProvider):
    """Call OpenRouter through its OpenAI-compatible chat completions API."""

    def __init__(self, model_name: str | None = None) -> None:
        self.settings = get_settings()
        self._model_name = model_name or self.settings.openrouter_model
        headers: dict[str, str] = {}
        if self.settings.openrouter_http_referer:
            headers["HTTP-Referer"] = self.settings.openrouter_http_referer
        if self.settings.openrouter_title:
            headers["X-Title"] = self.settings.openrouter_title
        self.client = (
            OpenAI(
                api_key=self.settings.openrouter_api_key,
                base_url=self.settings.openrouter_base_url,
                default_headers=headers or None,
            )
            if self.settings.openrouter_api_key
            else None
        )

    @property
    def model_name(self) -> str | None:
        """Return the configured OpenRouter model name."""
        return self._model_name or None

    def generate(self, prompt: str, question: str) -> tuple[str, TokenUsage, ProviderGenerationMetadata]:
        """Generate an answer through OpenRouter.

        Falls back to a deterministic stub when no API key is configured so the
        runtime stays locally runnable.
        """
        if self.client is None:
            answer = (
                "OpenRouter chat provider is not configured yet. "
                f"Question received: {question}"
            )
            return (
                answer,
                TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                ProviderGenerationMetadata(provider_usage_source="local stub"),
            )

        response = self.client.chat.completions.create(
            model=self._model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        choice = response.choices[0] if response.choices else None
        message = choice.message if choice is not None else None
        answer = (message.content if message else None) or "No response returned."
        usage = getattr(response, "usage", None)
        usage_cost = getattr(usage, "cost", None)
        if usage_cost is None:
            usage_cost = getattr(usage, "total_cost", None)
        return (
            answer,
            TokenUsage(
                prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                total_tokens=getattr(usage, "total_tokens", 0) or 0,
            ),
            ProviderGenerationMetadata(
                provider_reported_cost_usd=float(usage_cost) if usage_cost is not None else None,
                provider_generation_id=getattr(response, "id", None),
                provider_usage_source="OpenRouter chat completions usage",
            ),
        )
