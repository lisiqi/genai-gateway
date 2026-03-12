"""Minimal retrieval orchestration for the gateway MVP."""

from app.config.settings import get_settings


class RetrievalService:
    """Placeholder retrieval layer.

    The first milestone keeps retrieval explicit and simple. We can later swap
    this to pgvector-backed search or port selected logic from `rf-genai`.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def retrieve(self, question: str, task: str, top_k: int | None = None) -> list[dict]:
        """Return placeholder chunks for the configured task."""
        k = top_k or self.settings.retrieval_top_k
        return [
            {
                "chunk_id": f"{task}-seed-1",
                "source": "seed/legal_overview.txt",
                "content": (
                    "This is a placeholder retrieval result. Replace this service "
                    "with pgvector-backed retrieval during the next implementation step."
                ),
                "score": 1.0,
            }
        ][:k]
