"""Tests for bench.estimate_complexity — empirical Big-O fitting."""

from __future__ import annotations

import time

import pytest

import bench
from bench.exceptions import BenchError


def test_result_shape():
    res = bench.estimate_complexity(
        lambda n: sum(range(n)), sizes=[50, 100, 200], repeat=1, warmup=0
    )
    assert res.sizes == (50, 100, 200)
    assert len(res.times_ns) == 3
    assert len(res.fits) == 6  # all candidate models scored
    assert res.best is res.fits[0]
    assert 0.0 <= res.best.r_squared <= 1.0


def test_requires_three_distinct_sizes():
    with pytest.raises(BenchError):
        bench.estimate_complexity(lambda n: n, sizes=[10, 10, 10], repeat=1, warmup=0)
    with pytest.raises(BenchError):
        bench.estimate_complexity(lambda n: n, sizes=[10, 20], repeat=1, warmup=0)


def test_sizes_must_be_positive():
    with pytest.raises(BenchError):
        bench.estimate_complexity(lambda n: n, sizes=[0, 1, 2], repeat=1, warmup=0)


def test_linear_sleep_identified_as_linear():
    def linear(n):
        time.sleep(0.004 * n)

    res = bench.estimate_complexity(linear, sizes=[1, 2, 4], repeat=1, warmup=0)
    assert res.best.label in {"O(n)", "O(n log n)"}
    assert res.best.r_squared > 0.95


def test_constant_work_identified_as_constant():
    def constant(_n):
        time.sleep(0.003)

    res = bench.estimate_complexity(constant, sizes=[1, 4, 16], repeat=1, warmup=0)
    assert res.best.label == "O(1)"


def test_args_for_custom_mapping():
    seen = []

    def takes_list(xs):
        seen.append(len(xs))
        return len(xs)

    bench.estimate_complexity(
        takes_list,
        sizes=[3, 6, 9],
        args_for=lambda n: ([0] * n,),
        repeat=1,
        warmup=0,
    )
    assert set(seen) >= {3, 6, 9}


def test_prints_estimate(capsys):
    bench.configure(quiet=False)
    bench.estimate_complexity(lambda n: sum(range(n)), sizes=[10, 20, 40], repeat=1, warmup=0)
    out = capsys.readouterr().out
    assert "Estimated complexity" in out
    assert "O(" in out


def test_to_dict():
    res = bench.estimate_complexity(lambda n: sum(range(n)), sizes=[10, 20, 40], repeat=1, warmup=0)
    d = res.to_dict()
    assert d["sizes"] == [10, 20, 40]
    assert isinstance(d["fits"], list) and len(d["fits"]) == 6
