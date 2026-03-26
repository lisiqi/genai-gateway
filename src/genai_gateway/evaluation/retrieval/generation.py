"""Dataset generation helpers for offline retrieval evaluation.

The module has two generation paths:

- heuristic generation: derive questions and gold answers from chunk metadata/text
- llm generation: ask a chat model to produce question/gold-answer pairs per chunk
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
import math
import re
from typing import Any

from genai_gateway.evaluation.retrieval.datasets import EvaluationDataset, EvaluationSample
from genai_gateway.providers.chat.base import ChatProvider


@dataclass
class CorpusChunk:
    """Serializable retrieval chunk record used for dataset generation."""

    source_path: str
    chunk_index: int
    content: str
    metadata: dict[str, Any]
    title: str | None = None

    @property
    def chunk_id(self) -> str:
        """Return the retrieval chunk identifier used by the runtime."""
        return f"{self.source_path}::chunk::{self.chunk_index}"


@dataclass
class GeneratedSampleContent:
    """Generated question/answer payload before dataset metadata is attached."""

    question: str
    gold_answer: str | None
    metadata: dict[str, Any]


class LLMRetrievalSampleGenerator:
    """Generate retrieval-evaluation samples from corpus chunks with an LLM."""

    def __init__(self, *, chat_provider: ChatProvider, provider_name: str, model_name: str) -> None:
        self.chat_provider = chat_provider
        self.provider_name = provider_name
        self.model_name = model_name

    def generate_sample(self, chunk: CorpusChunk) -> GeneratedSampleContent:
        """Generate one retrieval-evaluation sample for a chunk."""
        prompt = _build_llm_prompt(chunk)
        raw_response, usage = self.chat_provider.generate(
            prompt=prompt,
            question="Generate one retrieval-evaluation sample as JSON.",
        )
        payload = _parse_llm_json(raw_response)
        generated_question = str(payload.get("question", "")).strip()
        generated_gold_answer = str(payload.get("gold_answer", "")).strip() or None

        fallback = _build_heuristic_sample_content(chunk)
        question = generated_question or fallback.question
        gold_answer = generated_gold_answer or fallback.gold_answer
        metadata = {
            "generation_method": "llm",
            "generator_provider": self.provider_name,
            "generator_model": self.model_name,
            "generator_usage": usage.model_dump(),
        }
        if not generated_question:
            metadata["generation_note"] = "llm_question_missing_fell_back_to_heuristic"
        if not generated_gold_answer:
            metadata["generation_note"] = (
                metadata.get("generation_note", "") + "; "
                if metadata.get("generation_note")
                else ""
            ) + "llm_gold_answer_missing_fell_back_to_heuristic"
        return GeneratedSampleContent(question=question, gold_answer=gold_answer, metadata=metadata)


def build_evaluation_dataset(
    chunks: list[CorpusChunk],
    *,
    max_samples: int | None = None,
    generation_method: str = "heuristic",
    llm_generator: LLMRetrievalSampleGenerator | None = None,
    progress_callback: Callable[[int, int, CorpusChunk], None] | None = None,
) -> EvaluationDataset:
    """Generate a retrieval-evaluation dataset from corpus chunks."""
    if max_samples is not None and max_samples <= 0:
        raise ValueError("max_samples must be greater than zero when provided.")
    if generation_method not in {"heuristic", "llm"}:
        raise ValueError("generation_method must be one of: heuristic, llm.")
    if generation_method == "llm" and llm_generator is None:
        raise ValueError("llm_generator is required when generation_method='llm'.")

    selected_chunks = _select_evenly_spaced(chunks, max_samples)
    samples: list[EvaluationSample] = []
    question_counts: dict[str, int] = {}
    for chunk in selected_chunks:
        generated = _generate_sample_content(
            chunk,
            generation_method=generation_method,
            llm_generator=llm_generator,
        )
        base_question = generated.question
        occurrence = question_counts.get(base_question, 0) + 1
        question_counts[base_question] = occurrence
        question = base_question if occurrence == 1 else f"{base_question} (passage {occurrence})"
        samples.append(
            EvaluationSample(
                question=question,
                relevant_chunk_ids=[chunk.chunk_id],
                gold_answer=generated.gold_answer,
                metadata={
                    "task": "legal_qa",
                    "source_path": chunk.source_path,
                    "chunk_index": chunk.chunk_index,
                    "article_number": chunk.metadata.get("article_number"),
                    "clause_number": chunk.metadata.get("clause_number"),
                    "article_title": chunk.metadata.get("article_title"),
                    "document_title": chunk.title,
                    "review_status": "auto_generated",
                    **generated.metadata,
                },
            )
        )
        if progress_callback is not None:
            progress_callback(len(samples), len(selected_chunks), chunk)
    return EvaluationDataset(samples=samples)


# Shared dataset assembly helpers


def _generate_sample_content(
    chunk: CorpusChunk,
    *,
    generation_method: str,
    llm_generator: LLMRetrievalSampleGenerator | None,
) -> GeneratedSampleContent:
    if generation_method == "heuristic":
        return _build_heuristic_sample_content(chunk)

    assert llm_generator is not None
    return llm_generator.generate_sample(chunk)


def _build_heuristic_sample_content(chunk: CorpusChunk) -> GeneratedSampleContent:
    """Build a retrieval-evaluation sample directly from metadata and chunk text."""
    return GeneratedSampleContent(
        question=_build_heuristic_question(chunk),
        gold_answer=_build_heuristic_gold_answer(chunk.content),
        metadata={"generation_method": "heuristic"},
    )


def _select_evenly_spaced(chunks: list[CorpusChunk], max_samples: int | None) -> list[CorpusChunk]:
    """Select chunks at roughly even intervals to preserve deterministic corpus coverage."""
    if max_samples is None or len(chunks) <= max_samples:
        return chunks

    step = len(chunks) / max_samples
    selected: list[CorpusChunk] = []
    seen_indices: set[int] = set()
    for sample_index in range(max_samples):
        chunk_index = min(math.floor(sample_index * step), len(chunks) - 1)
        while chunk_index in seen_indices and chunk_index < len(chunks) - 1:
            chunk_index += 1
        seen_indices.add(chunk_index)
        selected.append(chunks[chunk_index])
    return selected


# Heuristic generation path


def _build_heuristic_question(chunk: CorpusChunk) -> str:
    """Create a deterministic question from chunk metadata."""
    article_number = chunk.metadata.get("article_number")
    clause_numbers = chunk.metadata.get("clause_number") or []
    article_title = _normalize_phrase(chunk.metadata.get("article_title"))

    location = _build_location_label(article_number=article_number, clause_numbers=clause_numbers)
    if location and article_title:
        templates = [
            f"What does {location} say about {article_title}?",
            f"How does {location} address {article_title}?",
        ]
        return templates[chunk.chunk_index % len(templates)]
    if location:
        return f"What does {location} say?"
    if article_title:
        return f"What does the document say about {article_title}?"

    topic = _extract_topic(chunk.content)
    return f"What does this section say about {topic}?"


def _build_heuristic_gold_answer(content: str) -> str | None:
    """Take a short chunk-derived excerpt as the heuristic gold answer."""
    cleaned = " ".join(content.split())
    if not cleaned:
        return None
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) >= 40:
            return sentence[:280]
    return cleaned[:280]


def _build_location_label(*, article_number: Any, clause_numbers: list[Any]) -> str:
    parts: list[str] = []
    if article_number:
        parts.append(f"Article {article_number}")
    if clause_numbers:
        clause_label = ", ".join(str(number) for number in clause_numbers)
        parts.append(f"Clause {clause_label}")
    return ", ".join(parts)


# LLM generation path


def _build_llm_prompt(chunk: CorpusChunk) -> str:
    """Create the prompt used to ask an LLM for a benchmark sample."""
    article_number = chunk.metadata.get("article_number")
    clause_numbers = chunk.metadata.get("clause_number") or []
    article_title = chunk.metadata.get("article_title")
    location = _build_location_label(article_number=article_number, clause_numbers=clause_numbers)
    return (
        "You are generating an offline retrieval-evaluation sample for a legal RAG benchmark.\n"
        "Given one chunk of legal text, produce exactly one natural user question that is primarily answered by this chunk.\n"
        "Also produce a concise gold answer grounded only in the chunk.\n"
        "Return strict JSON with keys `question` and `gold_answer`.\n"
        "Do not include markdown fences or any extra commentary.\n\n"
        f"Document title: {chunk.title or 'unknown'}\n"
        f"Location: {location or 'unknown'}\n"
        f"Article title: {article_title or 'unknown'}\n"
        f"Chunk id: {chunk.chunk_id}\n"
        "Chunk content:\n"
        f"{chunk.content}\n"
    )


def _parse_llm_json(raw_response: str) -> dict[str, Any]:
    """Parse best-effort JSON from an LLM response."""
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match is None:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    return parsed if isinstance(parsed, dict) else {}


# Shared text helpers


def _normalize_phrase(value: Any) -> str | None:
    if value is None:
        return None
    phrase = str(value).strip().strip(".")
    return phrase.lower() if phrase else None


def _extract_topic(content: str) -> str:
    cleaned = " ".join(content.split())
    if not cleaned:
        return "this provision"
    first_sentence = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)[0]
    words = first_sentence.split()
    if not words:
        return "this provision"
    return " ".join(words[:8]).rstrip(".,:;")
