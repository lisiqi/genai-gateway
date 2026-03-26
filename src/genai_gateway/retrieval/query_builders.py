"""Lexical query builder abstractions for retrieval."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol


@dataclass(slots=True)
class LexicalQuery:
    """Normalized lexical query derived from a natural-language question."""

    tsquery_text: str | None
    article_number: str | None = None
    clause_number: str | None = None


class LexicalQueryBuilder(Protocol):
    """Build a lexical retrieval query from a natural-language question."""

    def build(self, question: str) -> LexicalQuery:
        """Return a normalized lexical query."""


class DefaultLexicalQueryBuilder:
    """Generic lexical query builder with light normalization only."""

    STOPWORDS = {
        "a",
        "an",
        "and",
        "are",
        "article",
        "by",
        "clause",
        "does",
        "how",
        "is",
        "of",
        "paragraph",
        "the",
        "to",
        "what",
        "when",
        "who",
    }

    def build(self, question: str) -> LexicalQuery:
        """Normalize a question into a generic lexical query."""
        article_match = re.search(r"\barticle\s+(\d+)\b", question, flags=re.IGNORECASE)
        clause_match = re.search(r"\b(?:clause|paragraph)\s+(\d+)\b", question, flags=re.IGNORECASE)

        normalized = question.lower()
        normalized = re.sub(r"\barticle\s+\d+\b", " ", normalized)
        normalized = re.sub(r"\b(?:clause|paragraph)\s+\d+\b", " ", normalized)
        normalized = normalized.replace("'", " ")
        normalized = re.sub(r"[^a-z0-9\s-]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        terms: list[str] = []
        seen: set[str] = set()
        for token in normalized.split():
            token = token.strip("-")
            if not token or token in self.STOPWORDS or token.isdigit() or token in seen:
                continue
            seen.add(token)
            terms.append(token)

        return LexicalQuery(
            tsquery_text=" | ".join(terms) if terms else None,
            article_number=article_match.group(1) if article_match else None,
            clause_number=clause_match.group(1) if clause_match else None,
        )
