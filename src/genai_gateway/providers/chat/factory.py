"""Factory for selecting the active chat provider."""

from genai_gateway.providers.chat.base import ChatProvider
from genai_gateway.providers.chat.openai_provider import OpenAIChatProvider
from genai_gateway.providers.chat.openrouter_provider import OpenRouterChatProvider


def get_chat_provider(*, provider_name: str, model_name: str | None = None) -> ChatProvider:
    """Return the selected chat provider implementation."""
    provider_name = provider_name.strip().lower()
    if provider_name == "openai":
        return OpenAIChatProvider(model_name=model_name)
    if provider_name == "openrouter":
        return OpenRouterChatProvider(model_name=model_name)
    raise ValueError(
        f"Unsupported chat provider '{provider_name}'. "
        "Expected one of: openai, openrouter."
    )
