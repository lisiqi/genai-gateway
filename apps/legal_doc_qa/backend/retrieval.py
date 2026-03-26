"""Application-specific retrieval helpers for legal_doc_qa."""

from __future__ import annotations

import re

from genai_gateway.retrieval.query_builders import DefaultLexicalQueryBuilder, LexicalQuery


QUESTION_BOILERPLATE_PATTERNS = [
    r"\bwhat is\b",
    r"\bwhat are\b",
    r"\bwhat does\b",
    r"\bhow does\b",
    r"\bwho is\b",
    r"\bwho are\b",
    r"\bwhen does\b",
    r"\baccording to\b",
    r"\bunder\b",
]
QUESTION_STOPWORDS = {
    "a",
    "an",
    "and",
    "article",
    "act",
    "by",
    "clause",
    "digital",
    "does",
    "how",
    "is",
    "of",
    "paragraph",
    "regulation",
    "services",
    "the",
    "this",
    "to",
    "what",
    "who",
}


class LegalDocQALexicalQueryBuilder(DefaultLexicalQueryBuilder):
    """Legal-question-specific lexical query builder."""

    def build(self, question: str) -> LexicalQuery:
        """Normalize a legal QA question into a relaxed lexical query."""
        article_match = re.search(r"\barticle\s+(\d+)\b", question, flags=re.IGNORECASE)
        clause_match = re.search(r"\b(?:clause|paragraph)\s+(\d+)\b", question, flags=re.IGNORECASE)

        normalized = question.lower()
        for pattern in QUESTION_BOILERPLATE_PATTERNS:
            normalized = re.sub(pattern, " ", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bdigital services act\b", " ", normalized)
        normalized = re.sub(r"\bthis regulation\b", " ", normalized)
        normalized = re.sub(r"\barticle\s+\d+\b", " ", normalized)
        normalized = re.sub(r"\b(?:clause|paragraph)\s+\d+\b", " ", normalized)
        normalized = normalized.replace("'", " ")
        normalized = re.sub(r"[^a-z0-9\s-]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        terms: list[str] = []
        seen: set[str] = set()
        for token in normalized.split():
            token = token.strip("-")
            if not token or token in QUESTION_STOPWORDS or token.isdigit() or token in seen:
                continue
            seen.add(token)
            terms.append(token)

        return LexicalQuery(
            tsquery_text=" | ".join(terms) if terms else None,
            article_number=article_match.group(1) if article_match else None,
            clause_number=clause_match.group(1) if clause_match else None,
        )
