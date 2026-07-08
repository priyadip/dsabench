"""Tests for bench.graph — matplotlib exports (skipped without matplotlib)."""

from __future__ import annotations

import pytest

matplotlib = pytest.importorskip("matplotlib")

import bench  # noqa: E402
from bench import run  # noqa: E402
from bench.exceptions import GraphError  # noqa: E402
from bench.graph import plot_comparison, plot_memory, plot_runtime  # noqa: E402


def _result():
    return run(lambda: sum(range(100)), repeat=3, warmup=0, label="plotme")


def test_plot_runtime_writes_png(tmp_path):
    path = plot_runtime(_result(), path=tmp_path / "rt.png")
    assert path.exists() and path.stat().st_size > 0


def test_plot_memory_writes_png(tmp_path):
    path = plot_memory(_result(), path=tmp_path / "mem.png")
    assert path.exists() and path.stat().st_size > 0


def test_plot_comparison_writes_png(tmp_path):
    cmp = bench.compare(("A", lambda: 1), ("B", lambda: 2), repeat=2, warmup=0)
    path = plot_comparison(cmp, path=tmp_path / "cmp.png")
    assert path.exists() and path.stat().st_size > 0


def test_plot_runtime_requires_timing(tmp_path):
    r = _result()
    r.timing = None
    with pytest.raises(GraphError):
        plot_runtime(r, path=tmp_path / "x.png")


def test_plot_memory_requires_memory(tmp_path):
    r = _result()
    r.memory = None
    with pytest.raises(GraphError):
        plot_memory(r, path=tmp_path / "x.png")


def test_plot_returns_figure_without_path():
    fig = plot_runtime(_result(), path=None, show=False)
    assert fig.__class__.__name__ == "Figure"
    import matplotlib.pyplot as plt

    plt.close(fig)
