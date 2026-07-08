"""Tests for the @benchmark decorator."""

from __future__ import annotations

import asyncio

import pytest

import bench
from bench import benchmark


def test_bare_decorator_passthrough():
    @benchmark
    def double(x):
        return 2 * x

    assert double(21) == 42


def test_parameterized_decorator():
    @benchmark(repeat=3, warmup=0, label="tri")
    def triple(x):
        return 3 * x

    assert triple(3) == 9
    assert triple.last_result.repeat == 3
    assert triple.last_result.name == "tri"


def test_wraps_preserves_metadata():
    @benchmark
    def documented(x):
        """Docstring survives."""
        return x

    assert documented.__name__ == "documented"
    assert "survives" in documented.__doc__
    assert documented.__wrapped__ is documented.original


def test_recursive_decorated_single_report(capsys):
    bench.configure(quiet=False)

    @benchmark(repeat=1, warmup=0)
    def rfib(n):
        return n if n < 2 else rfib(n - 1) + rfib(n - 2)

    assert rfib(6) == 8
    out = capsys.readouterr().out
    assert out.count("Benchmark Report") == 1


def test_recursion_metrics_correct_through_decorator():
    @benchmark(repeat=1, warmup=0)
    def rfib(n):
        return n if n < 2 else rfib(n - 1) + rfib(n - 2)

    rfib(10)
    calls = rfib.last_result.calls
    assert calls.function_calls == 177
    assert calls.max_recursion_depth == 10


def test_nested_decorated_functions_one_report_each_outer_call(capsys):
    bench.configure(quiet=False)

    @benchmark(repeat=1, warmup=0)
    def inner(x):
        return x + 1

    @benchmark(repeat=1, warmup=0)
    def outer(x):
        return inner(x) * 2

    assert outer(1) == 4
    out = capsys.readouterr().out
    assert out.count("Benchmark Report") == 1  # inner runs un-instrumented


def test_last_result_updates_per_call():
    @benchmark(repeat=1, warmup=0)
    def echo(x):
        return x

    echo(1)
    first = echo.last_result
    echo(2)
    assert echo.last_result is not first
    assert echo.last_result.return_value == 2


def test_decorator_reraises_exceptions():
    @benchmark(repeat=1, warmup=0)
    def boom():
        raise ValueError("d")

    with pytest.raises(ValueError):
        boom()
    assert boom.last_result.exception.type_name == "ValueError"


def test_async_decorated_function():
    @benchmark(repeat=2, warmup=0)
    async def acc(x):
        await asyncio.sleep(0.001)
        return x + 1

    assert asyncio.run(acc(41)) == 42
    assert acc.last_result.timing is not None
    assert len(acc.last_result.timing.runs_ns) == 2


def test_original_is_unwrapped():
    @benchmark
    def plain(x):
        return x

    assert plain.original(5) == 5  # runs without benchmarking machinery
