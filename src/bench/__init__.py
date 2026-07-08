"""DsaBench — beautiful one-line benchmarking for DSA and beyond.

Quick start::

    from bench import bench

    answer = bench(solve, arg1, arg2)   # runs, reports, returns the value

See :func:`benchmark` (decorator), :func:`auto` (automatic mode),
:func:`compare`, :func:`estimate_complexity`, and :func:`configure`.
"""

from .auto import AutoBench, AutoReport, FunctionRecord, auto, stop_auto
from .benchmark import bench, bench_async, run
from .compare import compare
from .complexity import estimate_complexity
from .config import Config, configure, get_config, reset_config
from .decorator import benchmark
from .exceptions import BenchError, ConfigurationError, ExportError, GraphError
from .export import auto_export, export_result, to_csv, to_json, to_markdown
from .graph import plot_comparison, plot_memory, plot_runtime
from .types import (
    MODE_DEFAULTS,
    BenchmarkResult,
    CallStats,
    ComparisonEntry,
    ComparisonResult,
    ComplexityFit,
    ComplexityResult,
    CPUStats,
    ExceptionInfo,
    MemoryStats,
    Mode,
    TimingStats,
)

__version__ = "0.2.0"

__all__ = [
    # core API
    "bench",
    "bench_async",
    "run",
    "benchmark",
    "auto",
    "stop_auto",
    "compare",
    "estimate_complexity",
    # configuration
    "configure",
    "get_config",
    "reset_config",
    "Config",
    # export & graphs
    "export_result",
    "auto_export",
    "to_json",
    "to_csv",
    "to_markdown",
    "plot_runtime",
    "plot_memory",
    "plot_comparison",
    # types
    "Mode",
    "MODE_DEFAULTS",
    "TimingStats",
    "MemoryStats",
    "CPUStats",
    "CallStats",
    "ExceptionInfo",
    "BenchmarkResult",
    "ComparisonEntry",
    "ComparisonResult",
    "ComplexityFit",
    "ComplexityResult",
    "AutoBench",
    "AutoReport",
    "FunctionRecord",
    # exceptions
    "BenchError",
    "ConfigurationError",
    "ExportError",
    "GraphError",
    # metadata
    "__version__",
]
