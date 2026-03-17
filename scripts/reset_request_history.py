"""Clear request logs and evaluations for a clean demo history."""

from __future__ import annotations

import argparse
from pathlib import Path

from database.models import Evaluation, QueryLog
from database.session import SessionLocal


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for request history reset."""
    parser = argparse.ArgumentParser(
        description="Delete request logs and evaluations, optionally clearing the JSONL log file too.",
    )
    parser.add_argument(
        "--keep-jsonl",
        action="store_true",
        help="Keep logs/requests.jsonl instead of truncating it.",
    )
    return parser


def main() -> None:
    """Delete request/evaluation rows and optionally truncate the local JSONL log."""
    parser = build_parser()
    args = parser.parse_args()

    with SessionLocal() as session:
        deleted_evaluations = session.query(Evaluation).delete()
        deleted_query_logs = session.query(QueryLog).delete()
        session.commit()

    print(
        f"Deleted {deleted_evaluations} evaluations and {deleted_query_logs} query logs from Postgres."
    )

    if not args.keep_jsonl:
        log_path = Path("logs/requests.jsonl")
        if log_path.exists():
            log_path.write_text("", encoding="utf-8")
            print(f"Truncated {log_path}.")
        else:
            print("No local JSONL log file found.")


if __name__ == "__main__":
    main()
