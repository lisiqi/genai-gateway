"""Main request orchestrator for the gateway."""

from app.evaluation.cost import estimate_token_cost
from app.evaluation.groundedness import score_groundedness
from app.evaluation.latency import measure_latency_ms
from app.gateway.model_client import ModelClient
from app.gateway.prompt_manager import PromptManager
from app.gateway.retrieval import RetrievalService
from app.logging.request_logger import RequestLogger
from app.schemas.request_schema import QueryRequest
from app.schemas.response_schema import EvaluationSummary, QueryResponse, RetrievedChunk


class GatewayRouter:
    """Coordinates the request lifecycle described in the README."""

    def __init__(self) -> None:
        self.prompt_manager = PromptManager()
        self.retrieval_service = RetrievalService()
        self.model_client = ModelClient()
        self.request_logger = RequestLogger()

    def handle_query(self, request: QueryRequest) -> QueryResponse:
        """Execute validation, retrieval, generation, logging, and evaluation."""
        prompt_text = self.prompt_manager.load_prompt(
            task=request.task,
            version=request.prompt_version,
        )
        retrieved = self.retrieval_service.retrieve(
            question=request.question,
            task=request.task,
            top_k=request.top_k,
        )
        final_prompt = self.prompt_manager.render_prompt(
            prompt_text=prompt_text,
            question=request.question,
            retrieved_chunks=retrieved,
        )
        answer, usage, latency_ms = measure_latency_ms(
            lambda: self.model_client.generate(
                prompt=final_prompt,
                question=request.question,
            )
        )
        groundedness = score_groundedness(answer=answer, retrieved_chunks=retrieved)
        token_cost = estimate_token_cost(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )
        response = QueryResponse(
            answer=answer,
            task=request.task,
            prompt_version=request.prompt_version,
            model_name=self.model_client.settings.openai_model if self.model_client.client or self.model_client.settings.openai_model else None,
            retrieved_chunks=[RetrievedChunk.model_validate(chunk) for chunk in retrieved],
            latency_ms=latency_ms,
            token_usage=usage,
            evaluation=EvaluationSummary(
                groundedness_score=groundedness,
                estimated_cost_usd=token_cost,
            ),
        )
        self.request_logger.log(request=request, response=response)
        return response
