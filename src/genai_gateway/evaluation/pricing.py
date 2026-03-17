"""Model-aware pricing registry for request cost accounting."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PricingCard:
    """Per-model price card in USD per 1M tokens."""

    provider: str
    model: str
    input_per_million_tokens_usd: float
    output_per_million_tokens_usd: float
    source: str
    is_estimated: bool = False


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    """Computed request cost breakdown."""

    total_cost_usd: float
    input_cost_usd: float
    output_cost_usd: float
    pricing_source: str
    is_estimated: bool


PRICING_CARDS: dict[tuple[str, str], PricingCard] = {
    (
        "openai",
        "gpt-4.1-mini",
    ): PricingCard(
        provider="openai",
        model="gpt-4.1-mini",
        input_per_million_tokens_usd=0.80,
        output_per_million_tokens_usd=3.20,
        source="OpenAI pricing (gpt-4.1-mini)",
    ),
    (
        "openai",
        "gpt-4.1",
    ): PricingCard(
        provider="openai",
        model="gpt-4.1",
        input_per_million_tokens_usd=3.00,
        output_per_million_tokens_usd=12.00,
        source="OpenAI pricing (gpt-4.1)",
    ),
    (
        "openai",
        "text-embedding-3-small",
    ): PricingCard(
        provider="openai",
        model="text-embedding-3-small",
        input_per_million_tokens_usd=0.02,
        output_per_million_tokens_usd=0.00,
        source="OpenAI pricing (text-embedding-3-small)",
    ),
    (
        "openrouter",
        "openai/gpt-4.1-mini",
    ): PricingCard(
        provider="openrouter",
        model="openai/gpt-4.1-mini",
        input_per_million_tokens_usd=0.80,
        output_per_million_tokens_usd=3.20,
        source="OpenRouter passthrough pricing using OpenAI gpt-4.1-mini rates",
        is_estimated=True,
    ),
    (
        "openrouter",
        "openai/gpt-4.1",
    ): PricingCard(
        provider="openrouter",
        model="openai/gpt-4.1",
        input_per_million_tokens_usd=3.00,
        output_per_million_tokens_usd=12.00,
        source="OpenRouter passthrough pricing using OpenAI gpt-4.1 rates",
        is_estimated=True,
    ),
}


def compute_request_cost(
    *,
    provider: str,
    model: str | None,
    prompt_tokens: int,
    completion_tokens: int,
) -> CostBreakdown:
    """Compute request cost using the configured model price card."""
    if not model:
        return CostBreakdown(
            total_cost_usd=0.0,
            input_cost_usd=0.0,
            output_cost_usd=0.0,
            pricing_source="No model selected",
            is_estimated=True,
        )

    card = PRICING_CARDS.get((provider, model))
    if card is None:
        return CostBreakdown(
            total_cost_usd=0.0,
            input_cost_usd=0.0,
            output_cost_usd=0.0,
            pricing_source=f"Unknown price card for {provider}/{model}",
            is_estimated=True,
        )

    input_cost = (prompt_tokens / 1_000_000) * card.input_per_million_tokens_usd
    output_cost = (completion_tokens / 1_000_000) * card.output_per_million_tokens_usd
    total_cost = input_cost + output_cost
    return CostBreakdown(
        total_cost_usd=round(total_cost, 6),
        input_cost_usd=round(input_cost, 6),
        output_cost_usd=round(output_cost, 6),
        pricing_source=card.source,
        is_estimated=card.is_estimated,
    )
