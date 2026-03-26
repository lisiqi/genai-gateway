"""Unit tests for runtime guardrails."""

from __future__ import annotations

from types import SimpleNamespace

from genai_gateway.runtime.guardrails import assess_retrieval_evidence, classify_request_scope
from genai_gateway.runtime.workflows.rag_workflow import RagWorkflow
from genai_gateway.schemas.request_schema import QueryRequest
from genai_gateway.schemas.response_schema import TokenUsage


class FakePromptManager:
    def load_prompt(self, task: str, version: str) -> str:
        return "prompt"

    def render_prompt(self, prompt_text: str, question: str, retrieved_chunks: list[dict]) -> str:
        return "rendered"


class FakeRetrievalService:
    def __init__(self, chunks: list[dict]) -> None:
        self._chunks = chunks

    def retrieve(self, question: str, task: str, retrieval_mode: str | None = None, top_k: int | None = None) -> list[dict]:
        return self._chunks[:top_k]

    def resolve_retrieval_mode(self, override: str | None = None) -> str:
        return override or "hybrid"


class FakeRoutingPolicy:
    def select(self, task: str, quality_mode: str, prompt_version: str):
        return SimpleNamespace(
            provider="openrouter",
            model="demo-model",
            fallback_provider=None,
            fallback_model=None,
            reason="test",
        )


class FakeLogger:
    def log(self, request, response) -> None:
        return None


class FakeChatProvider:
    def generate(self, prompt: str, question: str):
        return "generated answer", TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2)


class FakeReranker:
    @property
    def config_summary(self) -> dict:
        return {
            "reranker_type": "pass_through",
            "reranker_model": None,
            "reranker_top_k": None,
        }

    def rerank(self, question: str, chunks: list[dict]) -> list[dict]:
        return chunks


def test_scope_guardrail_rejects_obvious_off_topic_request(monkeypatch) -> None:
    assert classify_request_scope(question="What is the weather in Amsterdam?", task="legal_qa").status == "out_of_scope"

    workflow = RagWorkflow()
    workflow.prompt_manager = FakePromptManager()
    workflow.retrieval_service = FakeRetrievalService([])
    workflow.model_routing_policy = FakeRoutingPolicy()
    workflow.request_logger = FakeLogger()
    monkeypatch.setattr("genai_gateway.runtime.workflows.rag_workflow.get_reranker", lambda reranker_type=None: FakeReranker())

    response = workflow.run(
        request=QueryRequest(question="What is the weather in Amsterdam?", task="legal_qa"),
        context=SimpleNamespace(
            task="legal_qa",
            quality_mode="default",
            prompt_version="v1",
            retrieval_mode="hybrid",
            top_k=4,
            reranker_type=None,
        ),
    )

    assert response.guardrails.abstained is True
    assert response.guardrails.scope_status == "out_of_scope"
    assert response.routing.selected_provider == "guardrail"
    assert response.model_name is None


def test_evidence_guardrail_abstains_when_requested_article_is_missing(monkeypatch) -> None:
    decision = assess_retrieval_evidence(
        question="What does Article 99 say?",
        retrieved_chunks=[{"metadata": {"article_number": "12"}}],
    )
    assert decision.status == "insufficient"

    workflow = RagWorkflow()
    workflow.prompt_manager = FakePromptManager()
    workflow.retrieval_service = FakeRetrievalService(
        [
            {
                "chunk_id": "doc::chunk::0",
                "source": "doc.pdf",
                "content": "Article 12 content",
                "score": 0.5,
                "title": "doc",
                "chunk_index": 0,
                "metadata": {"article_number": "12"},
            }
        ]
    )
    workflow.model_routing_policy = FakeRoutingPolicy()
    workflow.request_logger = FakeLogger()
    monkeypatch.setattr("genai_gateway.runtime.workflows.rag_workflow.get_reranker", lambda reranker_type=None: FakeReranker())

    response = workflow.run(
        request=QueryRequest(question="What does Article 99 say?", task="legal_qa"),
        context=SimpleNamespace(
            task="legal_qa",
            quality_mode="default",
            prompt_version="v1",
            retrieval_mode="hybrid",
            top_k=4,
            reranker_type=None,
        ),
    )

    assert response.guardrails.abstained is True
    assert response.guardrails.evidence_status == "insufficient"
    assert len(response.retrieved_chunks) == 1


def test_in_scope_request_with_matching_article_continues_to_generation(monkeypatch) -> None:
    workflow = RagWorkflow()
    workflow.prompt_manager = FakePromptManager()
    workflow.retrieval_service = FakeRetrievalService(
        [
            {
                "chunk_id": "doc::chunk::0",
                "source": "doc.pdf",
                "content": "Article 12 content",
                "score": 0.5,
                "title": "doc",
                "chunk_index": 0,
                "metadata": {"article_number": "12"},
            }
        ]
    )
    workflow.model_routing_policy = FakeRoutingPolicy()
    workflow.request_logger = FakeLogger()
    monkeypatch.setattr("genai_gateway.runtime.workflows.rag_workflow.get_reranker", lambda reranker_type=None: FakeReranker())
    monkeypatch.setattr("genai_gateway.runtime.workflows.rag_workflow.get_chat_provider", lambda provider_name, model_name: FakeChatProvider())

    response = workflow.run(
        request=QueryRequest(question="What does Article 12 say?", task="legal_qa"),
        context=SimpleNamespace(
            task="legal_qa",
            quality_mode="default",
            prompt_version="v1",
            retrieval_mode="hybrid",
            top_k=4,
            reranker_type=None,
        ),
    )

    assert response.guardrails.abstained is False
    assert response.guardrails.scope_status == "in_scope"
    assert response.guardrails.evidence_status == "sufficient"
    assert response.answer == "generated answer"
