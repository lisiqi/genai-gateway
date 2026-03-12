"""FastAPI entrypoint for the GenAI gateway."""

from fastapi import FastAPI

from app.api.query import router as query_router
from app.config.settings import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Gateway-first RAG service for legal question answering.",
)
app.include_router(query_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Lightweight health endpoint for local development."""
    return {"status": "ok", "environment": settings.app_env}
