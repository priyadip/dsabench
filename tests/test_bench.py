"""Behavioral tests for bench.run and bench.bench — the core engine."""

from __future__ import annotations

import pytest

import bench
from bench import run
from bench.types import Mode


def fib(n: int) -> int:
    return n if n < 2 else fib(n - 1) + fib(n - 2)


def test_bench_returns_original_value():
    assert bench.bench(sorted, [3, 1, 2], repeat=2, warmup=0) == [1, 2, 3]


def test_bench_forwards_kwargs():
    assert bench.bench(sorted, [3, 1, 2], reverse=True, repeat=1, warmup=0) == [3, 2, 1]


def test_run_repeat_count_honored():
    r = run(fib, args=(5,), repeat=4, warmup=0)
    assert r.repeat == 4
    assert len(r.timing.runs_ns) == 4


def test_run_warmup_excluded_from_timing():
    calls = {"n": 0}

    def counted():
        calls["n"] += 1
        return calls["n"]

    r = run(counted, repeat=3, warmup=2)
    # 2 warmup + 3 timed + 1 instrumented pass = 6 calls total
    assert calls["n"] == 6
    assert len(r.timing.runs_ns) == 3


def test_fast_mode_single_combined_pass():
    calls = {"n": 0}

    def counted():
        calls["n"] += 1

    r = run(counted, mode="fast")
    assert calls["n"] == 1  # instrumented and timed in one call
    assert r.mode is Mode.FAST
    assert len(r.timing.runs_ns) == 1
    assert r.memory is not None
    assert r.calls is not None


def test_run_populates_all_sections():
    r = run(fib, args=(8,), repeat=2, warmup=0)
    assert r.return_value == 21
    assert r.timing is not None
    assert r.cpu is not None
    assert r.memory is not None
    assert r.calls is not None
    assert r.exception is None
    assert r.ok


def test_run_fib10_deterministic_call_metrics():
    r = run(fib, args=(10,), repeat=1, warmup=0)
    assert r.calls.function_calls == 177
    assert r.calls.recursive_calls == 176
    assert r.calls.max_recursion_depth == 10


def test_run_captures_exception_without_raising():
    def boom():
        raise ValueError("kapow")

    r = run(boom, repeat=1, warmup=0)
    assert not r.ok
    assert r.exception.type_name == "ValueError"
    assert "kapow" in r.exception.message
    assert isinstance(r.raised, ValueError)


def test_bench_reraises_by_default():
    def boom():
        raise KeyError("k")

    with pytest.raises(KeyError):
        bench.bench(boom, repeat=1, warmup=0)


def test_bench_swallow_when_raise_exceptions_disabled():
    bench.configure(raise_exceptions=False)

    def boom():
        raise RuntimeError("silent")

    assert bench.bench(boom, repeat=1, warmup=0) is None


def test_report_prints_expected_sections(capsys):
    bench.configure(quiet=False)
    bench.bench(fib, 6, repeat=2, warmup=0)
    out = capsys.readouterr().out
    for token in (
        "Benchmark Report",
        "fib",
        "Fastest",
        "Average",
        "Median",
        "Peak",
        "CPU",
        "Function calls",
        "Return",
    ):
        assert token in out, f"missing {token!r} in report"


def test_quiet_suppresses_report(capsys):
    bench.bench(fib, 6, repeat=1, warmup=0)  # conftest sets quiet=True
    assert capsys.readouterr().out == ""


def test_label_overrides_name():
    r = run(fib, args=(3,), repeat=1, warmup=0, label="my-fib")
    assert r.name == "my-fib"


def test_lambda_name():
    r = run(lambda: 1, repeat=1, warmup=0)
    assert "lambda" in r.name


def test_mode_string_accepted():
    r = run(fib, args=(3,), mode="accurate", repeat=3, warmup=0)
    assert r.mode is Mode.ACCURATE
    assert r.repeat == 3  # explicit repeat overrides mode default


def test_memory_section_can_be_disabled():
    bench.configure(memory=False)
    r = run(fib, args=(4,), repeat=1, warmup=0)
    assert r.memory is None


def test_profile_section_can_be_disabled():
    bench.configure(profile=False)
    r = run(fib, args=(4,), repeat=2, warmup=0)
    assert r.calls is None


def test_cpu_section_can_be_disabled():
    bench.configure(cpu=False)
    r = run(fib, args=(4,), repeat=2, warmup=0)
    assert r.cpu is None


def test_run_never_prints(capsys):
    bench.configure(quiet=False)
    run(fib, args=(3,), repeat=1, warmup=0)
    assert capsys.readouterr().out == ""


def test_args_repr_recorded():
    r = run(fib, args=(7,), repeat=1, warmup=0)
    assert "7" in r.args_repr


def test_to_dict_round_trip_keys():
    r = run(fib, args=(5,), repeat=2, warmup=0)
    d = r.to_dict()
    assert d["name"] == "fib"
    assert set(d["timing"]) >= {"fastest_ns", "average_ns", "median_ns", "p95_ns"}
    assert d["calls"]["function_calls"] > 0
