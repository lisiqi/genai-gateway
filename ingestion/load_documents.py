"""Document loading helpers."""

from pathlib import Path


def load_text_documents(root: str) -> list[dict]:
    """Load plain-text documents from a directory."""
    documents: list[dict] = []
    for path in sorted(Path(root).glob("*.txt")):
        documents.append({"source": str(path), "content": path.read_text(encoding="utf-8")})
    return documents
