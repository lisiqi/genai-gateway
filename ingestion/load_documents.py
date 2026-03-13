"""Document loading helpers."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

def load_text_documents(root: str) -> list[dict]:
    """Load plain-text documents from a directory."""
    documents: list[dict] = []
    for path in sorted(Path(root).glob("*.txt")):
        documents.append({"source": str(path), "content": path.read_text(encoding="utf-8")})
    return documents


def load_pdf_document(path: str) -> dict:
    """Extract text from a PDF file."""
    pdf_path = Path(path)
    reader = PdfReader(str(pdf_path))
    page_texts: list[str] = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        cleaned = extracted.strip()
        if cleaned:
            page_texts.append(cleaned)

    return {
        "source": str(pdf_path),
        "title": pdf_path.stem,
        "content": "\n\n".join(page_texts),
        "page_count": len(reader.pages),
    }
