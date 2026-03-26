"""Inspect and curate retrieval-evaluation samples stored as JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from genai_gateway.evaluation.retrieval import EvaluationDataset


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Inspect and review retrieval-evaluation dataset samples.",
    )
    parser.add_argument("--dataset", required=True, help="Input JSONL dataset path.")
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output dataset path. Defaults to in-place update of the input dataset.",
    )
    parser.add_argument("--index", type=int, default=None, help="Zero-based sample index to inspect or edit.")
    parser.add_argument("--show", action="store_true", help="Show one sample selected by --index.")
    parser.add_argument("--summary", action="store_true", help="Print dataset review-status summary.")
    parser.add_argument(
        "--list-status",
        default=None,
        help="List sample indexes whose review_status matches the supplied value.",
    )
    parser.add_argument(
        "--set-status",
        choices=["auto_generated", "unreviewed", "reviewed", "approved", "rejected"],
        default=None,
        help="Set review status for the sample selected by --index.",
    )
    parser.add_argument("--set-question", default=None, help="Replace the sample question for --index.")
    parser.add_argument("--set-gold-answer", default=None, help="Replace the gold answer for --index.")
    parser.add_argument(
        "--set-relevant-chunk-ids",
        nargs="+",
        default=None,
        help="Replace relevant chunk ids for --index.",
    )
    parser.add_argument("--set-reviewer-note", default=None, help="Set or replace reviewer_note for --index.")
    parser.add_argument(
        "--clear-reviewer-note",
        action="store_true",
        help="Remove reviewer_note for the sample selected by --index.",
    )
    return parser


def main() -> None:
    """Inspect or update a retrieval-evaluation dataset."""
    args = build_parser().parse_args()
    dataset_path = Path(args.dataset)
    dataset = EvaluationDataset.load(str(dataset_path))

    if args.summary:
        print(f"Dataset: {dataset_path}")
        print(f"Samples: {len(dataset)}")
        print("Review status counts:")
        for status, count in sorted(dataset.review_counts().items()):
            print(f"  {status}: {count}")

    if args.list_status is not None:
        print(f"Samples with review_status={args.list_status}:")
        for index, sample in enumerate(dataset.samples):
            if sample.review_status == args.list_status:
                print(f"  [{index}] {sample.question}")

    made_changes = False
    if args.index is not None:
        _validate_index(dataset=dataset, index=args.index)
        sample = dataset.samples[args.index]

        if args.show:
            print(json.dumps(sample.to_dict(), indent=2))

        if args.set_status is not None:
            sample.set_review_status(args.set_status)
            made_changes = True
        if args.set_question is not None:
            sample.question = args.set_question.strip()
            made_changes = True
        if args.set_gold_answer is not None:
            sample.gold_answer = args.set_gold_answer.strip() or None
            made_changes = True
        if args.set_relevant_chunk_ids is not None:
            sample.relevant_chunk_ids = [chunk_id.strip() for chunk_id in args.set_relevant_chunk_ids if chunk_id.strip()]
            made_changes = True
        if args.set_reviewer_note is not None:
            sample.set_reviewer_note(args.set_reviewer_note)
            made_changes = True
        if args.clear_reviewer_note:
            sample.set_reviewer_note(None)
            made_changes = True

    if made_changes:
        output_path = Path(args.output) if args.output else dataset_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dataset.save(str(output_path))
        print(f"Updated dataset written to {output_path}")


def _validate_index(*, dataset: EvaluationDataset, index: int) -> None:
    if index < 0 or index >= len(dataset.samples):
        raise IndexError(f"Sample index {index} is out of range for dataset of size {len(dataset.samples)}.")


if __name__ == "__main__":
    main()
