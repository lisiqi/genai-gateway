"""Run a small batch experiment across prompt versions and quality modes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from genai_gateway.config.settings import get_settings
from genai_gateway.runtime.service import RuntimeService
from genai_gateway.schemas.request_schema import QueryRequest


DEFAULT_QUESTION_FILE = "apps/legal_doc_qa/data/eval/sample_questions.json"


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for experiment runs."""
    parser = argparse.ArgumentParser(
        description="Run a batch of legal QA requests across prompt versions and quality modes.",
    )
    parser.add_argument(
        "--questions-file",
        default=DEFAULT_QUESTION_FILE,
        help="JSON file containing question objects with a 'question' field.",
    )
    parser.add_argument(
        "--prompt-versions",
        nargs="+",
        default=["v1", "v2"],
        help="Prompt versions to compare.",
    )
    parser.add_argument(
        "--quality-modes",
        nargs="+",
        default=["cheap", "default", "high_quality"],
        help="Quality modes to compare.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=4,
        help="Retriever top-k value for experiment requests.",
    )
    parser.add_argument(
        "--reranker-types",
        nargs="+",
        default=["pass_through"],
        help="Reranker types to compare, e.g. pass_through cross_encoder.",
    )
    return parser


def load_questions(path: str) -> list[str]:
    """Load plain questions from a JSON dataset."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Question file must contain a JSON list.")
    questions = [str(item["question"]).strip() for item in payload if isinstance(item, dict) and item.get("question")]
    if not questions:
        raise ValueError("Question file did not contain any usable questions.")
    return questions


def main() -> None:
    """Run the configured experiment matrix and print a compact summary."""
    parser = build_parser()
    args = parser.parse_args()
    questions = load_questions(args.questions_file)
    print("Running experiment matrix...")
    total_requests = 0
    original_reranker_type = os.environ.get("RERANKER_TYPE")
    try:
        for reranker_type in args.reranker_types:
            os.environ["RERANKER_TYPE"] = reranker_type
            get_settings.cache_clear()
            runtime = RuntimeService()
            for prompt_version in args.prompt_versions:
                for quality_mode in args.quality_modes:
                    for question in questions:
                        response = runtime.handle_query(
                            QueryRequest(
                                question=question,
                                task="legal_qa",
                                quality_mode=quality_mode,
                                prompt_version=prompt_version,
                                top_k=args.top_k,
                            )
                        )
                        total_requests += 1
                        print(
                            f"reranker={response.reranking.reranker_type} "
                            f"prompt={prompt_version} "
                            f"mode={quality_mode} "
                            f"provider={response.routing.selected_provider} "
                            f"model={response.routing.selected_model} "
                            f"latency_ms={response.latency_ms:.1f} "
                            f"groundedness={response.evaluation.groundedness_score:.2f} "
                            f"question={question}"
                        )
    finally:
        if original_reranker_type is None:
            os.environ.pop("RERANKER_TYPE", None)
        else:
            os.environ["RERANKER_TYPE"] = original_reranker_type
        get_settings.cache_clear()
    print(f"Completed {total_requests} experiment requests.")


if __name__ == "__main__":
    main()
