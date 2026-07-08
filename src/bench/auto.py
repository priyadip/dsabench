"""Automatic benchmarking of every user-defined function call.

Calling :func:`auto` installs a lightweight :func:`sys.setprofile` hook (and
:func:`threading.setprofile` for new threads). From that moment on, every
call of a *user-defined* function — code living outside the standard
library, site-packages, and bench itself — is timed and aggregated.

Per top-level call a compact live line is printed; :func:`stop_auto` (or
interpreter exit) prints a ranked summary table.

Known limitations (by design of the profile-hook approach):

* Generator bodies are measured per resume slice, not per full iteration.
* While :func:`bench.bench` runs its instrumented pass, its own
  :class:`~bench.profiler.CallTracker` temporarily supersedes the auto hook.
* Only functions, not C builtins, are captured.
"""

from __future__ import annotations

import atexit
import fnmatch
import sys
import threading
from dataclasses import dataclass, field
from types import FrameType, TracebackType
from typing import Any

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from .config import get_config
from .timer import cpu_ns, wall_ns
from .utils import describe_location, format_time_ns, is_user_file

__all__ = ["auto", "stop_auto", "AutoBench", "AutoReport", "FunctionRecord"]


@dataclass(slots=True)
class FunctionRecord:
    """Aggregated statistics for one user function under auto mode."""

    name: str
    location: str
    calls: int = 0
    total_wall_ns: int = 0
    total_cpu_ns: int = 0
    min_wall_ns: int = field(default=2**63 - 1)
    max_wall_ns: int = 0

    @property
    def average_wall_ns(self) -> float:
        """Average wall time per call in nanoseconds."""
        return self.total_wall_ns / self.calls if self.calls else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "name": self.name,
            "location": self.location,
            "calls": self.calls,
            "total_wall_ns": self.total_wall_ns,
            "total_cpu_ns": self.total_cpu_ns,
            "average_wall_ns": self.average_wall_ns,
            "min_wall_ns": self.min_wall_ns if self.calls else 0,
            "max_wall_ns": self.max_wall_ns,
        }


@dataclass(slots=True)
class AutoReport:
    """Summary returned by :meth:`AutoBench.stop`."""

    records: list[FunctionRecord]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {"records": [record.to_dict() for record in self.records]}


_ACTIVE: AutoBench | None = None
_state_lock = threading.RLock()


