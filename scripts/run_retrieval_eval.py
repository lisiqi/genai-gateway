"""Run offline retrieval evaluation against a labeled JSONL dataset."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from genai_gateway.evaluation.retrieval import EvaluationDataset, RetrievalEvaluationRunner


DEFAULT_DATASET = "apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl"
DEFAULT_ARTIFACT_DIR = "artifacts/retrieval_eval"


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Run offline retrieval evaluation against a labeled dataset.",
    )
    parser.add_argument("--task", default="legal_qa", help="Task corpus to evaluate.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Input JSONL dataset path.")
    parser.add_argument(
        "--k-values",
        nargs="+",
        type=int,
        default=[1, 3, 5, 10],
        help="IR metric cutoffs to compute.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional JSON report path. Defaults to a timestamped artifact under artifacts/retrieval_eval/.",
    )
    parser.add_argument(
        "--artifact-dir",
        default=DEFAULT_ARTIFACT_DIR,
        help="Base directory for timestamped reports when --output is not provided.",
    )
    parser.add_argument(
        "--experiment-id",
        default=None,
        help="Optional experiment id to attach to the report and default artifact filename.",
    )
    parser.add_argument(
        "--show-failures",
        type=int,
        default=5,
        help="How many low-MRR failures to print.",
    )
    parser.add_argument(
        "--review-statuses",
        nargs="+",
        default=None,
        help="Optional list of review statuses to include, e.g. approved reviewed.",
    )
    parser.add_argument(
        "--exclude-rejected",
        action="store_true",
        help="Drop samples marked review_status=rejected, even on an otherwise unfiltered run.",
    )
    parser.add_argument(
        "--reranker-type",
        default=None,
        help="Optional reranker override such as pass_through or cross_encoder.",
    )
    parser.add_argument(
        "--reranker-model",
        default=None,
        help="Optional reranker model override for cross-encoder evaluation.",
    )
    parser.add_argument(
        "--reranker-top-k",
        type=int,
        default=None,
        help="Optional reranker top-k override.",
    )
    return parser


def main() -> None:
    """Run the retrieval-evaluation harness and save a report."""
    args = build_parser().parse_args()
    dataset_path = Path(args.dataset)
    dataset = EvaluationDataset.load(str(dataset_path))
    generation_methods = {
        str(sample.metadata.get("generation_method")).strip()
        for sample in dataset.samples
        if sample.metadata.get("generation_method") is not None
    }
    dataset_generation_method = None
    if len(generation_methods) == 1:
        dataset_generation_method = next(iter(generation_methods))
    elif generation_methods:
        dataset_generation_method = "mixed"
    selected_review_statuses: list[str] | None = None
    exclude_statuses = {"rejected"} if args.exclude_rejected else None
    if args.review_statuses is not None or exclude_statuses is not None:
        selected_review_statuses = (
            sorted({status.strip() for status in args.review_statuses})
            if args.review_statuses is not None
            else None
        )
        dataset = dataset.filtered(
            review_statuses=set(selected_review_statuses) if selected_review_statuses else None,
            exclude_statuses=exclude_statuses,
        )
    runner = RetrievalEvaluationRunner()
    report = runner.run(
        dataset,
        task=args.task,
        k_values=args.k_values,
        reranker_type=args.reranker_type,
        reranker_model=args.reranker_model,
        reranker_top_k=args.reranker_top_k,
        extra_config={
            "experiment_id": args.experiment_id,
            "dataset_path": str(dataset_path),
            "dataset_name": dataset_path.name,
            "dataset_generation_method": dataset_generation_method,
            "review_statuses": selected_review_statuses,
            "excluded_statuses": sorted(exclude_statuses) if exclude_statuses else None,
        },
    )

    if args.output:
        output_path = Path(args.output)
    else:
        artifact_dir = Path(args.artifact_dir)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        experiment_id = args.experiment_id or timestamp
        retrieval_mode = str(report.config.get("retrieval_mode", "unknown"))
        reranker_type = str(report.config.get("reranker_type", "unknown"))
        dataset_stem = dataset_path.stem.replace(" ", "_")
        output_path = artifact_dir / (
            f"{experiment_id}_{args.task}_{dataset_stem}_{retrieval_mode}_{reranker_type}.report.json"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    print(f"Retrieval evaluation report saved to {output_path}")
    print(f"Samples: {report.n_samples}")
    print("Aggregate metrics:")
    for metric_name, value in sorted(report.aggregate.items()):
        print(f"  {metric_name}: {value:.4f}")

    failures = sorted(report.results, key=lambda result: result.metrics.get("mrr", 0.0))[: args.show_failures]
    if failures:
        print("Lowest-MRR samples:")
        for result in failures:
            print(f"  question={result.question}")
            print(f"    mrr={result.metrics.get('mrr', 0.0):.4f}")
            print(f"    relevant={result.relevant_chunk_ids}")
            print(f"    retrieved={result.retrieved_ids[: max(args.k_values)]}")


if __name__ == "__main__":
    main()
