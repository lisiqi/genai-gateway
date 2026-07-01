"""Generate a retrieval-evaluation dataset from stored corpus chunks."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from time import perf_counter

from sqlalchemy import Select, select


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.models import Document, DocumentChunk
from database.session import SessionLocal
from genai_gateway.evaluation.retrieval import (
    CorpusChunk,
    LLMRetrievalSampleGenerator,
    RelevanceJudge,
    build_evaluation_dataset,
    pool_relevant_chunks,
)
from genai_gateway.providers.chat import get_chat_provider
from genai_gateway.retrieval.retriever import RetrievalService
from genai_gateway.runtime.policies.model_routing import ModelRoutingPolicy


DEFAULT_OUTPUT_TEMPLATE = "apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.{generation_method}{variant}.jsonl"


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Generate a retrieval-evaluation dataset from stored corpus chunks.",
    )
    parser.add_argument("--task", default="legal_qa", help="Task corpus to sample from.")
    parser.add_argument(
        "--output",
        default=None,
        help="Target JSONL dataset path. Defaults to a generation-method-specific filename.",
    )
    parser.add_argument(
        "--generation-method",
        choices=["heuristic", "llm"],
        default="heuristic",
        help="How to generate questions and gold answers.",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=100,
        help="Maximum number of generated samples.",
    )
    parser.add_argument(
        "--document-id",
        type=int,
        default=None,
        help="Optional document id to restrict generation to one ingested document.",
    )
    parser.add_argument(
        "--generation-quality-mode",
        default="cheap",
        help="Routing quality mode used to select the LLM generator when generation-method=llm.",
    )
    parser.add_argument(
        "--generation-prompt-version",
        default="v1",
        help="Prompt version passed to route resolution when selecting the LLM generator.",
    )
    parser.add_argument(
        "--generation-provider",
        default=None,
        help="Optional explicit provider override; bypasses the routed provider for LLM generation.",
    )
    parser.add_argument(
        "--generation-model",
        default=None,
        help="Optional explicit model override; bypasses the routed model for LLM generation.",
    )
    parser.add_argument(
        "--judge-relevance",
        action="store_true",
        help=(
            "After generation, expand single-positive labels to multi-positive using "
            "retrieval pooling + an LLM relevance judge."
        ),
    )
    parser.add_argument(
        "--judge-quality-mode",
        default="cheap",
        help="Routing quality mode used to select the LLM relevance judge.",
    )
    parser.add_argument(
        "--judge-prompt-version",
        default="v1",
        help="Prompt version passed to route resolution when selecting the relevance judge.",
    )
    parser.add_argument(
        "--judge-provider",
        default=None,
        help="Optional explicit provider override for the relevance judge.",
    )
    parser.add_argument(
        "--judge-model",
        default=None,
        help="Optional explicit model override for the relevance judge.",
    )
    parser.add_argument(
        "--pool-top-k",
        type=int,
        default=10,
        help="Number of candidate chunks to pool per retrieval mode before judging.",
    )
    parser.add_argument(
        "--pool-retrieval-modes",
        nargs="+",
        default=["dense", "lexical"],
        help="Retrieval modes unioned into the candidate pool (default: dense lexical).",
    )
    return parser


def main() -> None:
    """Generate and persist a retrieval-evaluation dataset."""
    args = build_parser().parse_args()
    started_at = perf_counter()

    print(f"[1/3] Loading stored chunks for task='{args.task}'...", flush=True)

    with SessionLocal() as session:
        stmt: Select[tuple[Document, DocumentChunk]] = (
            select(Document, DocumentChunk)
            .join(DocumentChunk, Document.id == DocumentChunk.document_id)
            .where(Document.task == args.task)
            .order_by(Document.id, DocumentChunk.chunk_index)
        )
        if args.document_id is not None:
            stmt = stmt.where(Document.id == args.document_id)
        rows = session.execute(stmt).all()

    if not rows:
        raise ValueError(
            f"No chunks found for task '{args.task}'. Ingest the corpus before generating evaluation samples."
        )

    print(f"[1/3] Loaded {len(rows)} stored chunks.", flush=True)

    chunks = [
        CorpusChunk(
            source_path=document.source_path,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            metadata=chunk.metadata_json or {},
            title=document.title,
        )
        for document, chunk in rows
    ]
    llm_generator = None
    if args.generation_method == "llm":
        routing_decision = ModelRoutingPolicy().select(
            task=args.task,
            quality_mode=args.generation_quality_mode,
            prompt_version=args.generation_prompt_version,
        )
        provider_name = args.generation_provider or routing_decision.provider
        model_name = args.generation_model or routing_decision.model
        llm_generator = LLMRetrievalSampleGenerator(
            chat_provider=get_chat_provider(provider_name=provider_name, model_name=model_name),
            provider_name=provider_name,
            model_name=model_name,
        )
        print(
            "Using LLM generation route "
            f"provider={provider_name} model={model_name} quality_mode={args.generation_quality_mode}",
            flush=True,
        )

    print(
        f"[2/3] Generating dataset with method='{args.generation_method}' "
        f"max_samples={args.max_samples}...",
        flush=True,
    )
    generation_started_at = perf_counter()

    def on_progress(completed: int, total: int, chunk: CorpusChunk) -> None:
        if args.generation_method == "llm" or completed == total or completed % 10 == 0:
            print(
                f"[2/3] Generated {completed}/{total} samples "
                f"(chunk_index={chunk.chunk_index}, elapsed={perf_counter() - generation_started_at:.2f}s)",
                flush=True,
            )

    dataset = build_evaluation_dataset(
        chunks,
        max_samples=args.max_samples,
        generation_method=args.generation_method,
        llm_generator=llm_generator,
        progress_callback=on_progress,
    )

    if args.judge_relevance:
        judge_routing = ModelRoutingPolicy().select(
            task=args.task,
            quality_mode=args.judge_quality_mode,
            prompt_version=args.judge_prompt_version,
        )
        judge_provider = args.judge_provider or judge_routing.provider
        judge_model = args.judge_model or judge_routing.model
        judge = RelevanceJudge(
            chat_provider=get_chat_provider(provider_name=judge_provider, model_name=judge_model),
            provider_name=judge_provider,
            model_name=judge_model,
            retrieval_service=RetrievalService(),
            pool_top_k=args.pool_top_k,
            pool_retrieval_modes=args.pool_retrieval_modes,
        )
        print(
            "[2b/3] Pooling relevance judgments with "
            f"provider={judge_provider} model={judge_model} "
            f"pool_top_k={args.pool_top_k} modes={args.pool_retrieval_modes}...",
            flush=True,
        )
        pooling_started_at = perf_counter()
        total_added = 0

        def on_pooling_progress(completed: int, total: int, sample) -> None:
            nonlocal total_added
            total_added += len(sample.metadata.get("relevance_pooling", {}).get("judged_relevant", []))
            print(
                f"[2b/3] Judged {completed}/{total} samples "
                f"(+{total_added} relevant labels so far, "
                f"elapsed={perf_counter() - pooling_started_at:.2f}s)",
                flush=True,
            )

        pool_relevant_chunks(
            dataset,
            task=args.task,
            judge=judge,
            progress_callback=on_pooling_progress,
        )
        print(
            f"[2b/3] Relevance pooling added {total_added} labels across {len(dataset)} samples.",
            flush=True,
        )

    default_variant = ".pooled" if args.judge_relevance else ""
    target = Path(
        args.output
        or DEFAULT_OUTPUT_TEMPLATE.format(
            generation_method=args.generation_method,
            variant=default_variant,
        )
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"[3/3] Writing dataset to {target}...", flush=True)
    dataset.save(str(target))

    print(
        f"Generated {len(dataset)} retrieval-evaluation samples for task='{args.task}' "
        f"using generation_method='{args.generation_method}' "
        f"from {len(chunks)} chunks -> {target} "
        f"in {perf_counter() - started_at:.2f}s"
    )


if __name__ == "__main__":
    main()
