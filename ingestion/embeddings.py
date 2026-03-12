"""Embedding helpers."""


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return deterministic placeholder embeddings for local development."""
    return [[float(len(text))] for text in texts]
