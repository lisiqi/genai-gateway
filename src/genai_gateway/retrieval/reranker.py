"""Reranking interfaces for retrieval results."""


class PassThroughReranker:
    """Default reranker that preserves retrieval order."""

    def rerank(self, question: str, chunks: list[dict]) -> list[dict]:
        """Return chunks unchanged until a real reranker is implemented."""
        return chunks
