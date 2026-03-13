"""Chunking utilities."""

from __future__ import annotations

import re


ARTICLE_HEADING_RE = re.compile(r"^Article\s+(\d+[A-Za-z]?)\s*$", re.MULTILINE)
CLAUSE_RE = re.compile(r"^\s*(\d+)\.\s", re.MULTILINE)


def normalize_legal_text(text: str) -> str:
    """Normalize a subset of PDF extraction artifacts relevant to legal structure."""
    normalized = text.replace("\r\n", "\n")
    normalized = re.sub(r"\bAr\s*ticle\b", "Article", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bCHAP\s*TER\b", "CHAPTER", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bSEC\s*TION\b", "SECTION", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bTIT\s*LE\b", "TITLE", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    return normalized


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping character chunks."""
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def build_chunk_records(text: str, chunk_size: int = 800, overlap: int = 100) -> list[dict]:
    """Split text and return structured chunk records."""
    return [
        {
            "chunk_index": index,
            "content": chunk,
            "token_count": len(chunk.split()),
            "metadata_json": {},
        }
        for index, chunk in enumerate(chunk_text(text, chunk_size=chunk_size, overlap=overlap))
    ]


def build_legal_chunk_records(text: str, chunk_size: int = 1800, overlap: int = 200) -> list[dict]:
    """Build article-aware, clause-oriented chunk records for legal documents."""
    normalized = normalize_legal_text(text)
    article_matches = list(ARTICLE_HEADING_RE.finditer(normalized))
    if not article_matches:
        return build_chunk_records(normalized, chunk_size=chunk_size, overlap=overlap)

    chunk_records: list[dict] = []
    chunk_index = 0

    for index, match in enumerate(article_matches):
        article_number = match.group(1)
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
            title = body_lines[0]
            body_lines = body_lines[1:]

        body_text = "\n".join(body_lines).strip()
        if not body_text:
            continue

        clause_matches = list(CLAUSE_RE.finditer(body_text))
        if not clause_matches:
            full_text = _compose_legal_chunk_text(heading=heading, title=title, body=body_text)
            chunk_records.extend(
                _build_fallback_chunk_records(
                    text=full_text,
                    chunk_size=chunk_size,
                    overlap=overlap,
                    start_index=chunk_index,
                    metadata_json={
                        "article_number": article_number,
                        "clause_number": [],
                        "article_title": title,
                    },
                )
            )
            chunk_index = len(chunk_records)
            continue

        for clause_position, clause_match in enumerate(clause_matches):
            clause_number = int(clause_match.group(1))
            clause_start = clause_match.start()
            clause_end = clause_matches[clause_position + 1].start() if clause_position + 1 < len(clause_matches) else len(body_text)
            clause_text = body_text[clause_start:clause_end].strip()
            if not clause_text:
                continue

            full_text = _compose_legal_chunk_text(heading=heading, title=title, body=clause_text)
            metadata_json = {
                "article_number": article_number,
                "clause_number": [clause_number],
                "article_title": title,
            }
            if len(full_text) <= chunk_size:
                chunk_records.append(
                    {
                        "chunk_index": chunk_index,
                        "content": full_text,
                        "token_count": len(full_text.split()),
                        "metadata_json": metadata_json,
                    }
                )
                chunk_index += 1
            else:
                overflow_chunks = _build_fallback_chunk_records(
                    text=full_text,
                    chunk_size=chunk_size,
                    overlap=overlap,
                    start_index=chunk_index,
                    metadata_json=metadata_json,
                )
                chunk_records.extend(overflow_chunks)
                chunk_index = len(chunk_records)

    return chunk_records


def _compose_legal_chunk_text(*, heading: str, title: str, body: str) -> str:
    """Compose chunk content so structural context stays with the retrieval unit."""
    parts = [heading]
    if title:
        parts.append(title)
    parts.append(body)
    return "\n".join(parts).strip()


def _build_fallback_chunk_records(
    *,
    text: str,
    chunk_size: int,
    overlap: int,
    start_index: int,
    metadata_json: dict,
) -> list[dict]:
    """Build size-based chunks while preserving supplied metadata."""
    return [
        {
            "chunk_index": start_index + offset,
            "content": chunk,
            "token_count": len(chunk.split()),
            "metadata_json": dict(metadata_json),
        }
        for offset, chunk in enumerate(chunk_text(text, chunk_size=chunk_size, overlap=overlap))
    ]
