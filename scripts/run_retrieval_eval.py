"""Run offline retrieval evaluation against a labeled JSONL dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from genai_gateway.evaluation.retrieval import EvaluationDataset, RetrievalEvaluationRunner


DEFAULT_DATASET = "apps/legal_doc_qa/data/eval/legal_qa_retrieval_samples.heuristic.jsonl"


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
        help="Optional JSON report path. Defaults beside the dataset with a .report.json suffix.",
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
    return parser


def main() -> None:
    """Run the retrieval-evaluation harness and save a report."""
    args = build_parser().parse_args()
    dataset_path = Path(args.dataset)
    dataset = EvaluationDataset.load(str(dataset_path))
    if args.review_statuses is not None:
        dataset = dataset.filtered(review_statuses={status.strip() for status in args.review_statuses})
    runner = RetrievalEvaluationRunner()
    report = runner.run(dataset, task=args.task, k_values=args.k_values)

    output_path = Path(args.output) if args.output else dataset_path.with_suffix(".report.json")
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
