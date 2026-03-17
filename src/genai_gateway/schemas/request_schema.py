"""Request models for gateway queries."""

from pydantic import BaseModel, Field

from genai_gateway.config.settings import get_settings


settings = get_settings()


class QueryRequest(BaseModel):
    """Schema for the `/query` endpoint."""

    question: str = Field(min_length=1, description="The user question to answer.")
    task: str = Field(default=settings.default_task, description="Logical application task name.")
    quality_mode: str = Field(
        default="default",
        description="Routing quality mode such as default or high_quality.",
    )
    prompt_version: str = Field(
        default=settings.default_prompt_version,
        description="Prompt version identifier for the selected task.",
    )
    top_k: int | None = Field(default=None, ge=1, le=20, description="Override retrieval result count.")
