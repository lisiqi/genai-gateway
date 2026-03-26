"""Lightweight runtime guardrails for scope and evidence checks."""

from __future__ import annotations

from dataclasses import dataclass
import re


ARTICLE_PATTERN = re.compile(r"\barticle\s+(\d+)\b", re.IGNORECASE)
CLAUSE_PATTERN = re.compile(r"\b(?:clause|paragraph)\s+(\d+)\b", re.IGNORECASE)


@dataclass(slots=True)
class ScopeDecision:
    """Decision for whether a request is in scope for a task."""

    status: str
    reason: str


@dataclass(slots=True)
class EvidenceDecision:
    """Decision for whether retrieved evidence is sufficient to answer."""

    status: str
    reason: str


LEGAL_QA_DOMAIN_TERMS = {
    "article",
    "clause",
    "paragraph",
    "regulation",
    "law",
    "legal",
    "digital services act",
    "dsa",
    "provider",
    "platform",
    "search engine",
    "commission",
    "coordinator",
    "coordinators",
    "board",
    "fine",
    "fines",
    "risk assessment",
    "notice",
    "hosting",
    "intermediary service",
    "trusted flagger",
    "statement of reasons",
    "terms and conditions",
    "illegal content",
}

LEGAL_QA_OFF_TOPIC_TERMS = {
    "weather",
    "temperature",
    "recipe",
    "restaurant",
    "flight",
    "hotel",
    "movie",
    "song",
    "lyrics",
    "python",
    "javascript",
    "debug",
    "algorithm",
    "sql query",
    "travel plan",
    "birthday",
}


def classify_request_scope(*, question: str, task: str) -> ScopeDecision:
    """Return whether a request is in scope for the selected task."""
    normalized = _normalize(question)
    if task != "legal_qa":
        return ScopeDecision(status="in_scope", reason="no task-specific scope policy configured")

    has_domain_signal = any(term in normalized for term in LEGAL_QA_DOMAIN_TERMS)
    has_off_topic_signal = any(term in normalized for term in LEGAL_QA_OFF_TOPIC_TERMS)
    mentions_article = ARTICLE_PATTERN.search(question) is not None

    if has_domain_signal or mentions_article:
        return ScopeDecision(status="in_scope", reason="question matches legal_qa domain cues")

    if has_off_topic_signal:
        return ScopeDecision(status="out_of_scope", reason="question matches off-topic cues for legal_qa")

    return ScopeDecision(
        status="out_of_scope",
        reason="question does not look grounded in the ingested legal corpus",
    )


def assess_retrieval_evidence(*, question: str, retrieved_chunks: list[dict]) -> EvidenceDecision:
    """Return whether the retrieved evidence is sufficient to continue."""
    if not retrieved_chunks:
        return EvidenceDecision(status="insufficient", reason="no chunks were retrieved")

    article_match = ARTICLE_PATTERN.search(question)
    if article_match is None:
        return EvidenceDecision(status="sufficient", reason="retrieval returned candidate evidence")

    expected_article = article_match.group(1)
    top_chunks = retrieved_chunks[:3]
    has_article_match = any(
        str((chunk.get("metadata") or {}).get("article_number")) == expected_article
        for chunk in top_chunks
    )
    if has_article_match:
        return EvidenceDecision(status="sufficient", reason="top retrieved chunks match the requested article")

    return EvidenceDecision(
        status="insufficient",
        reason=f"top retrieved chunks do not match requested article {expected_article}",
    )


def extract_requested_clause(question: str) -> str | None:
    """Extract one requested clause/paragraph number when present."""
    match = CLAUSE_PATTERN.search(question)
    return match.group(1) if match else None


def _normalize(value: str) -> str:
    """Normalize free text for keyword checks."""
    return " ".join(value.lower().split())
