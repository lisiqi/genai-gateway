"""Latency measurement helpers."""

from collections.abc import Callable
from time import perf_counter
from typing import Any, TypeVar


T = TypeVar("T")


def measure_latency_ms(fn: Callable[[], T]) -> tuple[Any, ...]:
    """Execute a callable and append `elapsed_ms` to its tuple result."""
    started = perf_counter()
    result = fn()
    elapsed_ms = (perf_counter() - started) * 1000
    if not isinstance(result, tuple):
        raise TypeError("measure_latency_ms expects the wrapped callable to return a tuple")
    return (*result, round(elapsed_ms, 2))
