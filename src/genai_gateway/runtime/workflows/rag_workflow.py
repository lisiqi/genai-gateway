"""RAG workflow implementation for the runtime layer."""

from genai_gateway.config.settings import get_settings
from genai_gateway.evaluation.latency import measure_latency_ms
from genai_gateway.evaluation.pricing import compute_request_cost
from genai_gateway.evaluation.response import (
    score_answer_relevance,
    score_citation_presence,
    score_completeness,
    score_groundedness,
)
from genai_gateway.observability.request_logger import RequestLogger
from genai_gateway.observability.tracing import TraceRecorder
from genai_gateway.prompts.manager import PromptManager
from genai_gateway.providers.chat import get_chat_provider
from genai_gateway.retrieval.reranker import get_reranker
from genai_gateway.retrieval.retriever import RetrievalService
from genai_gateway.runtime.guardrails import assess_retrieval_evidence, classify_request_scope
from genai_gateway.runtime.context import RuntimeContext
from genai_gateway.runtime.policies.model_routing import ModelRoutingPolicy
from genai_gateway.schemas.request_schema import QueryRequest
from genai_gateway.schemas.response_schema import (
    EvaluationSummary,
    GuardrailSummary,
    QueryResponse,
    RetrievedChunk,
    RerankingSummary,
    RoutingSummary,
    TraceEvent,
    TraceSummary,
)


