"""Chunking utilities."""

from __future__ import annotations

from ingestion.legal_parser import parse_legal_structure
from ingestion.metadata import build_hierarchy_labels, extract_cross_references


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
    structure = parse_legal_structure(text)
    if not structure.articles:
        return build_chunk_records(structure.normalized_text, chunk_size=chunk_size, overlap=overlap)

    chunk_records: list[dict] = []
    chunk_index = 0

    for article in structure.articles:
        if not article.clauses:
            full_text = _compose_legal_chunk_text(
                heading=article.heading,
                title=article.title,
                body=article.body_text,
            )
            chunk_records.extend(
                _build_fallback_chunk_records(
                    text=full_text,
                    chunk_size=chunk_size,
                    overlap=overlap,
                    start_index=chunk_index,
                    metadata_json={
                        "article_number": article.number,
                        "clause_number": [],
                        "article_title": article.title,
                        "hierarchy_labels": build_hierarchy_labels(
                            article_number=article.number,
                            article_title=article.title,
                            clause_numbers=[],
                        ),
                        "cross_references": extract_cross_references(
                            article.body_text,
                            current_article_number=article.number,
                        ),
                    },
                )
            )
            chunk_index = len(chunk_records)
            continue

        for clause in article.clauses:
            full_text = _compose_legal_chunk_text(
                heading=article.heading,
                title=article.title,
                body=clause.text,
            )
            metadata_json = {
                "article_number": article.number,
                "clause_number": [clause.number],
                "article_title": article.title,
                "hierarchy_labels": build_hierarchy_labels(
                    article_number=article.number,
                    article_title=article.title,
                    clause_numbers=[clause.number],
                ),
                "cross_references": extract_cross_references(
                    clause.text,
                    current_article_number=article.number,
                    current_clause_numbers=[clause.number],
                ),
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
