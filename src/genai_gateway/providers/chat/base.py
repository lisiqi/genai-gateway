"""Base interface for chat model providers."""

from abc import ABC, abstractmethod

from genai_gateway.schemas.response_schema import ProviderGenerationMetadata, TokenUsage


class ChatProvider(ABC):
    """Common interface for runtime chat backends."""

    @property
    @abstractmethod
    def model_name(self) -> str | None:
        """Return the configured model name for logging."""

    @abstractmethod
    def generate(self, prompt: str, question: str) -> tuple[str, TokenUsage, ProviderGenerationMetadata]:
        """Generate a response from the provider."""
