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
    answer_relevance_score: float
    citation_score: float
    completeness_score: float
    estimated_cost_usd: float
    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    pricing_source: str | None = None
    cost_is_estimated: bool = True
    routing_notes: str | None = None


class RoutingSummary(BaseModel):
    """Routing details for the selected and fallback model path."""

    selected_provider: str
    selected_model: str
    fallback_used: bool = False
    fallback_provider: str | None = None
    fallback_model: str | None = None
    reason: str | None = None


class TraceEvent(BaseModel):
    """One stage-level trace event."""

    stage: str
    duration_ms: float
    metadata: dict = Field(default_factory=dict)


class TraceSummary(BaseModel):
    """Trace events collected during one request."""

    events: list[TraceEvent] = Field(default_factory=list)


class QueryResponse(BaseModel):
    """Schema returned by the `/query` endpoint."""

    answer: str
    task: str
    quality_mode: str
    prompt_version: str
    model_name: str | None = None
    retrieved_chunks: list[RetrievedChunk]
    latency_ms: float
    token_usage: TokenUsage
    routing: RoutingSummary
    trace: TraceSummary
    evaluation: EvaluationSummary
