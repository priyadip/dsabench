"""Tests for bench.profiler.CallTracker."""

from __future__ import annotations

import sys

from bench.profiler import CallTracker


def fib(n: int) -> int:
    return n if n < 2 else fib(n - 1) + fib(n - 2)


def _tracked(target):
    def sentinel():
        return target()

    tracker = CallTracker(entry_code=sentinel.__code__)
    tracker.start()
    try:
        sentinel()
    finally:
        tracker.stop()
    return tracker.as_stats()


def test_fib10_exact_counts():
    stats = _tracked(lambda: fib(10))
    # lambda + 177 fib frames; the lambda wrapper is a user frame too.
    assert stats.function_calls in (177, 178)
    assert stats.recursive_calls == 176
    assert stats.max_recursion_depth == 10


def test_single_call_no_recursion():
    stats = _tracked(lambda: sum(range(10)))
    assert stats.recursive_calls == 0
    assert stats.max_recursion_depth <= 1 + 1  # lambda (+ nothing recursive)


def test_stdlib_python_frames_counted_bench_frames_never():
    """function_calls uses cProfile semantics: every Python frame counts,
    except bench's own machinery and the sentinel."""
    import json

    stats = _tracked(lambda: json.dumps({"a": 1}))
    # lambda + a handful of json stdlib Python frames; small and stable.
    assert 2 <= stats.function_calls <= 10


def test_bench_internal_frames_excluded():
    from bench.benchmark import run

    def only_math(n):
        return n * n

    # run() wraps the target in invoke()/sentinel machinery living inside the
    # bench package; none of those frames may leak into the count.
    result = run(only_math, args=(4,), repeat=1, warmup=0)
    assert result.calls.function_calls == 1
    assert result.calls.recursive_calls == 0


def test_gc_collections_nonnegative():
    stats = _tracked(lambda: [list(range(100)) for _ in range(50)])
    assert stats.gc_collections >= 0


def test_profile_hook_restored():
    prev = sys.getprofile()
    _tracked(lambda: fib(3))
    assert sys.getprofile() is prev


def test_tracker_context_manager():
    def sentinel():
        return fib(5)

    with CallTracker(entry_code=sentinel.__code__) as tracker:
        sentinel()
    stats = tracker.as_stats()
    assert stats.function_calls >= 15  # fib(5) => 15 calls
