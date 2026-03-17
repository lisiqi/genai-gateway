"""Response models for gateway queries."""

from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """Chunk returned by retrieval."""

    chunk_id: str
    source: str
    content: str
    score: float | None = None
    title: str | None = None
    chunk_index: int | None = None
    metadata: dict = Field(default_factory=dict)


class TokenUsage(BaseModel):
    """Token accounting for a model request."""

    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)


class EvaluationSummary(BaseModel):
    """Evaluation metrics captured for a request."""

    groundedness_score: float
    estimated_cost_usd: float


class QueryResponse(BaseModel):
    """Schema returned by the `/query` endpoint."""

    answer: str
    task: str
    prompt_version: str
    model_name: str | None = None
    retrieved_chunks: list[RetrievedChunk]
    latency_ms: float
    token_usage: TokenUsage
    evaluation: EvaluationSummary
