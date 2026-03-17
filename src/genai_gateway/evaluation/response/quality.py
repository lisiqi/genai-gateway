"""Deterministic end-to-end response evaluation helpers."""

from __future__ import annotations

import re


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "with",
}


def _tokenize(text: str) -> set[str]:
    """Tokenize text into normalized content words."""
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def _clamp_score(value: float) -> float:
    """Clamp a heuristic score to the 0-5 range."""
    return round(max(0.0, min(5.0, value)), 2)


def score_answer_relevance(question: str, answer: str) -> float:
    """Estimate whether the answer addresses the user question."""
    question_tokens = _tokenize(question)
    answer_tokens = _tokenize(answer)
    if not question_tokens:
        return 0.0
    overlap = len(question_tokens & answer_tokens) / len(question_tokens)
    length_bonus = min(len(answer_tokens) / 40, 1.0)
    return _clamp_score((overlap * 4.0) + length_bonus)


def score_citation_presence(answer: str) -> float:
    """Estimate whether the answer cites supporting evidence."""
    patterns = [
        r"\barticle\s+\d+\b",
        r"\bchunk\s+\d+\b",
        r"\[\d+\]",
        r"\bclause\s+\d+\b",
    ]
    matches = sum(1 for pattern in patterns if re.search(pattern, answer, flags=re.IGNORECASE))
    return _clamp_score(matches * 1.5)


def score_completeness(answer: str, retrieved_chunks: list[dict]) -> float:
    """Estimate whether the answer is substantive relative to the available context."""
    if not answer.strip():
        return 0.0
    answer_tokens = _tokenize(answer)
    context_text = " ".join(str(chunk.get("content", "")) for chunk in retrieved_chunks)
    context_tokens = _tokenize(context_text)
    if not context_tokens:
        return _clamp_score(min(len(answer_tokens) / 20, 1.0) * 5.0)
    coverage = len(answer_tokens & context_tokens) / max(min(len(context_tokens), 30), 1)
    length_bonus = min(len(answer_tokens) / 50, 1.0)
    return _clamp_score((coverage * 4.0) + length_bonus)
