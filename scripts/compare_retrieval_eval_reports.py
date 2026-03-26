"""Compare saved retrieval-evaluation report artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_REPORT_DIR = "artifacts/retrieval_eval"
DEFAULT_COMPARISON_DIR = "artifacts/retrieval_eval_comparisons"
DEFAULT_METRICS = ["hit_rate@1", "hit_rate@3", "mrr", "ndcg@3", "precision@1", "precision@3"]


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Compare retrieval-evaluation report artifacts.",
    )
    parser.add_argument(
        "--report-dir",
        default=DEFAULT_REPORT_DIR,
        help="Directory containing retrieval-evaluation report JSON files.",
    )
    parser.add_argument(
        "--pattern",
        default="*.report.json",
        help="Glob pattern for selecting report files inside the report directory.",
    )
    parser.add_argument(
        "--experiment-id",
        required=True,
        help="Experiment id to filter reports by config.experiment_id.",
    )
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=DEFAULT_METRICS,
        help="Aggregate metrics to display as columns.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to save the comparison artifact as JSON.",
    )
    parser.add_argument(
        "--artifact-dir",
        default=DEFAULT_COMPARISON_DIR,
        help="Directory for saved comparison artifacts when --output is not provided.",
    )
    return parser


def main() -> None:
    """Load report artifacts and print a comparison table."""
    args = build_parser().parse_args()
    report_dir = Path(args.report_dir)
    report_paths = sorted(report_dir.glob(args.pattern))
    rows = [_load_row(path, metrics=args.metrics) for path in report_paths]
    rows = [row for row in rows if row.get("experiment_id") == args.experiment_id]

    if not rows:
        raise SystemExit(
            f"No report files found in {report_dir} matching pattern {args.pattern!r} "
            f"for experiment_id={args.experiment_id!r}."
        )
    headers = [
        "experiment_id",
        "dataset_generation_method",
        "retrieval_mode",
        "reranker_type",
        "n_samples",
        *args.metrics,
        "file",
    ]
    _print_table(rows, headers=headers)
    output_path = _resolve_output_path(
        output=args.output,
        artifact_dir=args.artifact_dir,
        experiment_id=args.experiment_id,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_payload = {
        "experiment_id": args.experiment_id,
        "report_dir": str(report_dir),
        "pattern": args.pattern,
        "metrics": args.metrics,
        "rows": rows,
    }
    output_path.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")
    print(f"\nSaved comparison artifact to {output_path}")


def _load_row(path: Path, *, metrics: list[str]) -> dict[str, str | int | float | None]:
    """Load one report into a normalized comparison row."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    config = payload.get("config", {})
    aggregate = payload.get("aggregate", {})
    row: dict[str, str | int | float | None] = {
        "experiment_id": config.get("experiment_id"),
        "dataset_generation_method": config.get("dataset_generation_method"),
        "retrieval_mode": config.get("retrieval_mode"),
        "reranker_type": config.get("reranker_type"),
        "n_samples": payload.get("n_samples"),
        "file": path.name,
    }
    for metric in metrics:
        row[metric] = aggregate.get(metric)
    return row


def _print_table(rows: list[dict[str, str | int | float | None]], *, headers: list[str]) -> None:
    """Print rows as a simple aligned table."""
    widths = {header: max(len(header), max((_render_value(row.get(header)) for row in rows), key=len).__len__()) for header in headers}
    print(" | ".join(header.ljust(widths[header]) for header in headers))
    print("-+-".join("-" * widths[header] for header in headers))
    for row in rows:
        print(" | ".join(_render_value(row.get(header)).ljust(widths[header]) for header in headers))


def _resolve_output_path(*, output: str | None, artifact_dir: str, experiment_id: str | None) -> Path:
    """Resolve where to save the comparison artifact."""
    if output is not None:
        return Path(output)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = experiment_id or timestamp
    return Path(artifact_dir) / f"{stem}.comparison.json"


def _render_value(value: str | int | float | None) -> str:
    """Render a table value consistently."""
    if isinstance(value, float):
        return f"{value:.4f}"
    if value is None:
        return ""
    return str(value)


if __name__ == "__main__":
    main()
