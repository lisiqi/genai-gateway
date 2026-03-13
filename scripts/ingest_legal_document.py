"""Ingest a legal document into Postgres with deterministic local embeddings."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.repositories import DocumentRepository
from database.session import SessionLocal
from ingestion.chunking import build_legal_chunk_records
from ingestion.load_documents import load_pdf_document
from providers.embeddings import get_embedding_provider


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(description="Ingest a legal PDF into Postgres.")
    parser.add_argument(
        "path",
        nargs="?",
        default="data/legal_documents/digital-services-act-en.pdf",
        help="Path to the source PDF.",
    )
    parser.add_argument("--task", default="legal_qa", help="Task name for retrieval filtering.")
    parser.add_argument("--chunk-size", type=int, default=1400, help="Chunk size in characters.")
    parser.add_argument("--overlap", type=int, default=200, help="Chunk overlap in characters.")
    return parser


def main() -> None:
    """Ingest one legal document."""
    args = build_parser().parse_args()
    source_path = Path(args.path)
    document = load_pdf_document(str(source_path))
    chunk_records = build_legal_chunk_records(
        document["content"],
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )
    embedding_provider = get_embedding_provider()
    embeddings = embedding_provider.embed_texts([chunk["content"] for chunk in chunk_records])
    for chunk, embedding in zip(chunk_records, embeddings, strict=True):
        chunk["embedding"] = embedding

    metadata_json = {
        "page_count": document["page_count"],
        "source_file": source_path.name,
        "embedding_config": embedding_provider.embedding_config(),
    }

    with SessionLocal() as session:
        repository = DocumentRepository(session)
        stored = repository.replace_document(
            task=args.task,
            title=document["title"],
            source_path=document["source"],
            document_type="pdf",
            metadata_json=metadata_json,
            chunks=chunk_records,
        )

    print(
        f"Ingested document id={stored.id} title='{stored.title}' "
        f"chunks={len(chunk_records)} task='{args.task}'"
    )


if __name__ == "__main__":
    main()
