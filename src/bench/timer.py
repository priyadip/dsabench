"""High-resolution timing primitives.

Wall-clock time uses :func:`time.perf_counter_ns` (monotonic, highest
available resolution). CPU time uses :func:`time.process_time_ns`
(user + system time of the whole process, sleep excluded).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

__all__ = ["wall_ns", "cpu_ns", "measure"]


def wall_ns() -> int:
    """Return the current monotonic wall-clock reading in nanoseconds."""
    return time.perf_counter_ns()


def cpu_ns() -> int:
    """Return the current process CPU-time reading in nanoseconds."""
    return time.process_time_ns()


def measure(
    func: Callable[..., Any],
    args: Sequence[Any] = (),
    kwargs: Mapping[str, Any] | None = None,
) -> tuple[int, int, Any]:
    """Call *func* once and measure its wall and CPU time.

    The CPU clock is sampled outside the wall clock so the wall reading is
    the tightest possible bracket around the call itself.

    Args:
        func: The callable to execute.
        args: Positional arguments for *func*.
        kwargs: Keyword arguments for *func*.

    Returns:
        A ``(wall_ns, cpu_ns, return_value)`` tuple for this single call.
    """
    kw = kwargs or {}
    c0 = time.process_time_ns()
    w0 = time.perf_counter_ns()
    value = func(*args, **kw)
    w1 = time.perf_counter_ns()
    c1 = time.process_time_ns()
    return w1 - w0, c1 - c0, value
