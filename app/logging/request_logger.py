"""Structured request logging."""

import json
from datetime import UTC, datetime
from pathlib import Path

from app.schemas.request_schema import QueryRequest
from app.schemas.response_schema import QueryResponse


class RequestLogger:
    """Writes request/response records to a local JSONL file for the MVP."""

    def __init__(self, log_path: str = "logs/requests.jsonl") -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, request: QueryRequest, response: QueryResponse) -> None:
        """Persist a request record."""
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "request": request.model_dump(),
            "response": response.model_dump(),
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
