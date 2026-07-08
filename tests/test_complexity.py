"""Tests for bench.estimate_complexity — empirical Big-O fitting."""

from __future__ import annotations

import math
import time

import pytest

import bench
from bench.complexity import (
    COMPLEXITY_MODELS,
    compose,
    const,
    exp_base,
    factorial,
    loglog,
    poly,
    polylog,
    raised,
)
from bench.exceptions import BenchError


def test_result_shape():
    res = bench.estimate_complexity(
        lambda n: sum(range(n)), sizes=[50, 100, 200], repeat=1, warmup=0
    )
    assert res.sizes == (50, 100, 200)
    assert len(res.times_ns) == 3
    assert len(res.fits) == 10  # all viable candidate models scored (n! overflows at 200!)
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
    assert isinstance(d["fits"], list) and len(d["fits"]) == 11


def test_exponential_sleep_identified_as_exponential():
    def exponential(n):
        time.sleep(0.0005 * (2**n))

    res = bench.estimate_complexity(exponential, sizes=[4, 6, 8, 10], repeat=1, warmup=0)
    assert res.best.label == "O(2ⁿ)"
    assert res.best.r_squared > 0.95


def test_factorial_sleep_identified_as_factorial():
    def combinatorial(n):
        time.sleep(0.0002 * math.factorial(n))

    res = bench.estimate_complexity(combinatorial, sizes=[3, 4, 5, 6], repeat=1, warmup=0)
    assert res.best.label == "O(n!)"
    assert res.best.r_squared > 0.95


def test_models_parameter_restricts_candidates():
    def quadratic(n):
        time.sleep(0.0002 * n * n)

    res = bench.estimate_complexity(
        quadratic,
        sizes=[10, 20, 40],
        repeat=1,
        warmup=0,
        models=[("O(n)", poly(1)), ("O(n²)", poly(2))],
    )
    assert len(res.fits) == 2
    assert res.best.label == "O(n²)"


def test_models_all_overflow_raises():
    with pytest.raises(BenchError):
        bench.estimate_complexity(
            lambda n: n,
            sizes=[100, 200, 300],
            repeat=1,
            warmup=0,
            models=[("way too big", lambda n: math.exp(n**5))],
        )


def test_complexity_models_extend_with_plus():
    custom = COMPLEXITY_MODELS + [("O(n⁴log²n)", polylog(4, 2))]
    assert len(custom) == len(COMPLEXITY_MODELS) + 1
    assert custom[-1][0] == "O(n⁴log²n)"


def test_builder_const():
    f = const(7.0)
    assert f(1) == 7.0
    assert f(1000) == 7.0


def test_builder_poly():
    assert poly(2)(4.0) == 16.0
    assert poly(0.5)(4.0) == 2.0


def test_builder_polylog():
    f = polylog(2, 1)
    assert f(1) == 1.0  # guarded: n <= 1 drops the log factor
    assert f(4) == pytest.approx(4.0**2 * math.log2(4.0))


def test_builder_loglog():
    f = loglog()
    assert f(2) == 1.0  # guarded: n <= 2
    assert f(16) == pytest.approx(math.log2(math.log2(16.0)))


def test_builder_exp_base():
    assert exp_base(2.0)(10) == 2.0**10
    assert exp_base(3.0)(4) == 81.0


def test_builder_factorial():
    f = factorial()
    assert f(5) == pytest.approx(120.0)
    assert f(0) == pytest.approx(1.0)


def test_builder_compose():
    f = compose(poly(4), polylog(0, 2))
    n = 8.0
    assert f(n) == pytest.approx(n**4 * math.log2(n) ** 2)


def test_builder_raised():
    f = raised(poly(1), const(3.0))
    assert f(5.0) == pytest.approx(5.0**3)
