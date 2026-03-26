"""Structural parsing utilities for legal-style documents."""

from __future__ import annotations

from dataclasses import dataclass, field
import re


ARTICLE_HEADING_RE = re.compile(r"^Article\s+(\d+[A-Za-z]?)\s*$", re.MULTILINE)
CLAUSE_RE = re.compile(r"^\s*(\d+)\.\s", re.MULTILINE)


@dataclass(slots=True)
class LegalClause:
    """One numbered clause inside an article."""

    number: int
    text: str


@dataclass(slots=True)
class LegalArticle:
    """One parsed article with optional title and clause structure."""

    number: str
    heading: str
    title: str
    body_text: str
    clauses: list[LegalClause] = field(default_factory=list)


@dataclass(slots=True)
class LegalDocumentStructure:
    """Parsed structural representation of a legal-style document."""

    normalized_text: str
    articles: list[LegalArticle] = field(default_factory=list)


def normalize_legal_text(text: str) -> str:
    """Normalize a subset of PDF extraction artifacts relevant to legal structure."""
    normalized = text.replace("\r\n", "\n")
    normalized = re.sub(r"\bAr\s*ticle\b", "Article", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bCHAP\s*TER\b", "CHAPTER", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bSEC\s*TION\b", "SECTION", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bTIT\s*LE\b", "TITLE", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    return normalized

def parse_legal_structure(text: str) -> LegalDocumentStructure:
    """Parse article and clause structure from a legal-style document."""
    normalized = normalize_legal_text(text)
    article_matches = list(ARTICLE_HEADING_RE.finditer(normalized))
    if not article_matches:
        return LegalDocumentStructure(normalized_text=normalized)

    articles: list[LegalArticle] = []
    for index, match in enumerate(article_matches):
        start = match.start()
        end = article_matches[index + 1].start() if index + 1 < len(article_matches) else len(normalized)
        article_block = normalized[start:end].strip()
        if not article_block:
            continue

        article_lines = [line.strip() for line in article_block.splitlines() if line.strip()]
        if not article_lines:
            continue

        heading = article_lines[0]
        title = ""
        body_lines = article_lines[1:]
        if body_lines and not CLAUSE_RE.match(body_lines[0]):
            title = body_lines[0].strip()
            body_lines = body_lines[1:]

        body_text = "\n".join(body_lines).strip()
        if not body_text:
            continue

        clauses: list[LegalClause] = []
        clause_matches = list(CLAUSE_RE.finditer(body_text))
        for clause_position, clause_match in enumerate(clause_matches):
            clause_start = clause_match.start()
            clause_end = clause_matches[clause_position + 1].start() if clause_position + 1 < len(clause_matches) else len(body_text)
            clause_text = body_text[clause_start:clause_end].strip()
            if not clause_text:
                continue
            clauses.append(
                LegalClause(
                    number=int(clause_match.group(1)),
                    text=clause_text,
                )
            )

        articles.append(
            LegalArticle(
                number=match.group(1),
                heading=heading,
                title=title,
                body_text=body_text,
                clauses=clauses,
            )
        )

    return LegalDocumentStructure(
        normalized_text=normalized,
        articles=articles,
    )
