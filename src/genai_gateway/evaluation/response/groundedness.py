"""Groundedness scoring for generated answers."""


def score_groundedness(answer: str, retrieved_chunks: list[dict]) -> float:
    """Return a simple heuristic groundedness score.

    This is intentionally lightweight for the scaffold. We can replace it with
    an LLM-as-a-judge implementation once the core request pipeline is stable.
    """
    if not retrieved_chunks:
        return 1.0 if not answer else 0.0
    return 3.0 if answer else 1.0
