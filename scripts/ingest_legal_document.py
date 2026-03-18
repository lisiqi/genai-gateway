"""Ingest a legal document into Postgres with deterministic local embeddings."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.repositories import DocumentRepository
from database.session import SessionLocal
from ingestion.chunking import build_legal_chunk_records
from ingestion.load_documents import load_pdf_document
from genai_gateway.providers.embeddings import get_embedding_provider


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(description="Ingest a legal PDF into Postgres.")
    parser.add_argument(
        "path",
        nargs="?",
        default="apps/legal_doc_qa/data/legal_documents/digital-services-act-en.pdf",
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

    started_at = perf_counter()
    print(f"[1/4] Loading document from {source_path}...", flush=True)
    document = load_pdf_document(str(source_path))

    chunking_started_at = perf_counter()
    print(f"[2/4] Building chunks from {document['page_count']} pages...", flush=True)
    chunk_records = build_legal_chunk_records(
        document["content"],
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )
    print(
        f"[2/4] Built {len(chunk_records)} chunks in {perf_counter() - chunking_started_at:.2f}s.",
        flush=True,
    )

    embedding_provider = get_embedding_provider()
    embedding_started_at = perf_counter()
    print(
        "[3/4] Generating embeddings "
        f"with provider={embedding_provider.provider_name} model={embedding_provider.model_name}...",
        flush=True,
    )

    last_progress_at = embedding_started_at

    def on_embedding_progress(completed: int, total: int, batch_size: int) -> None:
        nonlocal last_progress_at
        now = perf_counter()
        print(
            f"[3/4] Embedded {completed}/{total} chunks "
            f"(last batch={batch_size}, batch_time={now - last_progress_at:.2f}s, elapsed={now - embedding_started_at:.2f}s)",
            flush=True,
        )
        last_progress_at = now

    embeddings = embedding_provider.embed_texts(
        [chunk["content"] for chunk in chunk_records],
        progress_callback=on_embedding_progress,
    )
    for chunk, embedding in zip(chunk_records, embeddings, strict=True):
        chunk["embedding"] = embedding
    print(f"[3/4] Embeddings completed in {perf_counter() - embedding_started_at:.2f}s.", flush=True)

    metadata_json = {
        "page_count": document["page_count"],
        "source_file": source_path.name,
        "embedding_config": embedding_provider.embedding_config(),
    }

    db_started_at = perf_counter()
    print("[4/4] Writing document and chunks to Postgres...", flush=True)
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
    print(f"[4/4] Database write completed in {perf_counter() - db_started_at:.2f}s.", flush=True)

    print(
        f"Ingested document id={stored.id} title='{stored.title}' "
        f"chunks={len(chunk_records)} task='{args.task}' "
        f"total_time={perf_counter() - started_at:.2f}s"
    )


if __name__ == "__main__":
    main()
