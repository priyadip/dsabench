"""Small, dependency-free statistics helpers used across the package.

These functions intentionally mirror the semantics of the standard
:mod:`statistics` module but with two practical differences:

* ``stdev`` returns ``0.0`` (instead of raising) for fewer than two samples,
  which is the sensible value for a single benchmark run.
* ``percentile`` implements linear interpolation between closest ranks,
  matching the behaviour of ``numpy.percentile(..., method="linear")``
  without requiring NumPy.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

__all__ = ["mean", "median", "stdev", "percentile"]


def _require_data(data: Sequence[float], name: str) -> None:
    if len(data) == 0:
        raise ValueError(f"{name}() requires at least one data point")


def mean(data: Sequence[float]) -> float:
    """Return the arithmetic mean of *data*.

    Args:
        data: A non-empty sequence of numbers.

    Returns:
        The arithmetic mean as a float.

    Raises:
        ValueError: If *data* is empty.
    """
    _require_data(data, "mean")
    return math.fsum(data) / len(data)


def median(data: Sequence[float]) -> float:
    """Return the median (middle value) of *data*.

    For an even number of samples the average of the two middle values is
    returned.

    Args:
        data: A non-empty sequence of numbers.

    Returns:
        The median as a float.

    Raises:
        ValueError: If *data* is empty.
    """
    _require_data(data, "median")
    ordered = sorted(data)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def stdev(data: Sequence[float]) -> float:
    """Return the sample standard deviation of *data*.

    Unlike :func:`statistics.stdev`, this returns ``0.0`` when fewer than two
    samples are provided, which is the natural value for a single benchmark
    run.

    Args:
        data: A non-empty sequence of numbers.

    Returns:
        The sample standard deviation as a float.

    Raises:
        ValueError: If *data* is empty.
    """
    _require_data(data, "stdev")
    n = len(data)
    if n < 2:
        return 0.0
    mu = mean(data)
    variance = math.fsum((x - mu) ** 2 for x in data) / (n - 1)
    return math.sqrt(variance)


def percentile(data: Sequence[float], pct: float) -> float:
    """Return the *pct*-th percentile of *data* using linear interpolation.

    Args:
        data: A non-empty sequence of numbers.
        pct: Percentile to compute, between 0 and 100 inclusive.

    Returns:
        The interpolated percentile value as a float.

    Raises:
        ValueError: If *data* is empty or *pct* is outside ``[0, 100]``.
    """
    _require_data(data, "percentile")
    if not 0.0 <= pct <= 100.0:
        raise ValueError("pct must be between 0 and 100")
    ordered = sorted(data)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (pct / 100.0) * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return float(ordered[int(rank)])
    fraction = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction
