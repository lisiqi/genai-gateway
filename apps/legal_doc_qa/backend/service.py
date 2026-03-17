"""Application service for legal document question answering."""

from genai_gateway.runtime.service import RuntimeService
from genai_gateway.schemas.request_schema import QueryRequest
from genai_gateway.schemas.response_schema import QueryResponse


class LegalDocQAService:
    """Thin adapter over the generic runtime for the legal_qa task."""

    def __init__(self) -> None:
        self.runtime = RuntimeService()

    def ask(self, *, question: str, prompt_version: str = "v1", top_k: int | None = None) -> QueryResponse:
        """Run a legal document QA request through the runtime."""
        request = QueryRequest(
            question=question,
            task="legal_qa",
            prompt_version=prompt_version,
            top_k=top_k,
        )
        return self.runtime.handle_query(request)
