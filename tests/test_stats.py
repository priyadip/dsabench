"""Unit tests for bench.stats — pure statistics helpers."""

from __future__ import annotations

import statistics

import pytest

from bench.stats import mean, median, percentile, stdev


@pytest.mark.parametrize(
    ("data", "expected"),
    [([1.0], 1.0), ([1.0, 2.0, 3.0], 2.0), ([2.0, 4.0], 3.0), ([5.0, 5.0, 5.0], 5.0)],
)
def test_mean(data, expected):
    assert mean(data) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("data", "expected"),
    [([1.0], 1.0), ([3.0, 1.0, 2.0], 2.0), ([1.0, 2.0, 3.0, 4.0], 2.5), ([9.0, 1.0], 5.0)],
)
def test_median(data, expected):
    assert median(data) == pytest.approx(expected)


def test_stdev_matches_stdlib():
    data = [12.0, 15.0, 9.0, 21.0, 18.0]
    assert stdev(data) == pytest.approx(statistics.stdev(data))


def test_stdev_single_value_is_zero():
    assert stdev([42.0]) == 0.0


@pytest.mark.parametrize(
    ("pct", "expected"),
    [(0, 1.0), (25, 2.0), (50, 3.0), (75, 4.0), (100, 5.0), (95, 4.8), (10, 1.4)],
)
def test_percentile_linear_interpolation(pct, expected):
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert percentile(data, pct) == pytest.approx(expected)


def test_percentile_single_element():
    assert percentile([7.0], 95) == 7.0


def test_percentile_unsorted_input():
    assert percentile([5.0, 1.0, 3.0], 50) == pytest.approx(3.0)


@pytest.mark.parametrize("func", [mean, median, stdev])
def test_empty_sequences_raise(func):
    with pytest.raises(ValueError):
        func([])


def test_percentile_empty_raises():
    with pytest.raises(ValueError):
        percentile([], 50)


@pytest.mark.parametrize("bad_pct", [-1, 100.5, 200])
def test_percentile_out_of_range_raises(bad_pct):
    with pytest.raises(ValueError):
        percentile([1.0, 2.0], bad_pct)
