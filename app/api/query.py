"""Gateway query endpoint."""

from fastapi import APIRouter

from app.gateway.router import GatewayRouter
from app.schemas.request_schema import QueryRequest
from app.schemas.response_schema import QueryResponse


router = APIRouter()
gateway_router = GatewayRouter()


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    """Handle a single gateway request."""
    return gateway_router.handle_query(request)
