"""Call-graph instrumentation used during the instrumented pass.

:class:`CallTracker` installs a :func:`sys.setprofile` hook to count function
calls, recursive calls, and the maximum simultaneous recursion depth reached
while the target executes, plus garbage-collector activity via
:func:`gc.get_stats`.

The tracker supports *arming* on a sentinel code object: counting only begins
once that code object is entered and stops when it returns, so bench's own
plumbing (wrapper functions, context managers) never pollutes the numbers.
"""

from __future__ import annotations

import gc
import os
import sys
from functools import lru_cache
from types import CodeType, FrameType, TracebackType
from typing import Any

from .types import CallStats

__all__ = ["CallTracker"]

_BENCH_DIR = os.path.normcase(os.path.dirname(os.path.abspath(__file__)))


@lru_cache(maxsize=4096)
def _is_bench_file(filename: str) -> bool:
    """Return True when *filename* belongs to the bench package itself."""
    if not filename or filename.startswith("<"):
        return False
    path = os.path.normcase(os.path.abspath(filename))
    return path == _BENCH_DIR or path.startswith(_BENCH_DIR + os.sep)


class CallTracker:
    """Profile-hook based counter of calls, recursion, and GC activity.

    Args:
        entry_code: Optional sentinel code object. When given, counting is
            armed only while a call of that exact code object is on the
            stack; the sentinel itself is not counted.

    Example:
        >>> def fib(n):
        ...     return n if n < 2 else fib(n - 1) + fib(n - 2)
        >>> with CallTracker() as tracker:
        ...     fib(10)
        89
        >>> tracker.function_calls
        177
    """

    __slots__ = (
        "_entry_code",
        "_armed",
        "_entry_depth",
        "_prev_profile",
        "_active_counts",
        "_gc_before",
        "function_calls",
        "recursive_calls",
        "max_recursion_depth",
        "gc_collections",
    )

    def __init__(self, entry_code: CodeType | None = None) -> None:
        self._entry_code = entry_code
        self._armed = entry_code is None
        self._entry_depth = 0
        self._prev_profile: Any = None
        self._active_counts: dict[CodeType, int] = {}
        self._gc_before = 0
        self.function_calls = 0
        self.recursive_calls = 0
        self.max_recursion_depth = 0
        self.gc_collections = 0

    # -- profile hook --------------------------------------------------------
    def _hook(self, frame: FrameType, event: str, arg: Any) -> None:
        code = frame.f_code
        if event == "call":
            if not self._armed:
                if code is self._entry_code:
                    self._armed = True
                    self._entry_depth = 1
                return
            if code is self._entry_code:
                self._entry_depth += 1
                return
            if _is_bench_file(code.co_filename):
                return
            self.function_calls += 1
            depth = self._active_counts.get(code, 0) + 1
            self._active_counts[code] = depth
            if depth > 1:
                self.recursive_calls += 1
            if depth > self.max_recursion_depth:
                self.max_recursion_depth = depth
        elif event == "return":
            if code is self._entry_code and self._armed:
                self._entry_depth -= 1
                if self._entry_depth <= 0:
                    self._armed = False
                return
            if not self._armed:
                return
            if _is_bench_file(code.co_filename):
                return
            depth = self._active_counts.get(code, 0)
            if depth > 1:
                self._active_counts[code] = depth - 1
            elif depth == 1:
                del self._active_counts[code]

    # -- lifecycle ------------------------------------------------------------
    def start(self) -> None:
        """Install the profile hook (saving any previously installed one)."""
        self._gc_before = self._total_gc_collections()
        self._prev_profile = sys.getprofile()
        sys.setprofile(self._hook)

    def stop(self) -> None:
        """Remove the hook, restore the previous one, and finalise GC stats."""
        sys.setprofile(self._prev_profile)
        self._prev_profile = None
        self.gc_collections = max(0, self._total_gc_collections() - self._gc_before)

    def __enter__(self) -> CallTracker:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.stop()

    # -- helpers ---------------------------------------------------------------
    @staticmethod
    def _total_gc_collections() -> int:
        return sum(int(stat.get("collections", 0)) for stat in gc.get_stats())

    def as_stats(self) -> CallStats:
        """Return the collected counters as a :class:`bench.types.CallStats`."""
        return CallStats(
            function_calls=self.function_calls,
            recursive_calls=self.recursive_calls,
            max_recursion_depth=self.max_recursion_depth,
            gc_collections=self.gc_collections,
        )
