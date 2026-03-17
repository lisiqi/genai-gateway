"""Lightweight runtime tracing helpers."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any, TypeVar


T = TypeVar("T")


class TraceRecorder:
    """Collect stage-level timing events for one request."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def record(self, *, stage: str, duration_ms: float, metadata: dict[str, Any] | None = None) -> None:
        """Append one trace event."""
        self._events.append(
            {
                "stage": stage,
                "duration_ms": round(duration_ms, 2),
                "metadata": metadata or {},
            }
        )

    def measure(
        self,
        stage: str,
        fn: Callable[[], T],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[T, float]:
        """Measure one stage and record the event."""
        started = perf_counter()
        result = fn()
        duration_ms = (perf_counter() - started) * 1000
        self.record(stage=stage, duration_ms=duration_ms, metadata=metadata)
        return result, round(duration_ms, 2)

    def as_list(self) -> list[dict[str, Any]]:
        """Return the collected trace events."""
        return list(self._events)
