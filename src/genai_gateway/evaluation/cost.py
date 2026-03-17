"""Token cost estimation helpers."""


def estimate_token_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate request cost in USD.

    Placeholder pricing for local development. Replace this with model-specific
    pricing tables once routing is introduced.
    """
    prompt_cost = prompt_tokens * 0.0000004
    completion_cost = completion_tokens * 0.0000016
    return round(prompt_cost + completion_cost, 6)
