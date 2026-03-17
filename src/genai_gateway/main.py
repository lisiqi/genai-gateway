"""FastAPI entrypoint for the orchestration runtime."""

from fastapi import FastAPI

from genai_gateway.api.query import router as query_router
from genai_gateway.config.settings import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Lightweight orchestration runtime for GenAI workflows.",
)
app.include_router(query_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Lightweight health endpoint for local development."""
    return {"status": "ok", "environment": settings.app_env}
