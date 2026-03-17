"""Document loading helpers."""

from __future__ import annotations

from pathlib import Path
import re

from pypdf import PdfReader


FRAGMENT_STOPWORDS = {
    "a",
    "an",
    "are",
    "as",
    "at",
    "be",
    "by",
    "do",
    "for",
    "he",
    "if",
    "in",
    "is",
    "and",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "those",
    "these",
    "to",
    "us",
    "was",
    "we",
    "were",
    "when",
    "with",
}


def load_text_documents(root: str) -> list[dict]:
    """Load plain-text documents from a directory."""
    documents: list[dict] = []
    for path in sorted(Path(root).glob("*.txt")):
        documents.append({"source": str(path), "content": path.read_text(encoding="utf-8")})
    return documents


def normalize_extracted_pdf_text(text: str) -> str:
    """Repair common PDF extraction artifacts before structural parsing."""
    normalized = text.replace("\r\n", "\n")
    return "\n".join(_normalize_pdf_line(line) for line in normalized.splitlines())


def _normalize_pdf_line(line: str) -> str:
    tokens = line.split()
    if not tokens:
        return ""

    normalized: list[str] = []
    index = 0
    while index < len(tokens):
        if index + 2 < len(tokens):
            merged_triplet = _try_merge_triplet(tokens[index], tokens[index + 1], tokens[index + 2])
            if merged_triplet is not None:
                normalized.append(merged_triplet)
                index += 3
                continue

        if index + 1 < len(tokens):
            merged_pair = _try_merge_pair(tokens[index], tokens[index + 1])
            if merged_pair is not None:
                normalized.append(merged_pair)
                index += 2
                continue

        normalized.append(tokens[index])
        index += 1

    return " ".join(normalized)


def _try_merge_triplet(first: str, second: str, third: str) -> str | None:
    first_clean = _clean_alpha_token(first)
    second_clean = _clean_alpha_token(second)
    third_clean = _clean_alpha_token(third)
    if not first_clean or not second_clean or not third_clean:
        return None
    if first_clean.lower() in FRAGMENT_STOPWORDS:
        return None

    if (
        2 <= len(first_clean) <= 4
        and len(second_clean) <= 2
        and len(third_clean) >= 4
        and (second_clean.lower() not in FRAGMENT_STOPWORDS or second_clean.lower() == "or")
    ):
        return f"{first}{second}{third}"
    if len(first_clean) >= 4 and len(second_clean) >= 4 and len(third_clean) <= 2 and third_clean.lower() not in FRAGMENT_STOPWORDS:
        return f"{first}{second}{third}"
    return None


def _try_merge_pair(first: str, second: str) -> str | None:
    first_clean = _clean_alpha_token(first)
    second_clean = _clean_alpha_token(second)
    if not first_clean or not second_clean:
        return None
    if first_clean.lower() in FRAGMENT_STOPWORDS or second_clean.lower() in FRAGMENT_STOPWORDS:
        return None

    if first_clean.endswith("-"):
        return f"{first}{second}"
    if len(first_clean) == 1 and len(second_clean) >= 4:
        return f"{first}{second}"
    if len(first_clean) <= 3 and len(second_clean) >= 4:
        return f"{first}{second}"
    if len(first_clean) >= 4 and len(second_clean) <= 2:
        return f"{first}{second}"
    return None


def _clean_alpha_token(token: str) -> str:
    return re.sub(r"^[^A-Za-z]+|[^A-Za-z-]+$", "", token)


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
        "content": normalize_extracted_pdf_text("\n\n".join(page_texts)),
        "page_count": len(reader.pages),
    }
