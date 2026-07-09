"""Typed result objects returned by the bench package.

Everything here is a plain, ``slots``-enabled dataclass so results are cheap,
introspectable, and easy to serialise via :meth:`BenchmarkResult.to_dict`.
"""

from __future__ import annotations

import math
import traceback as _traceback
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .exceptions import ConfigurationError
from .stats import mean, median, percentile, stdev

__all__ = [
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
    "SpaceComplexityResult",
]


class Mode(str, Enum):
    """Benchmark precision mode controlling default repetitions and warmups."""

    FAST = "fast"
    DEFAULT = "default"
    ACCURATE = "accurate"

    @classmethod
    def from_value(cls, value: Mode | str) -> Mode:
        """Coerce a string (or Mode) into a :class:`Mode` member.

        Args:
            value: A :class:`Mode` member or its string value
                (``"fast"``, ``"default"``, ``"accurate"``).

        Returns:
            The corresponding :class:`Mode` member.

        Raises:
            ConfigurationError: If *value* is not a recognised mode.
        """
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError:
            valid = ", ".join(m.value for m in cls)
            raise ConfigurationError(f"Unknown mode {value!r}; expected one of: {valid}") from None


#: Default ``(repeat, warmup)`` pairs for each mode.
MODE_DEFAULTS: dict[Mode, tuple[int, int]] = {
    Mode.FAST: (1, 0),
    Mode.DEFAULT: (10, 1),
    Mode.ACCURATE: (100, 5),
}


@dataclass(slots=True, frozen=True)
class TimingStats:
    """Wall-clock timing statistics over the timed runs (nanoseconds)."""

    runs_ns: tuple[int, ...]
    fastest_ns: float
    slowest_ns: float
    average_ns: float
    median_ns: float
    stdev_ns: float
    p95_ns: float
    total_ns: float

    @classmethod
    def from_runs(cls, runs_ns: Sequence[int]) -> TimingStats:
        """Build a :class:`TimingStats` from raw per-run wall times.

        Args:
            runs_ns: Wall-clock duration of each timed run in nanoseconds.

        Returns:
            A populated :class:`TimingStats`.

        Raises:
            ValueError: If *runs_ns* is empty.
        """
        runs = tuple(int(r) for r in runs_ns)
        values = [float(r) for r in runs]
        return cls(
            runs_ns=runs,
            fastest_ns=min(values),
            slowest_ns=max(values),
            average_ns=mean(values),
            median_ns=median(values),
            stdev_ns=stdev(values),
            p95_ns=percentile(values, 95.0),
            total_ns=math.fsum(values),
        )

    # -- unit conversion helpers -------------------------------------------------
    @property
    def fastest_us(self) -> float:
        """Fastest run in microseconds."""
        return self.fastest_ns / 1_000.0

    @property
    def fastest_ms(self) -> float:
        """Fastest run in milliseconds."""
        return self.fastest_ns / 1_000_000.0

    @property
    def average_us(self) -> float:
        """Average run in microseconds."""
        return self.average_ns / 1_000.0

    @property
    def average_ms(self) -> float:
        """Average run in milliseconds."""
        return self.average_ns / 1_000_000.0

    @property
    def average_s(self) -> float:
        """Average run in seconds."""
        return self.average_ns / 1_000_000_000.0

    @property
    def median_ms(self) -> float:
        """Median run in milliseconds."""
        return self.median_ns / 1_000_000.0

    @property
    def total_s(self) -> float:
        """Total measured wall time in seconds."""
        return self.total_ns / 1_000_000_000.0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "runs_ns": list(self.runs_ns),
            "fastest_ns": self.fastest_ns,
            "slowest_ns": self.slowest_ns,
            "average_ns": self.average_ns,
            "median_ns": self.median_ns,
            "stdev_ns": self.stdev_ns,
            "p95_ns": self.p95_ns,
            "total_ns": self.total_ns,
        }


@dataclass(slots=True, frozen=True)
class MemoryStats:
    """Heap memory statistics from a single instrumented pass (bytes)."""

    peak_bytes: int
    current_bytes: int
    delta_bytes: int
    process_rss_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "peak_bytes": self.peak_bytes,
            "current_bytes": self.current_bytes,
            "delta_bytes": self.delta_bytes,
            "process_rss_bytes": self.process_rss_bytes,
        }


@dataclass(slots=True, frozen=True)
class CPUStats:
    """CPU-time statistics over the timed runs."""

    cpu_runs_ns: tuple[int, ...]
    average_cpu_ns: float
    cpu_percent: float

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "cpu_runs_ns": list(self.cpu_runs_ns),
            "average_cpu_ns": self.average_cpu_ns,
            "cpu_percent": self.cpu_percent,
        }


@dataclass(slots=True, frozen=True)
class CallStats:
    """Call-graph statistics from the instrumented pass."""

    function_calls: int
    recursive_calls: int
    max_recursion_depth: int
    gc_collections: int

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "function_calls": self.function_calls,
            "recursive_calls": self.recursive_calls,
            "max_recursion_depth": self.max_recursion_depth,
            "gc_collections": self.gc_collections,
        }


