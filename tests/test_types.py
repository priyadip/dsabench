"""Unit tests for bench.types — dataclasses and conversions."""

from __future__ import annotations

import pytest

from bench.exceptions import ConfigurationError
from bench.types import (
    BenchmarkResult,
    ExceptionInfo,
    Mode,
    TimingStats,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("fast", Mode.FAST), ("DEFAULT", Mode.DEFAULT), (Mode.ACCURATE, Mode.ACCURATE)],
)
def test_mode_from_value(value, expected):
    assert Mode.from_value(value) is expected


def test_mode_from_value_invalid():
    with pytest.raises(ConfigurationError):
        Mode.from_value("bogus")


def test_timing_stats_from_runs():
    ts = TimingStats.from_runs([100, 300, 200])
    assert ts.fastest_ns == 100
    assert ts.slowest_ns == 300
    assert ts.average_ns == pytest.approx(200.0)
    assert ts.median_ns == pytest.approx(200.0)
    assert ts.total_ns == pytest.approx(600.0)
    assert ts.runs_ns == (100, 300, 200)


def test_timing_stats_unit_properties():
    ts = TimingStats.from_runs([2_000_000])  # 2 ms
    assert ts.fastest_us == pytest.approx(2000.0)
    assert ts.fastest_ms == pytest.approx(2.0)
    assert ts.average_ms == pytest.approx(2.0)
    assert ts.average_s == pytest.approx(0.002)


def test_timing_stats_empty_raises():
    with pytest.raises(ValueError):
        TimingStats.from_runs([])


def test_exception_info_from_exception():
    try:
        raise ValueError("boom")
    except ValueError as exc:
        info = ExceptionInfo.from_exception(exc)
    assert info.type_name == "ValueError"
    assert "boom" in info.message
    assert "ValueError" in info.traceback


def test_benchmark_result_to_dict_shape():
    ts = TimingStats.from_runs([1000, 2000])
    result = BenchmarkResult(
        name="f",
        mode=Mode.DEFAULT,
        repeat=2,
        warmup=0,
        return_value=42,
        return_repr="42",
        args_repr="()",
        timing=ts,
    )
    d = result.to_dict()
    assert d["name"] == "f"
    assert d["mode"] == "default"
    assert d["timing"]["average_ns"] == pytest.approx(1500.0)
    assert "return_value" not in d  # raw object excluded
    assert "raised" not in d
    assert d["return_repr"] == "42"


def test_benchmark_result_delegation_none_safe():
    result = BenchmarkResult(
        name="f",
        mode=Mode.FAST,
        repeat=1,
        warmup=0,
        return_value=None,
        return_repr="—",
        args_repr="()",
    )
    assert result.average_ms is None
    assert result.fastest_ns is None
    assert result.peak_memory_bytes is None
    assert result.ok  # no exception recorded
