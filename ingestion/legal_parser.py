"""Structural parsing utilities for legal-style documents."""

from __future__ import annotations

from dataclasses import dataclass, field
import re


ARTICLE_HEADING_RE = re.compile(r"^Article\s+(\d+[A-Za-z]?)\s*$", re.MULTILINE)
CLAUSE_RE = re.compile(r"^\s*(\d+)\.\s", re.MULTILINE)
NON_MERGE_TITLE_TOKENS = {
    "a",
    "an",
    "and",
    "by",
    "for",
    "in",
    "no",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


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


def repair_fragmented_heading_text(text: str) -> str:
    """Repair common PDF extraction word splits in short heading/title text."""
    tokens = _split_glued_title_stopword_prefixes(text.split())
    if len(tokens) < 2:
        return text.strip()

    repaired = _merge_fragmented_title_tokens(tokens)
    return " ".join(repaired).strip()


def _merge_fragmented_title_tokens(tokens: list[str]) -> list[str]:
    """Apply conservative title-token repair rules in a single left-to-right pass."""
    merged: list[str] = []
    index = 0
    while index < len(tokens):
        if index + 2 < len(tokens):
            merged_triplet = _try_merge_title_triplet(tokens[index], tokens[index + 1], tokens[index + 2])
            if merged_triplet is not None:
                merged.append(merged_triplet)
                index += 3
                continue

        current = tokens[index]
        if index == len(tokens) - 1:
            merged.append(current)
            break

        following = tokens[index + 1]
        current_clean = re.sub(r"^[^A-Za-z]+|[^A-Za-z-]+$", "", current)
        following_clean = re.sub(r"^[^A-Za-z]+|[^A-Za-z-]+$", "", following)

        should_merge = False
        if current_clean and following_clean:
            current_lower = current_clean.lower()
            if current_lower not in NON_MERGE_TITLE_TOKENS:
                if len(current_clean) == 1 and current_clean[:1].isupper() and following_clean[:1].islower():
                    should_merge = True
                elif len(following_clean) == 1 and following_clean.lower() not in NON_MERGE_TITLE_TOKENS and current_clean[-1:].isalpha():
                    should_merge = True
                elif 2 <= len(current_clean) <= 3 and len(following_clean) >= 4 and following_clean[:1].islower():
                    should_merge = True
                elif "-" in current_clean and re.search(r"-[A-Za-z]$", current_clean) and len(following_clean) >= 4:
                    should_merge = True

        if should_merge:
            merged.append(f"{current}{following}")
            index += 2
            continue

        merged.append(current)
        index += 1

    return merged


def _try_merge_title_triplet(first: str, second: str, third: str) -> str | None:
    """Repair title-specific three-token word fragments."""
    first_clean = re.sub(r"^[^A-Za-z]+|[^A-Za-z-]+$", "", first)
    second_clean = re.sub(r"^[^A-Za-z]+|[^A-Za-z-]+$", "", second)
    third_clean = re.sub(r"^[^A-Za-z]+|[^A-Za-z-]+$", "", third)
    if not first_clean or not second_clean or not third_clean:
        return None
    if len(first_clean) >= 4 and len(second_clean) == 1 and len(third_clean) == 1:
        return f"{first}{second}{third}"
    return None


def _split_glued_title_stopword_prefixes(tokens: list[str]) -> list[str]:
    """Split tokens like 'Nogeneral' into 'No', 'general' for title lines."""
    split_tokens: list[str] = []
    for token in tokens:
        matched = False
        for prefix in ("No", "For", "In", "On", "Of", "The"):
            if token.startswith(prefix) and len(token) > len(prefix) + 2 and token[len(prefix)].islower():
                split_tokens.extend([prefix, token[len(prefix):]])
                matched = True
                break
        if not matched:
            split_tokens.append(token)
    return split_tokens


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
            title = repair_fragmented_heading_text(body_lines[0])
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