@dataclass(slots=True, frozen=True)
class ExceptionInfo:
    """Details of an exception raised by the benchmarked function."""

    type_name: str
    message: str
    traceback: str

    @classmethod
    def from_exception(cls, exc: BaseException) -> ExceptionInfo:
        """Capture *exc* into a serialisable record.

        Args:
            exc: The exception instance raised by the target function.

        Returns:
            A populated :class:`ExceptionInfo`.
        """
        tb = "".join(_traceback.format_exception(type(exc), exc, exc.__traceback__))
        return cls(type_name=type(exc).__name__, message=str(exc), traceback=tb)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "type_name": self.type_name,
            "message": self.message,
            "traceback": self.traceback,
        }


@dataclass(slots=True)
class BenchmarkResult:
    """Complete result of benchmarking a single callable."""

    name: str
    mode: Mode
    repeat: int
    warmup: int
    return_value: Any
    return_repr: str
    args_repr: str
    timing: TimingStats | None = None
    cpu: CPUStats | None = None
    memory: MemoryStats | None = None
    calls: CallStats | None = None
    exception: ExceptionInfo | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    raised: BaseException | None = field(default=None, repr=False, compare=False)

    # -- convenience delegation --------------------------------------------------
    @property
    def ok(self) -> bool:
        """``True`` when the function completed without raising."""
        return self.exception is None

    @property
    def fastest_ns(self) -> float | None:
        """Fastest wall-clock run in nanoseconds, or None if not timed."""
        return self.timing.fastest_ns if self.timing else None

    @property
    def average_ns(self) -> float | None:
        """Average wall-clock run in nanoseconds, or None if not timed."""
        return self.timing.average_ns if self.timing else None

    @property
    def average_ms(self) -> float | None:
        """Average wall-clock run in milliseconds, or None if not timed."""
        return self.timing.average_ms if self.timing else None

    @property
    def median_ns(self) -> float | None:
        """Median wall-clock run in nanoseconds, or None if not timed."""
        return self.timing.median_ns if self.timing else None

    @property
    def peak_memory_bytes(self) -> int | None:
        """Peak traced heap usage in bytes, or None if memory was off."""
        return self.memory.peak_bytes if self.memory else None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation.

        The live ``return_value`` and ``raised`` exception objects are
        intentionally excluded; use :attr:`return_repr` and
        :attr:`exception` instead.
        """
        return {
            "name": self.name,
            "mode": self.mode.value,
            "repeat": self.repeat,
            "warmup": self.warmup,
            "return_repr": self.return_repr,
            "args_repr": self.args_repr,
            "timing": self.timing.to_dict() if self.timing else None,
            "cpu": self.cpu.to_dict() if self.cpu else None,
            "memory": self.memory.to_dict() if self.memory else None,
            "calls": self.calls.to_dict() if self.calls else None,
            "exception": self.exception.to_dict() if self.exception else None,
            "timestamp": self.timestamp,
        }


@dataclass(slots=True)
class ComparisonEntry:
    """One ranked candidate inside a :class:`ComparisonResult`."""

    name: str
    result: BenchmarkResult
    rank: int
    relative: float

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "name": self.name,
            "rank": self.rank,
            "relative": self.relative,
            "result": self.result.to_dict(),
        }


@dataclass(slots=True)
class ComparisonResult:
    """Ranked results of :func:`bench.compare`."""

    entries: list[ComparisonEntry]
    args_repr: str
    outputs_match: bool | None = None

    @property
    def winner(self) -> ComparisonEntry:
        """The fastest (rank 1) entry."""
        return self.entries[0]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "args_repr": self.args_repr,
            "outputs_match": self.outputs_match,
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(slots=True, frozen=True)
class ComplexityFit:
    """Goodness-of-fit of one asymptotic model in a complexity estimate."""

    label: str
    coefficient: float
    r_squared: float

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "label": self.label,
            "coefficient": self.coefficient,
            "r_squared": self.r_squared,
        }


@dataclass(slots=True)
class ComplexityResult:
    """Result of :func:`bench.estimate_complexity` (fits sorted best-first)."""

    name: str
    sizes: tuple[int, ...]
    times_ns: tuple[float, ...]
    fits: list[ComplexityFit]

    @property
    def best(self) -> ComplexityFit:
        """The best-fitting asymptotic model."""
        return self.fits[0]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "name": self.name,
            "sizes": list(self.sizes),
            "times_ns": list(self.times_ns),
            "best": self.best.label if self.fits else None,
            "fits": [fit.to_dict() for fit in self.fits],
        }


@dataclass(slots=True)
class SpaceComplexityResult:
    """Result of :func:`bench.estimate_space_complexity` (fits sorted best-first)."""

    name: str
    sizes: tuple[int, ...]
    peak_bytes: tuple[float, ...]
    fits: list[ComplexityFit]

    @property
    def best(self) -> ComplexityFit:
        """The best-fitting asymptotic model."""
        return self.fits[0]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "name": self.name,
            "sizes": list(self.sizes),
            "peak_bytes": list(self.peak_bytes),
            "best": self.best.label if self.fits else None,
            "fits": [fit.to_dict() for fit in self.fits],
        }
