"""Runtime query endpoint."""

from fastapi import APIRouter

from genai_gateway.runtime.service import RuntimeService
from genai_gateway.schemas.request_schema import QueryRequest
from genai_gateway.schemas.response_schema import QueryResponse


router = APIRouter()
runtime_service = RuntimeService()


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    """Handle a single runtime request."""
    return runtime_service.handle_query(request)