class RagWorkflow:
    """Coordinates the current retrieve -> rerank -> prompt -> generate flow."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.prompt_manager = PromptManager()
        self.retrieval_service = RetrievalService()
        self.model_routing_policy = ModelRoutingPolicy()
        self.request_logger = RequestLogger()

    def run(self, request: QueryRequest, context: RuntimeContext) -> QueryResponse:
        """Execute the RAG workflow."""
        tracer = TraceRecorder()
        reranker = get_reranker(reranker_type=context.reranker_type)
        if self.settings.guardrails_enabled:
            scope_decision, _ = tracer.measure(
                "guardrail.scope",
                lambda: classify_request_scope(question=request.question, task=context.task),
                metadata={"task": context.task},
            )
            if scope_decision.status != "in_scope":
                response = self._build_abstention_response(
                    context=context,
                    tracer=tracer,
                    answer=(
                        "This assistant only answers questions grounded in the ingested legal document. "
                        "Ask about the Digital Services Act or a specific article, clause, or legal concept in the corpus."
                    ),
                    reranker=reranker,
                    scope_status=scope_decision.status,
                    evidence_status=None,
                    reason=scope_decision.reason,
                )
                self.request_logger.log(request=request, response=response)
                return response

        prompt_text, _ = tracer.measure(
            "prompt.load",
            lambda: self.prompt_manager.load_prompt(
                task=context.task,
                version=context.prompt_version,
            ),
            metadata={"task": context.task, "prompt_version": context.prompt_version},
        )
        retrieved, _ = tracer.measure(
            "retrieval.search",
            lambda: self.retrieval_service.retrieve(
                question=request.question,
                task=context.task,
                retrieval_mode=context.retrieval_mode,
                top_k=context.top_k,
            ),
            metadata={
                "top_k": context.top_k,
                "retrieval_mode": self.retrieval_service.resolve_retrieval_mode(context.retrieval_mode),
            },
        )
        reranked, _ = tracer.measure(
            "retrieval.rerank",
            lambda: reranker.rerank(
                question=request.question,
                chunks=retrieved,
            ),
            metadata={
                "retrieved_count": len(retrieved),
                "reranker_type": reranker.config_summary["reranker_type"],
            },
        )
        if self.settings.guardrails_enabled:
            evidence_decision, _ = tracer.measure(
                "guardrail.evidence",
                lambda: assess_retrieval_evidence(question=request.question, retrieved_chunks=reranked),
                metadata={"retrieved_count": len(reranked)},
            )
            if evidence_decision.status != "sufficient":
                response = self._build_abstention_response(
                    context=context,
                    tracer=tracer,
                    answer=(
                        "I can't answer that confidently from the retrieved sections of this legal document. "
                        "Try naming the relevant article, clause, or concept more explicitly."
                    ),
                    reranker=reranker,
                    scope_status="in_scope",
                    evidence_status=evidence_decision.status,
                    reason=evidence_decision.reason,
                    retrieved_chunks=reranked,
                )
                self.request_logger.log(request=request, response=response)
                return response
        routing_decision, _ = tracer.measure(
            "routing.select",
            lambda: self.model_routing_policy.select(
                task=context.task,
                quality_mode=context.quality_mode,
                prompt_version=context.prompt_version,
            ),
            metadata={"quality_mode": context.quality_mode},
        )
        chat_provider = get_chat_provider(
            provider_name=routing_decision.provider,
            model_name=routing_decision.model,
        )
        final_prompt, _ = tracer.measure(
            "prompt.render",
            lambda: self.prompt_manager.render_prompt(
                prompt_text=prompt_text,
                question=request.question,
                retrieved_chunks=reranked,
            ),
            metadata={"reranked_count": len(reranked)},
        )
        selected_provider = routing_decision.provider
        selected_model = routing_decision.model
        fallback_used = False
        try:
            answer, usage, latency_ms = measure_latency_ms(
                lambda: chat_provider.generate(
                    prompt=final_prompt,
                    question=request.question,
                )
            )
            tracer.record(
                stage="generation.primary",
                duration_ms=latency_ms,
                metadata={"provider": selected_provider, "model": selected_model},
            )
        except Exception:
            if not routing_decision.fallback_provider:
                raise
            fallback_used = True
            selected_provider = routing_decision.fallback_provider
            selected_model = routing_decision.fallback_model or routing_decision.model
            fallback_provider = get_chat_provider(
                provider_name=selected_provider,
                model_name=selected_model,
            )
            answer, usage, latency_ms = measure_latency_ms(
                lambda: fallback_provider.generate(
                    prompt=final_prompt,
                    question=request.question,
                )
            )
            tracer.record(
                stage="generation.fallback",
                duration_ms=latency_ms,
                metadata={"provider": selected_provider, "model": selected_model},
            )
        groundedness, _ = tracer.measure(
            "evaluation.groundedness",
            lambda: score_groundedness(answer=answer, retrieved_chunks=reranked),
        )
        answer_relevance, _ = tracer.measure(
            "evaluation.answer_relevance",
            lambda: score_answer_relevance(question=request.question, answer=answer),
        )
        citation_score, _ = tracer.measure(
            "evaluation.citation",
            lambda: score_citation_presence(answer=answer),
        )
        completeness_score, _ = tracer.measure(
            "evaluation.completeness",
            lambda: score_completeness(answer=answer, retrieved_chunks=reranked),
        )
        cost_breakdown, _ = tracer.measure(
            "evaluation.cost",
            lambda: compute_request_cost(
                provider=selected_provider,
                model=selected_model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            ),
            metadata={"provider": selected_provider, "model": selected_model},
        )
        tracer.record(
            stage="request.summary",
            duration_ms=latency_ms,
            metadata={
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            },
        )
        response = QueryResponse(
            answer=answer,
            task=context.task,
            quality_mode=context.quality_mode,
            prompt_version=context.prompt_version,
            model_name=selected_model,
            retrieved_chunks=[RetrievedChunk.model_validate(chunk) for chunk in reranked],
            latency_ms=latency_ms,
            token_usage=usage,
            routing=RoutingSummary(
                selected_provider=selected_provider,
                selected_model=selected_model,
                fallback_used=fallback_used,
                fallback_provider=routing_decision.fallback_provider,
                fallback_model=routing_decision.fallback_model,
                reason=routing_decision.reason,
            ),
            reranking=RerankingSummary(**reranker.config_summary),
            guardrails=GuardrailSummary(
                scope_status="in_scope",
                evidence_status="sufficient",
                abstained=False,
                reason=None,
            ),
            trace=TraceSummary(
                events=[TraceEvent.model_validate(event) for event in tracer.as_list()],
            ),
            evaluation=EvaluationSummary(
                groundedness_score=groundedness,
                answer_relevance_score=answer_relevance,
                citation_score=citation_score,
                completeness_score=completeness_score,
                estimated_cost_usd=cost_breakdown.total_cost_usd,
                input_cost_usd=cost_breakdown.input_cost_usd,
                output_cost_usd=cost_breakdown.output_cost_usd,
                pricing_source=cost_breakdown.pricing_source,
                cost_is_estimated=cost_breakdown.is_estimated,
                routing_notes=(
                    f"Fallback used: {routing_decision.provider}/{routing_decision.model} -> "
                    f"{selected_provider}/{selected_model}"
                    if fallback_used
                    else None
                ),
            ),
        )
        self.request_logger.log(request=request, response=response)
        return response

    def _build_abstention_response(
        self,
        *,
        context: RuntimeContext,
        tracer: TraceRecorder,
        answer: str,
        reranker,
        scope_status: str,
        evidence_status: str | None,
        reason: str,
        retrieved_chunks: list[dict] | None = None,
    ) -> QueryResponse:
        """Build a controlled abstention response for guardrail blocks."""
        return QueryResponse(
            answer=answer,
            task=context.task,
            quality_mode=context.quality_mode,
            prompt_version=context.prompt_version,
            model_name=None,
            retrieved_chunks=[RetrievedChunk.model_validate(chunk) for chunk in (retrieved_chunks or [])],
            latency_ms=0.0,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            routing=RoutingSummary(
                selected_provider="guardrail",
                selected_model="guardrail",
                fallback_used=False,
                fallback_provider=None,
                fallback_model=None,
                reason=reason,
            ),
            reranking=RerankingSummary(**reranker.config_summary),
            guardrails=GuardrailSummary(
                scope_status=scope_status,
                evidence_status=evidence_status,
                abstained=True,
                reason=reason,
            ),
            trace=TraceSummary(events=[TraceEvent.model_validate(event) for event in tracer.as_list()]),
            evaluation=EvaluationSummary(
                groundedness_score=0.0,
                answer_relevance_score=0.0,
                citation_score=0.0,
                completeness_score=0.0,
                estimated_cost_usd=0.0,
                input_cost_usd=0.0,
                output_cost_usd=0.0,
                pricing_source=None,
                cost_is_estimated=True,
                routing_notes=reason,
            ),
        )
