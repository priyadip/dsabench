"""Optional matplotlib visualisations.

Matplotlib is an optional dependency; install it with
``pip install "dsabench[viz]"``. Every function saves to *path* when given
(returning the :class:`pathlib.Path`), otherwise returns the live
``Figure`` (and can ``show`` it).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .exceptions import GraphError
from .types import BenchmarkResult, ComparisonResult

__all__ = ["plot_runtime", "plot_memory", "plot_comparison"]


def _plt() -> Any:
    """Import and return ``matplotlib.pyplot`` with a helpful error."""
    try:
        import matplotlib

        matplotlib.use("Agg", force=False)
        import matplotlib.pyplot as plt

        return plt
    except ImportError as exc:  # pragma: no cover - exercised only without mpl
        raise GraphError('matplotlib is required for graphs: pip install "dsabench[viz]"') from exc


def _finish(fig: Any, plt: Any, path: str | Path | None, show: bool) -> Path | Any:
    if path is not None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return target
    if show:  # pragma: no cover - opens a window
        plt.show()
    return fig


def plot_runtime(
    result: BenchmarkResult,
    path: str | Path | None = None,
    show: bool = False,
) -> Path | Any:
    """Plot per-run wall time for a single benchmark.

    Args:
        result: A benchmark result with timing data.
        path: Optional output image path (PNG/SVG/... by suffix).
        show: Display interactively when no path is given.

    Returns:
        The written :class:`~pathlib.Path`, or the ``Figure``.

    Raises:
        GraphError: When the result has no timing data or matplotlib is
            missing.
    """
    if result.timing is None:
        raise GraphError("plot_runtime() needs timing data")
    plt = _plt()
    runs_ms = [r / 1e6 for r in result.timing.runs_ns]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(range(1, len(runs_ms) + 1), runs_ms, marker="o", linewidth=1.5, label="run")
    ax.axhline(result.timing.average_ms, linestyle="--", linewidth=1.2, label="average")
    ax.set_title(f"Runtime per run — {result.name}")
    ax.set_xlabel("Run #")
    ax.set_ylabel("Wall time (ms)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return _finish(fig, plt, path, show)


def plot_memory(
    result: BenchmarkResult,
    path: str | Path | None = None,
    show: bool = False,
) -> Path | Any:
    """Plot peak/current/delta heap usage for a single benchmark.

    Args:
        result: A benchmark result with memory data.
        path: Optional output image path.
        show: Display interactively when no path is given.

    Returns:
        The written :class:`~pathlib.Path`, or the ``Figure``.

    Raises:
        GraphError: When the result has no memory data or matplotlib is
            missing.
    """
    if result.memory is None:
        raise GraphError("plot_memory() needs memory data")
    plt = _plt()
    mem = result.memory
    labels = ["Peak", "Current", "Delta"]
    values_kb = [mem.peak_bytes / 1024, mem.current_bytes / 1024, mem.delta_bytes / 1024]
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(labels, values_kb)
    ax.bar_label(bars, fmt="%.1f")
    ax.set_title(f"Heap memory — {result.name}")
    ax.set_ylabel("KB")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    return _finish(fig, plt, path, show)


def plot_comparison(
    comparison: ComparisonResult,
    path: str | Path | None = None,
    show: bool = False,
) -> Path | Any:
    """Plot a horizontal bar chart of average runtimes for a comparison.

    Args:
        comparison: Result of :func:`bench.compare`.
        path: Optional output image path.
        show: Display interactively when no path is given.

    Returns:
        The written :class:`~pathlib.Path`, or the ``Figure``.

    Raises:
        GraphError: When no candidate has timing data or matplotlib is
            missing.
    """
    entries = [e for e in comparison.entries if e.result.timing is not None]
    if not entries:
        raise GraphError("plot_comparison() needs at least one timed candidate")
    plt = _plt()
    names = [e.name for e in entries][::-1]
    avgs_ms = [e.result.timing.average_ms for e in entries][::-1]
    errs_ms = [e.result.timing.stdev_ns / 1e6 for e in entries][::-1]
    fig, ax = plt.subplots(figsize=(8, 0.6 * len(entries) + 1.5))
    ax.barh(names, avgs_ms, xerr=errs_ms, capsize=4)
    ax.set_title("Average runtime comparison")
    ax.set_xlabel("Wall time (ms)")
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    return _finish(fig, plt, path, show)
