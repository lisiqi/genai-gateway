"""Unit tests for offline retrieval evaluation helpers."""

from __future__ import annotations

from pathlib import Path

from genai_gateway.evaluation.retrieval import (
    CorpusChunk,
    EvaluationDataset,
    EvaluationSample,
    LLMRetrievalSampleGenerator,
    RetrievalEvaluationRunner,
    build_evaluation_dataset,
)
from genai_gateway.schemas.response_schema import TokenUsage


class FakeRetrievalService:
    def __init__(self, responses: dict[str, list[dict]]) -> None:
        self.responses = responses

    def retrieve(self, question: str, task: str, top_k: int | None = None) -> list[dict]:
        return self.responses[question][:top_k]


class FakeChatProvider:
    def __init__(self, answer: str) -> None:
        self.answer = answer

    @property
    def model_name(self) -> str | None:
        return "fake-model"

    def generate(self, prompt: str, question: str) -> tuple[str, TokenUsage]:
        return self.answer, TokenUsage(prompt_tokens=12, completion_tokens=7, total_tokens=19)


class TestEvaluationDataset:
    def test_save_and_load_preserves_gold_answer(self, tmp_path: Path) -> None:
        dataset = EvaluationDataset(
            samples=[
                EvaluationSample(
                    question="What does Article 1 say?",
                    relevant_chunk_ids=["doc::chunk::0"],
                    gold_answer="Article 1 explains the aim.",
                    metadata={"task": "legal_qa"},
                )
            ]
        )

        target = tmp_path / "dataset.jsonl"
        dataset.save(str(target))
        loaded = EvaluationDataset.load(str(target))

        assert len(loaded.samples) == 1
        assert loaded.samples[0].gold_answer == "Article 1 explains the aim."


class TestRetrievalEvaluationGeneration:
    def test_build_dataset_generates_questions_and_gold_answers(self) -> None:
        dataset = build_evaluation_dataset(
            [
                CorpusChunk(
                    source_path="doc.pdf",
                    chunk_index=0,
                    content="Article 5 Risk assessments Providers shall assess systemic risks.",
                    metadata={"article_number": "5", "clause_number": ["1"], "article_title": "Risk assessments"},
                    title="doc",
                )
            ]
        )

        assert len(dataset.samples) == 1
        sample = dataset.samples[0]
        assert sample.question.startswith("What does Article 5, Clause 1 say about risk assessments")
        assert sample.relevant_chunk_ids == ["doc.pdf::chunk::0"]
        assert sample.gold_answer is not None
        assert sample.metadata["generation_method"] == "heuristic"

    def test_build_dataset_supports_llm_generation(self) -> None:
        generator = LLMRetrievalSampleGenerator(
            chat_provider=FakeChatProvider(
                '{"question": "What obligations apply under Article 5?", "gold_answer": "Article 5 sets out the obligations."}'
            ),
            provider_name="openrouter",
            model_name="test-model",
        )
        dataset = build_evaluation_dataset(
            [
                CorpusChunk(
                    source_path="doc.pdf",
                    chunk_index=0,
                    content="Article 5 obligations Providers shall assess systemic risks.",
                    metadata={"article_number": "5", "clause_number": ["1"], "article_title": "Obligations"},
                    title="doc",
                )
            ],
            generation_method="llm",
            llm_generator=generator,
        )

        sample = dataset.samples[0]
        assert sample.question == "What obligations apply under Article 5?"
        assert sample.gold_answer == "Article 5 sets out the obligations."
        assert sample.metadata["generation_method"] == "llm"
        assert sample.metadata["generator_provider"] == "openrouter"
        assert sample.metadata["generator_model"] == "test-model"

    def test_llm_generation_falls_back_to_heuristic_when_json_is_missing(self) -> None:
        generator = LLMRetrievalSampleGenerator(
            chat_provider=FakeChatProvider("not valid json"),
            provider_name="openrouter",
            model_name="test-model",
        )
        dataset = build_evaluation_dataset(
            [
                CorpusChunk(
                    source_path="doc.pdf",
                    chunk_index=0,
                    content="Article 5 obligations Providers shall assess systemic risks.",
                    metadata={"article_number": "5", "clause_number": ["1"], "article_title": "Obligations"},
                    title="doc",
                )
            ],
            generation_method="llm",
            llm_generator=generator,
        )

        sample = dataset.samples[0]
        assert sample.question.startswith("What does Article 5, Clause 1 say about obligations")
        assert sample.gold_answer is not None
        assert "generation_note" in sample.metadata


class TestRetrievalEvaluationRunner:
    def test_runner_computes_expected_metrics(self) -> None:
        dataset = EvaluationDataset(
            samples=[
                EvaluationSample(
                    question="Q1",
                    relevant_chunk_ids=["doc::chunk::1"],
                )
            ]
        )
        runner = RetrievalEvaluationRunner(
            retrieval_service=FakeRetrievalService(
                {
                    "Q1": [
                        {"chunk_id": "doc::chunk::9"},
                        {"chunk_id": "doc::chunk::1"},
                    ]
                }
            )
        )

        report = runner.run(dataset, task="legal_qa", k_values=[1, 2])

        assert report.n_samples == 1
        assert report.aggregate["hit_rate@1"] == 0.0
        assert report.aggregate["hit_rate@2"] == 1.0
        assert report.aggregate["mrr"] == 0.5
