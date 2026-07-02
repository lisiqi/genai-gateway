"""Unit tests for offline retrieval evaluation helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from genai_gateway.evaluation.retrieval import (
    CorpusChunk,
    EvaluationDataset,
    EvaluationSample,
    LLMRetrievalSampleGenerator,
    RelevanceJudge,
    RetrievalEvaluationRunner,
    build_evaluation_dataset,
    pool_relevant_chunks,
)
from genai_gateway.schemas.response_schema import ProviderGenerationMetadata, TokenUsage


class FakeRetrievalService:
    def __init__(self, responses: dict[str, list[dict]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str | None, str | None]] = []

    def retrieve(
        self,
        question: str,
        task: str,
        top_k: int | None = None,
        retrieval_mode: str | None = None,
        lexical_backend: str | None = None,
    ) -> list[dict]:
        self.calls.append((retrieval_mode, lexical_backend))
        return self.responses[question][:top_k]


class BackendAwareRetrievalService:
    """Returns different candidates per (mode, lexical_backend) for pooling tests."""

    def __init__(self, by_key: dict[tuple[str, str | None], list[dict]]) -> None:
        self.by_key = by_key
        self.calls: list[tuple[str | None, str | None]] = []

    def retrieve(
        self,
        question: str,
        task: str,
        top_k: int | None = None,
        retrieval_mode: str | None = None,
        lexical_backend: str | None = None,
    ) -> list[dict]:
        self.calls.append((retrieval_mode, lexical_backend))
        return self.by_key.get((str(retrieval_mode), lexical_backend), [])[:top_k]


class FakeChatProvider:
    def __init__(self, answer: str) -> None:
        self.answer = answer

    @property
    def model_name(self) -> str | None:
        return "fake-model"

    def generate(
        self, prompt: str, question: str
    ) -> tuple[str, TokenUsage, ProviderGenerationMetadata]:
        return (
            self.answer,
            TokenUsage(prompt_tokens=12, completion_tokens=7, total_tokens=19),
            ProviderGenerationMetadata(),
        )


class ScriptedChatProvider:
    """Return canned answers keyed by a substring found in the prompt."""

    def __init__(self, answers_by_marker: dict[str, str], default: str = "no") -> None:
        self.answers_by_marker = answers_by_marker
        self.default = default

    @property
    def model_name(self) -> str | None:
        return "fake-judge"

    def generate(
        self, prompt: str, question: str
    ) -> tuple[str, TokenUsage, ProviderGenerationMetadata]:
        answer = self.default
        for marker, response in self.answers_by_marker.items():
            if marker in prompt:
                answer = response
                break
        return (
            answer,
            TokenUsage(prompt_tokens=5, completion_tokens=1, total_tokens=6),
            ProviderGenerationMetadata(),
        )


class FakeReranker:
    def __init__(self, rerank_fn=None) -> None:
        self._rerank_fn = rerank_fn or (lambda question, chunks: chunks)

    def rerank(self, question: str, chunks: list[dict]) -> list[dict]:
        return self._rerank_fn(question, chunks)

    @property
    def config_summary(self) -> dict:
        return {
            "reranker_type": "fake",
            "reranker_model": None,
            "reranker_top_k": None,
        }


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

    def test_llm_prompt_does_not_leak_article_labels_and_asks_for_paraphrase(self) -> None:
        from genai_gateway.evaluation.retrieval.generation import _build_llm_prompt

        chunk = CorpusChunk(
            source_path="doc.pdf",
            chunk_index=0,
            content="Providers shall assess systemic risks arising from their services.",
            metadata={"article_number": "5", "clause_number": ["1"], "article_title": "Risk assessment"},
            title="DSA",
        )
        prompt = _build_llm_prompt(chunk)

        # the paraphrase guardrail is present
        assert "Do NOT quote exact phrases, article numbers, or section headings" in prompt
        # the article/clause identifiers are the label, not prompt input — not injected
        assert "Location:" not in prompt
        assert "Article title:" not in prompt
        assert "Chunk id:" not in prompt
        assert "Risk assessment" not in prompt
        # the chunk content itself is still provided
        assert "systemic risks" in prompt

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


class TestRelevancePooling:
    def test_pooling_adds_judged_relevant_candidates(self) -> None:
        dataset = EvaluationDataset(
            samples=[
                EvaluationSample(
                    question="What are the obligations?",
                    relevant_chunk_ids=["doc::chunk::0"],
                    metadata={"review_status": "auto_generated"},
                )
            ]
        )
        retrieval = FakeRetrievalService(
            {
                "What are the obligations?": [
                    {"chunk_id": "doc::chunk::0", "content": "source obligations passage"},
                    {"chunk_id": "doc::chunk::1", "content": "RELEVANT duplicate obligations"},
                    {"chunk_id": "doc::chunk::2", "content": "unrelated penalties text"},
                ]
            }
        )
        judge = RelevanceJudge(
            chat_provider=ScriptedChatProvider({"RELEVANT": "yes"}, default="no"),
            provider_name="openrouter",
            model_name="judge-model",
            retrieval_service=retrieval,
            pool_top_k=10,
            pool_retrieval_modes=["dense", "lexical"],
        )

        pool_relevant_chunks(dataset, task="legal_qa", judge=judge)

        sample = dataset.samples[0]
        assert sample.relevant_chunk_ids == ["doc::chunk::0", "doc::chunk::1"]
        pooling = sample.metadata["relevance_pooling"]
        assert pooling["judge_provider"] == "openrouter"
        assert pooling["judge_model"] == "judge-model"
        assert pooling["judged_relevant"] == ["doc::chunk::1"]
        # source chunk is never re-judged; only non-source candidates are
        assert set(pooling["candidates_judged"]) == {"doc::chunk::1", "doc::chunk::2"}
        assert pooling["pool_retrieval_modes"] == ["dense", "lexical"]

    def test_mixed_backend_pools_candidates_from_both_fts_and_bm25(self) -> None:
        from genai_gateway.evaluation.retrieval import resolve_pool_lexical_backends

        dataset = EvaluationDataset(
            samples=[EvaluationSample(question="Q", relevant_chunk_ids=["doc::chunk::0"])]
        )
        retrieval = BackendAwareRetrievalService(
            {
                ("dense", None): [{"chunk_id": "doc::chunk::0", "content": "source"}],
                ("lexical", "fts"): [{"chunk_id": "doc::chunk::fts", "content": "RELEVANT fts hit"}],
                ("lexical", "bm25"): [{"chunk_id": "doc::chunk::bm25", "content": "RELEVANT bm25 hit"}],
            }
        )
        judge = RelevanceJudge(
            chat_provider=ScriptedChatProvider({"RELEVANT": "yes"}, default="no"),
            provider_name="openrouter",
            model_name="judge-model",
            retrieval_service=retrieval,
            pool_lexical_backends=resolve_pool_lexical_backends("mixed"),
        )

        pool_relevant_chunks(dataset, task="legal_qa", judge=judge)

        sample = dataset.samples[0]
        # both lexical backends contributed judged-relevant candidates
        assert set(sample.relevant_chunk_ids) == {"doc::chunk::0", "doc::chunk::fts", "doc::chunk::bm25"}
        assert ("lexical", "fts") in retrieval.calls
        assert ("lexical", "bm25") in retrieval.calls
        assert sample.metadata["relevance_pooling"]["pool_lexical_backends"] == ["fts", "bm25"]

    def test_resolve_pool_lexical_backends(self) -> None:
        from genai_gateway.evaluation.retrieval import resolve_pool_lexical_backends

        assert resolve_pool_lexical_backends("bm25") == ["bm25"]
        assert resolve_pool_lexical_backends("fts") == ["fts"]
        assert resolve_pool_lexical_backends("mixed") == ["fts", "bm25"]

    def test_pooling_keeps_single_positive_when_nothing_judged_relevant(self) -> None:
        dataset = EvaluationDataset(
            samples=[
                EvaluationSample(question="Q", relevant_chunk_ids=["doc::chunk::0"])
            ]
        )
        retrieval = FakeRetrievalService(
            {
                "Q": [
                    {"chunk_id": "doc::chunk::0", "content": "source"},
                    {"chunk_id": "doc::chunk::5", "content": "other"},
                ]
            }
        )
        judge = RelevanceJudge(
            chat_provider=ScriptedChatProvider({}, default="no"),
            provider_name="openai",
            model_name="m",
            retrieval_service=retrieval,
        )

        pool_relevant_chunks(dataset, task="legal_qa", judge=judge)

        sample = dataset.samples[0]
        assert sample.relevant_chunk_ids == ["doc::chunk::0"]
        assert sample.metadata["relevance_pooling"]["judged_relevant"] == []


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

    def test_runner_can_evaluate_reranked_results(self) -> None:
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
                        {"chunk_id": "doc::chunk::9", "content": "wrong"},
                        {"chunk_id": "doc::chunk::1", "content": "right"},
                    ]
                }
            )
        )

        def rerank_fn(question: str, chunks: list[dict]) -> list[dict]:
            return [chunks[1], chunks[0]]

        with patch("genai_gateway.evaluation.retrieval.harness.get_reranker", return_value=FakeReranker(rerank_fn)):
            report = runner.run(dataset, task="legal_qa", k_values=[1, 2], reranker_type="cross_encoder")

        assert report.aggregate["hit_rate@1"] == 1.0
        assert report.aggregate["mrr"] == 1.0
        assert report.config["reranker_type"] == "fake"
