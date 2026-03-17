"""RAG workflow implementation for the runtime layer."""

from genai_gateway.evaluation.cost import estimate_token_cost
from genai_gateway.evaluation.groundedness import score_groundedness
from genai_gateway.evaluation.latency import measure_latency_ms
from genai_gateway.observability.request_logger import RequestLogger
from genai_gateway.prompts.manager import PromptManager
from genai_gateway.providers.chat import get_chat_provider
from genai_gateway.retrieval.reranker import PassThroughReranker
from genai_gateway.retrieval.retriever import RetrievalService
from genai_gateway.runtime.context import RuntimeContext
from genai_gateway.runtime.policies.model_routing import ModelRoutingPolicy
from genai_gateway.schemas.request_schema import QueryRequest
from genai_gateway.schemas.response_schema import EvaluationSummary, QueryResponse, RetrievedChunk, RoutingSummary


class RagWorkflow:
    """Coordinates the current retrieve -> rerank -> prompt -> generate flow."""

    def __init__(self) -> None:
        self.prompt_manager = PromptManager()
        self.retrieval_service = RetrievalService()
        self.reranker = PassThroughReranker()
        self.model_routing_policy = ModelRoutingPolicy()
        self.request_logger = RequestLogger()

    def run(self, request: QueryRequest, context: RuntimeContext) -> QueryResponse:
        """Execute the RAG workflow."""
        prompt_text = self.prompt_manager.load_prompt(
            task=context.task,
            version=context.prompt_version,
        )
        retrieved = self.retrieval_service.retrieve(
            question=request.question,
            task=context.task,
            top_k=context.top_k,
        )
        reranked = self.reranker.rerank(
            question=request.question,
            chunks=retrieved,
        )
        routing_decision = self.model_routing_policy.select(
            task=context.task,
            quality_mode=context.quality_mode,
            prompt_version=context.prompt_version,
        )
        chat_provider = get_chat_provider(
            provider_name=routing_decision.provider,
            model_name=routing_decision.model,
        )
        final_prompt = self.prompt_manager.render_prompt(
            prompt_text=prompt_text,
            question=request.question,
            retrieved_chunks=reranked,
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
        groundedness = score_groundedness(answer=answer, retrieved_chunks=reranked)
        token_cost = estimate_token_cost(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
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
            evaluation=EvaluationSummary(
                groundedness_score=groundedness,
                estimated_cost_usd=token_cost,
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
