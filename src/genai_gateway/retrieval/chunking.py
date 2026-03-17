"""Compatibility exports for legal document parsing and chunk construction."""

from ingestion.chunking import build_legal_chunk_records
from ingestion.legal_parser import parse_legal_structure

__all__ = ["build_legal_chunk_records", "parse_legal_structure"]
