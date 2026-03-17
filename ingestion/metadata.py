"""Metadata extraction helpers for legal-style documents."""

from __future__ import annotations

import re


ARTICLE_REFERENCE_RE = re.compile(r"\bArticles?\s+(\d+[A-Za-z]?)\b", re.IGNORECASE)
CLAUSE_OF_ARTICLE_RE = re.compile(
    r"\b(?:clause|paragraph)\s+(\d+)\s+of\s+Articles?\s+(\d+[A-Za-z]?)\b",
    re.IGNORECASE,
)
THIS_ARTICLE_CLAUSE_RE = re.compile(
    r"\b(?:clause|paragraph)\s+(\d+)\s+of\s+(?:this|the)\s+Article\b",
    re.IGNORECASE,
)


def build_hierarchy_labels(*, article_number: str, article_title: str, clause_numbers: list[int]) -> list[str]:
    """Build simple hierarchy labels that can be shown in retrieval demos."""
    labels = [f"article:{article_number}"]
    if article_title:
        labels.append(f"article_title:{article_title}")
    labels.extend(f"clause:{number}" for number in clause_numbers)
    return labels


def extract_cross_references(
    text: str,
    *,
    current_article_number: str,
    current_clause_numbers: list[int] | None = None,
) -> list[dict[str, str | int | None]]:
    """Extract same-document article and clause cross-references deterministically."""
    references: list[dict[str, str | int | None]] = []
    seen: set[tuple[str, int | None]] = set()

    for match in CLAUSE_OF_ARTICLE_RE.finditer(text):
        clause_number = int(match.group(1))
        article_number = match.group(2)
        key = (article_number, clause_number)
        if article_number == current_article_number and current_clause_numbers and clause_number in current_clause_numbers:
            continue
        if key in seen:
            continue
        seen.add(key)
        references.append(
            {
                "article_number": article_number,
                "clause_number": clause_number,
                "scope": "same_document",
            }
        )

    for match in ARTICLE_REFERENCE_RE.finditer(text):
        article_number = match.group(1)
        key = (article_number, None)
        if article_number == current_article_number:
            continue
        if key in seen:
            continue
        seen.add(key)
        references.append(
            {
                "article_number": article_number,
                "clause_number": None,
                "scope": "same_document",
            }
        )

    for match in THIS_ARTICLE_CLAUSE_RE.finditer(text):
        clause_number = int(match.group(1))
        key = (current_article_number, clause_number)
        if current_clause_numbers and clause_number in current_clause_numbers:
            continue
        if key in seen:
            continue
        seen.add(key)
        references.append(
            {
                "article_number": current_article_number,
                "clause_number": clause_number,
                "scope": "same_article",
            }
        )

    return references
