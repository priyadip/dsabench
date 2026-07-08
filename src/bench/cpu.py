"""CPU-time statistics helpers."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .stats import mean
from .types import CPUStats

__all__ = ["cpu_percent", "build_cpu_stats"]


def cpu_percent(wall_total_ns: float, cpu_total_ns: float) -> float:
    """Return CPU utilisation as a percentage of wall time.

    Values above 100% are possible (and meaningful) for multi-threaded code
    because :func:`time.process_time_ns` sums CPU time across all threads.

    Args:
        wall_total_ns: Total wall-clock time in nanoseconds.
        cpu_total_ns: Total process CPU time in nanoseconds.

    Returns:
        Utilisation percentage; ``0.0`` when wall time is not positive.
    """
    if wall_total_ns <= 0:
        return 0.0
    return (cpu_total_ns / wall_total_ns) * 100.0


def build_cpu_stats(wall_runs_ns: Sequence[int], cpu_runs_ns: Sequence[int]) -> CPUStats:
    """Aggregate per-run CPU samples into a :class:`bench.types.CPUStats`.

    Args:
        wall_runs_ns: Wall time of each timed run in nanoseconds.
        cpu_runs_ns: CPU time of each timed run in nanoseconds.

    Returns:
        A populated :class:`bench.types.CPUStats`.
    """
    cpu_runs = tuple(int(c) for c in cpu_runs_ns)
    average_cpu = mean([float(c) for c in cpu_runs]) if cpu_runs else 0.0
    wall_total = math.fsum(float(w) for w in wall_runs_ns)
    cpu_total = math.fsum(float(c) for c in cpu_runs)
    return CPUStats(
        cpu_runs_ns=cpu_runs,
        average_cpu_ns=average_cpu,
        cpu_percent=cpu_percent(wall_total, cpu_total),
    )
