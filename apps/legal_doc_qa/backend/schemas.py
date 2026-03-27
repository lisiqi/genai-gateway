"""Application-facing schemas for the legal document Q&A backend."""

from pydantic import BaseModel, Field

from genai_gateway.runtime.agent import AgentExecutionReport
from genai_gateway.schemas.response_schema import QueryResponse


class AskRequest(BaseModel):
    """Request body accepted by the legal document Q&A backend."""

    question: str = Field(min_length=1)
    quality_mode: str = Field(default="default")
    prompt_version: str = Field(default="v1")
    retrieval_mode: str | None = Field(default=None)
    top_k: int | None = Field(default=None, ge=1, le=20)
    reranker_type: str | None = Field(default=None)


class AskResponse(BaseModel):
    """Application response returned by the legal document Q&A backend."""

    question: str
    result: QueryResponse


class AgentRunRequest(BaseModel):
    """Request body accepted by the controlled agent runtime endpoint."""

    instruction: str = Field(
        default="Answer the question from the legal corpus and draft a follow-up email.",
        min_length=1,
    )
    question: str = Field(min_length=1)
    recipient_email: str | None = Field(default=None)
    quality_mode: str = Field(default="default")
    prompt_version: str = Field(default="v1")
    retrieval_mode: str | None = Field(default=None)
    top_k: int | None = Field(default=None, ge=1, le=20)
    reranker_type: str | None = Field(default=None)


class AgentRunResponse(BaseModel):
    """Response returned by the controlled agent runtime endpoint."""

    result: AgentExecutionReport
