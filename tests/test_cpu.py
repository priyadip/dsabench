"""Unit tests for bench.cpu — CPU stats helpers."""

from __future__ import annotations

import pytest

from bench.cpu import build_cpu_stats, cpu_percent


def test_cpu_percent_basic():
    assert cpu_percent(wall_total_ns=100, cpu_total_ns=50) == pytest.approx(50.0)


def test_cpu_percent_can_exceed_100_with_threads():
    assert cpu_percent(wall_total_ns=100, cpu_total_ns=250) == pytest.approx(250.0)


@pytest.mark.parametrize("wall", [0, -5])
def test_cpu_percent_guards_nonpositive_wall(wall):
    assert cpu_percent(wall_total_ns=wall, cpu_total_ns=100) == 0.0


def test_build_cpu_stats_fields():
    stats = build_cpu_stats(wall_runs_ns=[100, 100], cpu_runs_ns=[50, 70])
    assert stats.cpu_runs_ns == (50, 70)
    assert stats.average_cpu_ns == pytest.approx(60.0)
    assert stats.cpu_percent == pytest.approx(60.0)


def test_build_cpu_stats_to_dict():
    stats = build_cpu_stats([10], [10])
    d = stats.to_dict()
    assert d["cpu_percent"] == pytest.approx(100.0)
    assert "average_cpu_ns" in d
