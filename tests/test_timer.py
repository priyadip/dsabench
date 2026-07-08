"""Unit tests for bench.timer — clock primitives."""

from __future__ import annotations

import time

from bench.timer import cpu_ns, measure, wall_ns


def test_wall_ns_monotonic_increasing():
    a = wall_ns()
    b = wall_ns()
    assert isinstance(a, int)
    assert b >= a


def test_cpu_ns_is_int():
    assert isinstance(cpu_ns(), int)


def test_measure_returns_wall_cpu_value():
    wall, cpu, value = measure(lambda: 41 + 1)
    assert value == 42
    assert isinstance(wall, int) and wall >= 0
    assert isinstance(cpu, int) and cpu >= 0


def test_measure_wall_reflects_sleep():
    wall, cpu, _ = measure(lambda: time.sleep(0.005))
    assert wall >= 4_000_000  # at least ~4 ms in ns
    # sleeping burns almost no CPU time
    assert cpu < wall


def test_measure_propagates_exception():
    def boom():
        raise RuntimeError("x")

    try:
        measure(boom)
    except RuntimeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected RuntimeError")
