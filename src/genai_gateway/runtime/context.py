"""Typed runtime context objects."""

from dataclasses import dataclass


@dataclass(slots=True)
class RuntimeContext:
    """Carries execution metadata through a workflow run."""

    task: str
    quality_mode: str
    prompt_version: str
    retrieval_mode: str | None = None
    top_k: int | None = None
    reranker_type: str | None = None
