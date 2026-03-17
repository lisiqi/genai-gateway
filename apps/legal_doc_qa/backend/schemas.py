"""Application-facing schemas for the legal document Q&A backend."""

from pydantic import BaseModel, Field

from genai_gateway.schemas.response_schema import QueryResponse


class AskRequest(BaseModel):
    """Request body accepted by the legal document Q&A backend."""

    question: str = Field(min_length=1)
    quality_mode: str = Field(default="default")
    prompt_version: str = Field(default="v1")
    top_k: int | None = Field(default=None, ge=1, le=20)


class AskResponse(BaseModel):
    """Application response returned by the legal document Q&A backend."""

    question: str
    result: QueryResponse
