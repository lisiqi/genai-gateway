"""Application service for legal document question answering."""

from genai_gateway.runtime.agent import AgentExecutionReport, AgentTaskRequest
from genai_gateway.runtime.service import RuntimeService
from genai_gateway.schemas.request_schema import QueryRequest
from genai_gateway.schemas.response_schema import QueryResponse


class LegalDocQAService:
    """Thin adapter over the generic runtime for the legal_qa task."""

    def __init__(self) -> None:
        self.runtime = RuntimeService()

    def ask(
        self,
        *,
        question: str,
        quality_mode: str = "default",
        prompt_version: str = "v1",
        retrieval_mode: str | None = None,
        top_k: int | None = None,
        reranker_type: str | None = None,
    ) -> QueryResponse:
        """Run a legal document QA request through the runtime."""
        request = QueryRequest(
            question=question,
            task="legal_qa",
            quality_mode=quality_mode,
            prompt_version=prompt_version,
            retrieval_mode=retrieval_mode,
            top_k=top_k,
            reranker_type=reranker_type,
        )
        return self.runtime.handle_query(request)

    def run_agent_task(
        self,
        *,
        instruction: str,
        question: str,
        recipient_email: str | None = None,
        quality_mode: str = "default",
        prompt_version: str = "v1",
        retrieval_mode: str | None = None,
        top_k: int | None = None,
        reranker_type: str | None = None,
    ) -> AgentExecutionReport:
        """Run the Phase 1 controlled agent workflow for legal QA."""
        request = AgentTaskRequest(
            instruction=instruction,
            question=question,
            task="legal_qa",
            recipient_email=recipient_email,
            quality_mode=quality_mode,
            prompt_version=prompt_version,
            retrieval_mode=retrieval_mode,
            top_k=top_k,
            reranker_type=reranker_type,
        )
        return self.runtime.run_agent_task(request)
