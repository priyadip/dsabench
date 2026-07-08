"""Tests for coroutine, generator, and threaded targets."""

from __future__ import annotations

import asyncio
import threading

import pytest

import bench
from bench import bench_async, run
from bench.exceptions import BenchError


async def _coro(x):
    await asyncio.sleep(0.001)
    return x * 2


def test_bench_awaits_coroutine_outside_loop():
    assert bench.bench(_coro, 5, repeat=2, warmup=0) == 10


def test_run_records_async_timing():
    r = run(_coro, args=(1,), repeat=2, warmup=0)
    assert r.return_value == 2
    assert len(r.timing.runs_ns) == 2
    assert r.calls is None  # documented: no call tracking for async


def test_bench_inside_running_loop_raises():
    async def main():
        with pytest.raises(BenchError):
            bench.bench(_coro, 1, repeat=1, warmup=0)

    asyncio.run(main())


def test_bench_async_inside_loop():
    async def main():
        value = await bench_async(_coro, 21, repeat=2, warmup=0)
        assert value == 42

    asyncio.run(main())


def test_bench_async_rejects_sync_function():
    async def main():
        with pytest.raises(BenchError):
            await bench_async(lambda: 1)

    asyncio.run(main())


def test_bench_async_propagates_exception():
    async def bad():
        raise ValueError("async boom")

    async def main():
        with pytest.raises(ValueError):
            await bench_async(bad, repeat=1, warmup=0)

    asyncio.run(main())


def _squares(n):
    for i in range(n):
        yield i * i


def test_generator_returns_fresh_generator():
    gen = bench.bench(_squares, 4, repeat=2, warmup=0)
    assert list(gen) == [0, 1, 4, 9]


def test_generator_return_repr_counts_items():
    r = run(_squares, args=(4,), repeat=2, warmup=0)
    assert "yielded 4 items per run" in r.return_repr


def test_generator_single_item_grammar():
    r = run(_squares, args=(1,), repeat=1, warmup=0)
    assert "1 item per run" in r.return_repr


def test_threaded_function_benchmarks():
    def spin_threads():
        results = []

        def work():
            results.append(sum(range(2_000)))

        threads = [threading.Thread(target=work) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return len(results)

    assert bench.bench(spin_threads, repeat=1, warmup=0) == 4