class AutoBench:
    """Automatic benchmarking session (see module docstring).

    Args:
        live: Print a one-line timing for every top-level user call.
        include: Optional function names or fnmatch patterns (e.g.
            ``["solve*"]``) to capture exclusively.
        exclude: Optional function names or fnmatch patterns to ignore.
    """

    def __init__(
        self,
        live: bool = True,
        include: set[str] | frozenset[str] | list[str] | tuple[str, ...] | None = None,
        exclude: set[str] | frozenset[str] | list[str] | tuple[str, ...] | None = None,
    ) -> None:
        self.live = live
        self.include = frozenset(include) if include else None
        self.exclude = frozenset(exclude) if exclude else frozenset()
        self.records: dict[Any, FunctionRecord] = {}
        self.last_report: AutoReport | None = None
        self._local = threading.local()
        self._prev_profile: Any = None
        self._prev_thread_profile: Any = None
        self._running = False
        self._console = Console(no_color=not get_config().color, highlight=False)

    # -- qualification ------------------------------------------------------
    @staticmethod
    def _matches(patterns: frozenset[str], name: str, qualname: str) -> bool:
        """True when *name* or *qualname* matches any fnmatch pattern."""
        return any(
            fnmatch.fnmatchcase(name, pat) or fnmatch.fnmatchcase(qualname, pat) for pat in patterns
        )

    def _qualifies(self, code: Any) -> bool:
        name = code.co_name
        if name.startswith("<"):  # <lambda>, <listcomp>, <module>, ...
            return False
        if not is_user_file(code.co_filename):
            return False
        qualname = getattr(code, "co_qualname", name)
        if self.include is not None:
            return self._matches(self.include, name, qualname)
        return not self._matches(self.exclude, name, qualname)

    # -- profile hook ----------------------------------------------------------
    def _hook(self, frame: FrameType, event: str, arg: Any) -> None:
        if event == "call":
            code = frame.f_code
            if not self._qualifies(code):
                return
            stack = getattr(self._local, "stack", None)
            if stack is None:
                stack = self._local.stack = []
            is_top = not stack
            stack.append((frame, wall_ns(), cpu_ns(), is_top))
        elif event == "return":
            stack = getattr(self._local, "stack", None)
            if not stack:
                return
            top_frame, w0, c0, is_top = stack[-1]
            if top_frame is not frame:
                return  # return of a non-tracked frame interleaved
            stack.pop()
            wall = wall_ns() - w0
            cpu = cpu_ns() - c0
            code = frame.f_code
            record = self.records.get(code)
            if record is None:
                record = self.records[code] = FunctionRecord(
                    name=getattr(code, "co_qualname", code.co_name),
                    location=describe_location(code.co_filename, code.co_firstlineno),
                )
            record.calls += 1
            record.total_wall_ns += wall
            record.total_cpu_ns += cpu
            if wall < record.min_wall_ns:
                record.min_wall_ns = wall
            if wall > record.max_wall_ns:
                record.max_wall_ns = wall
            if self.live and is_top:
                # Safe: CPython suppresses profile events raised by the hook itself.
                self._console.print(
                    Text(record.name, style="bold magenta")
                    + Text(f"  {format_time_ns(wall)}", style="green")
                )

    # -- lifecycle ----------------------------------------------------------------
    @property
    def active(self) -> bool:
        """``True`` while this session's hooks are installed."""
        return self._running

    def start(self) -> AutoBench:
        """Install the hooks and register this session as the active one."""
        global _ACTIVE
        with _state_lock:
            if _ACTIVE is not None and _ACTIVE is not self:
                _ACTIVE.stop(print_summary=False)
            self._prev_profile = sys.getprofile()
            self._prev_thread_profile = threading.getprofile()
            sys.setprofile(self._hook)
            threading.setprofile(self._hook)
            self._running = True
            _ACTIVE = self
        return self

    def stop(self, print_summary: bool = True) -> AutoReport:
        """Remove the hooks and return (optionally print) the summary.

        Args:
            print_summary: Print the ranked table when records exist.

        Returns:
            An :class:`AutoReport` with per-function aggregates ranked by
            total wall time.
        """
        global _ACTIVE
        with _state_lock:
            if self._running:
                sys.setprofile(self._prev_profile)
                threading.setprofile(self._prev_thread_profile)
                self._running = False
            if _ACTIVE is self:
                _ACTIVE = None
        ranked = sorted(self.records.values(), key=lambda r: r.total_wall_ns, reverse=True)
        report = AutoReport(records=ranked)
        self.last_report = report
        if print_summary:
            self._print_summary(report)
        return report

    def __enter__(self) -> AutoBench:
        return self.start()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.stop(print_summary=True)

    # -- rendering ------------------------------------------------------------------
    def _print_summary(self, report: AutoReport) -> None:
        if not report.records:
            self._console.print(Text("bench.auto: no user functions captured", style="yellow"))
            return
        table = Table(
            box=box.ROUNDED,
            border_style="cyan",
            title="Auto Benchmark Summary",
            title_justify="left",
        )
        table.add_column("Function", style="bold")
        table.add_column("Location")
        table.add_column("Calls", justify="right")
        table.add_column("Total", justify="right")
        table.add_column("Average", justify="right")
        table.add_column("Min", justify="right")
        table.add_column("Max", justify="right")
        for record in report.records:
            table.add_row(
                record.name,
                record.location,
                f"{record.calls:,}",
                format_time_ns(record.total_wall_ns),
                format_time_ns(record.average_wall_ns),
                format_time_ns(record.min_wall_ns if record.calls else 0),
                format_time_ns(record.max_wall_ns),
            )
        self._console.print(table)


def auto(
    live: bool = True,
    include: set[str] | list[str] | tuple[str, ...] | None = None,
    exclude: set[str] | list[str] | tuple[str, ...] | None = None,
) -> AutoBench:
    """Start automatic benchmarking of every user-defined function call.

    Example:
        >>> from bench import auto
        >>> auto()                      # doctest: +SKIP
        >>> def work(n):
        ...     return sum(range(n))
        >>> work(10_000)                # printed and recorded automatically

    Args:
        live: Print a one-line timing for each top-level user call.
        include: Capture only these function names or fnmatch patterns.
        exclude: Ignore these function names or fnmatch patterns.

    Returns:
        The started :class:`AutoBench` session (also usable as a context
        manager and stoppable via :func:`stop_auto`).
    """
    return AutoBench(live=live, include=include, exclude=exclude).start()


def stop_auto(print_summary: bool = True) -> AutoReport | None:
    """Stop the active :func:`auto` session, if any.

    Args:
        print_summary: Print the ranked summary table.

    Returns:
        The session's :class:`AutoReport`, or ``None`` when auto mode was
        not running.
    """
    session = _ACTIVE
    if session is None:
        return None
    return session.stop(print_summary=print_summary)


@atexit.register
def _print_summary_at_exit() -> None:  # pragma: no cover - interpreter teardown
    session = _ACTIVE
    if session is not None and session.active:
        session.stop(print_summary=True)
