"""Unit tests for provider-reported metadata extraction."""

from __future__ import annotations

from types import SimpleNamespace

from genai_gateway.providers.chat.openrouter_provider import OpenRouterChatProvider


def test_openrouter_provider_returns_provider_reported_cost(monkeypatch) -> None:
    provider = OpenRouterChatProvider(model_name="test-model")
    provider.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(
                    id="gen_123",
                    choices=[SimpleNamespace(message=SimpleNamespace(content="hello"))],
                    usage=SimpleNamespace(
                        prompt_tokens=10,
                        completion_tokens=4,
                        total_tokens=14,
                        cost=0.0123,
                    ),
                )
            )
        )
    )

    answer, usage, metadata = provider.generate(prompt="p", question="q")

    assert answer == "hello"
    assert usage.total_tokens == 14
    assert metadata.provider_reported_cost_usd == 0.0123
    assert metadata.provider_generation_id == "gen_123"
    assert metadata.provider_usage_source == "OpenRouter chat completions usage"
