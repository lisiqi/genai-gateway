"""FastAPI backend for the legal document Q&A example app."""

from fastapi import FastAPI

from apps.legal_doc_qa.backend.schemas import AskRequest, AskResponse
from apps.legal_doc_qa.backend.service import LegalDocQAService


service = LegalDocQAService()
app = FastAPI(
    title="legal_doc_qa backend",
    version="0.1.0",
    description="Example application backend built on top of the genai_gateway runtime.",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Lightweight health endpoint for the example app."""
    return {"status": "ok", "app": "legal_doc_qa"}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """Answer a legal document question using the runtime."""
    result = service.ask(
        question=request.question,
        prompt_version=request.prompt_version,
        top_k=request.top_k,
    )
    return AskResponse(question=request.question, result=result)
