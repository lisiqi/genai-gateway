"""Latency measurement helpers."""

from collections.abc import Callable
from time import perf_counter
from typing import TypeVar


T = TypeVar("T")


def measure_latency_ms(fn: Callable[[], T]) -> tuple[object, object, float]:
    """Execute a callable and return `(value_1, value_2, elapsed_ms)`.

    The wrapped callable is expected to return a two-item tuple.
    """
    started = perf_counter()
    result = fn()
    elapsed_ms = (perf_counter() - started) * 1000
    return result[0], result[1], round(elapsed_ms, 2)
