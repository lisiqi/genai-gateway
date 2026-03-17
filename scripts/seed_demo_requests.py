"""Seed a small set of legal QA requests for dashboard demos."""

from __future__ import annotations

import argparse

from genai_gateway.runtime.service import RuntimeService
from genai_gateway.schemas.request_schema import QueryRequest


DEFAULT_QUESTIONS = [
    "What is the aim of this Regulation?",
    "How does the Regulation define intermediary services?",
    "What obligations apply to providers regarding illegal content notices?",
]
DEFAULT_QUALITY_MODES = ["cheap", "default", "high_quality"]


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for demo request seeding."""
    parser = argparse.ArgumentParser(
        description="Seed a few legal QA requests into Postgres and the local request log.",
    )
    parser.add_argument(
        "--prompt-version",
        default="v1",
        help="Prompt version to use for seeded requests.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=4,
        help="Retriever top-k value for seeded requests.",
    )
    return parser


def main() -> None:
    """Run a small batch of requests across quality modes."""
    parser = build_parser()
    args = parser.parse_args()

    runtime = RuntimeService()
    total_requests = 0
    print("Seeding demo requests...")
    for quality_mode in DEFAULT_QUALITY_MODES:
        for question in DEFAULT_QUESTIONS:
            result = runtime.handle_query(
                QueryRequest(
                    question=question,
                    task="legal_qa",
                    quality_mode=quality_mode,
                    prompt_version=args.prompt_version,
                    top_k=args.top_k,
                )
            )
            total_requests += 1
            print(
                f"[{quality_mode}] "
                f"provider={result.routing.selected_provider} "
                f"model={result.routing.selected_model} "
                f"fallback={result.routing.fallback_used} "
                f"question={question}"
            )
    print(f"Seeded {total_requests} requests.")


if __name__ == "__main__":
    main()
