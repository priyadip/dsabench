"""The core benchmarking engine.

Execution model (default and accurate modes):

1. ``warmup`` untimed runs (JIT caches, memoisation tables, page faults).
2. ``repeat`` clean timed runs measuring wall and CPU time only.
3. One extra *instrumented* pass with :mod:`tracemalloc` and the call
   profiler enabled, so instrumentation overhead never pollutes timings.

Fast mode (``repeat == 1`` and ``warmup == 0``) collapses this into a single
combined pass: the function runs exactly once.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeVar

from .config import Config, get_config
from .cpu import build_cpu_stats
from .exceptions import BenchError
from .export import auto_export
from .memory import MemoryTracker, get_process_rss
from .profiler import CallTracker
from .report import print_report
from .timer import measure
from .types import BenchmarkResult, ExceptionInfo, TimingStats
from .utils import format_args, safe_repr

__all__ = ["bench", "bench_async", "run"]

T = TypeVar("T")


def _function_name(func: Callable[..., Any], label: str | None = None) -> str:
    """Return the display name for *func* (label wins, then qualname)."""
    if label:
        return label
    return getattr(func, "__qualname__", None) or getattr(func, "__name__", repr(func))


def _build_invoker(
    func: Callable[..., Any],
    args: Sequence[Any],
    kwargs: Mapping[str, Any],
) -> tuple[Callable[[], Any], str | None]:
    """Return a zero-argument invoker for *func* plus a kind marker.

    Plain callables are called directly. Generator functions are fully
    consumed each run (otherwise creating the generator would measure
    nothing). Coroutine functions are executed with :func:`asyncio.run`
    per repetition; if an event loop is already running, a
    :class:`BenchError` explains how to proceed.

    Returns:
        ``(invoker, kind)`` where kind is ``None``, ``"generator"`` or
        ``"async"``.
    """
    if inspect.iscoroutinefunction(func):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise BenchError(
                "bench() cannot drive a coroutine while an event loop is already "
                "running (e.g. inside Jupyter). Use `await bench_async(func, ...)` "
                "or decorate the async function with @benchmark instead."
            )

        def invoke_async() -> Any:
            return asyncio.run(func(*args, **kwargs))

        return invoke_async, "async"

    if inspect.isgeneratorfunction(func):
        consumed = [0]

        def invoke_gen() -> Any:
            count = 0
            for _ in func(*args, **kwargs):
                count += 1
            consumed[0] = count
            return count

        invoke_gen.consumed = consumed  # type: ignore[attr-defined]
        return invoke_gen, "generator"

    def invoke() -> Any:
        return func(*args, **kwargs)

    return invoke, None


def run(
    func: Callable[..., Any],
    args: Sequence[Any] = (),
    kwargs: Mapping[str, Any] | None = None,
    *,
    config: Config | None = None,
    mode: str | None = None,
    repeat: int | None = None,
    warmup: int | None = None,
    label: str | None = None,
) -> BenchmarkResult:
    """Benchmark *func* and return the result without printing or raising.

    This is the low-level engine behind :func:`bench` and the decorator.
    Exceptions raised by *func* are captured into ``result.exception`` (and
    kept alive on ``result.raised``); :class:`KeyboardInterrupt` and
    :class:`SystemExit` always propagate.

    Args:
        func: Callable, generator function, or coroutine function.
        args: Positional arguments for *func*.
        kwargs: Keyword arguments for *func*.
        config: Base configuration (defaults to the global one).
        mode: Optional mode override (``"fast"|"default"|"accurate"``).
        repeat: Optional timed-repetition override.
        warmup: Optional warmup override.
        label: Optional display name override.

    Returns:
        A fully populated :class:`bench.types.BenchmarkResult`.
    """
    kwargs = dict(kwargs or {})
    cfg = (config or get_config()).merged(mode=mode, repeat=repeat, warmup=warmup)
    n_repeat = cfg.resolved_repeat()
    n_warmup = cfg.resolved_warmup()

    invoker, kind = _build_invoker(func, tuple(args), kwargs)
    name = _function_name(func, label)

    result = BenchmarkResult(
        name=name,
        mode=cfg.mode,
        repeat=n_repeat,
        warmup=n_warmup,
        return_value=None,
        return_repr="—",
        args_repr=format_args(args, kwargs, cfg.max_repr_length) if cfg.show_args else "",
    )

    wall_runs: list[int] = []
    cpu_runs: list[int] = []
    value: Any = None
    combined = n_repeat == 1 and n_warmup == 0

    try:
        # 1. Warmup runs (never timed, never instrumented).
        for _ in range(n_warmup):
            invoker()

        if combined:
            # Fast path: one call total, instrumented and timed together.
            def _sentinel() -> Any:
                return invoker()

            profiled = cfg.profile and kind != "async"
            tracker = CallTracker(entry_code=_sentinel.__code__)
            memtrack = MemoryTracker() if cfg.memory else None
            if profiled:
                tracker.start()
            try:
                if memtrack is not None:
                    with memtrack:
                        w, c, value = measure(_sentinel)
                else:
                    w, c, value = measure(_sentinel)
            finally:
                if profiled:
                    tracker.stop()
            wall_runs.append(w)
            cpu_runs.append(c)
            if memtrack is not None:
                result.memory = memtrack.as_stats(get_process_rss())
            if profiled:
                result.calls = tracker.as_stats()
        else:
            # 2. Clean timed runs.
            for _ in range(n_repeat):
                w, c, value = measure(invoker)
                wall_runs.append(w)
                cpu_runs.append(c)

            # 3. One instrumented pass (memory + calls), untimed.
            profiled = cfg.profile and kind != "async"
            if cfg.memory or profiled:

                def _sentinel() -> Any:
                    return invoker()

                tracker = CallTracker(entry_code=_sentinel.__code__)
                memtrack = MemoryTracker() if cfg.memory else None
                if profiled:
                    tracker.start()
                try:
                    if memtrack is not None:
                        with memtrack:
                            _sentinel()
                    else:
                        _sentinel()
                finally:
                    if profiled:
                        tracker.stop()
                if memtrack is not None:
                    result.memory = memtrack.as_stats(get_process_rss())
                if profiled:
                    result.calls = tracker.as_stats()
    except Exception as exc:  # noqa: BLE001 - target may raise anything
        result.exception = ExceptionInfo.from_exception(exc)
        result.raised = exc

    if wall_runs:
        result.timing = TimingStats.from_runs(wall_runs)
        if cfg.cpu:
            result.cpu = build_cpu_stats(wall_runs, cpu_runs)

    if result.exception is None:
        result.return_value = value
        if kind == "generator":
            consumed = getattr(invoker, "consumed", [0])[0]
            item = "item" if consumed == 1 else "items"
            result.return_repr = f"<generator: yielded {consumed} {item} per run>"
        else:
            result.return_repr = safe_repr(value, cfg.max_repr_length)

    return result


def _finalise(result: BenchmarkResult, cfg: Config) -> None:
    """Print and auto-export *result* according to *cfg*."""
    if not cfg.quiet:
        print_report(result, cfg)
    if cfg.export:
        auto_export(result, cfg)


def _caller_value(
    func: Callable[..., Any],
    args: Sequence[Any],
    kwargs: Mapping[str, Any],
    result: BenchmarkResult,
) -> Any:
    """Return what the caller of :func:`bench` should receive.

    For generator functions a *fresh* generator is returned (creating it does
    not execute the body), so ``for x in bench(gen, ...)`` works naturally.
    """
    if inspect.isgeneratorfunction(func):
        return func(*args, **kwargs)
    return result.return_value


def _execute(
    func: Callable[..., Any],
    args: Sequence[Any],
    kwargs: Mapping[str, Any],
    *,
    mode: str | None,
    repeat: int | None,
    warmup: int | None,
    quiet: bool | None,
    label: str | None,
) -> BenchmarkResult:
    """Run + report + optionally re-raise; shared by bench() and decorator."""
    cfg = get_config().merged(mode=mode, repeat=repeat, warmup=warmup, quiet=quiet)
    result = run(func, args, kwargs, config=cfg, label=label)
    _finalise(result, cfg)
    if result.raised is not None and cfg.raise_exceptions:
        raise result.raised
    return result


def bench(
    func: Callable[..., T],
    /,
    *args: Any,
    mode: str | None = None,
    repeat: int | None = None,
    warmup: int | None = None,
    quiet: bool | None = None,
    label: str | None = None,
    **kwargs: Any,
) -> T:
    """Benchmark ``func(*args, **kwargs)``, print a report, return its value.

    Example:
        >>> from bench import bench
        >>> answer = bench(sorted, [3, 1, 2])   # doctest: +SKIP
        >>> answer
        [1, 2, 3]

    Note:
        ``mode``, ``repeat``, ``warmup``, ``quiet`` and ``label`` are
        reserved by bench itself. If the target function needs a keyword
        with one of those names, call :func:`run` directly instead.

    Args:
        func: Callable, generator function, or coroutine function.
        *args: Positional arguments forwarded to *func*.
        mode: ``"fast"``, ``"default"``, or ``"accurate"``.
        repeat: Timed repetitions (overrides the mode default).
        warmup: Warmup runs (overrides the mode default).
        quiet: Suppress the printed report for this call.
        label: Display name override.
        **kwargs: Keyword arguments forwarded to *func*.

    Returns:
        The value returned by *func* (a fresh generator for generator
        functions; the awaited result for coroutine functions).

    Raises:
        BenchError: For coroutine functions while a loop is already running.
        Exception: Whatever *func* raised, unless ``raise_exceptions`` is
            disabled in the configuration.
    """
    result = _execute(
        func, args, kwargs, mode=mode, repeat=repeat, warmup=warmup, quiet=quiet, label=label
    )
    return _caller_value(func, args, kwargs, result)


async def _run_async(
    func: Callable[..., Any],
    args: Sequence[Any],
    kwargs: Mapping[str, Any],
    cfg: Config,
    label: str | None,
) -> BenchmarkResult:
    """Await-based engine for coroutine functions inside a running loop."""
    from .timer import cpu_ns, wall_ns  # local import keeps module top tidy

    n_repeat = cfg.resolved_repeat()
    n_warmup = cfg.resolved_warmup()
    name = _function_name(func, label)

    result = BenchmarkResult(
        name=name,
        mode=cfg.mode,
        repeat=n_repeat,
        warmup=n_warmup,
        return_value=None,
        return_repr="—",
        args_repr=format_args(args, kwargs, cfg.max_repr_length) if cfg.show_args else "",
    )

    wall_runs: list[int] = []
    cpu_runs: list[int] = []
    value: Any = None
    try:
        for _ in range(n_warmup):
            await func(*args, **kwargs)
        for _ in range(n_repeat):
            c0 = cpu_ns()
            w0 = wall_ns()
            value = await func(*args, **kwargs)
            wall_runs.append(wall_ns() - w0)
            cpu_runs.append(cpu_ns() - c0)
        if cfg.memory:
            with MemoryTracker() as memtrack:
                await func(*args, **kwargs)
            result.memory = memtrack.as_stats(get_process_rss())
    except Exception as exc:  # noqa: BLE001
        result.exception = ExceptionInfo.from_exception(exc)
        result.raised = exc

    if wall_runs:
        result.timing = TimingStats.from_runs(wall_runs)
        if cfg.cpu:
            result.cpu = build_cpu_stats(wall_runs, cpu_runs)
    if result.exception is None:
        result.return_value = value
        result.return_repr = safe_repr(value, cfg.max_repr_length)
    return result


async def bench_async(
    func: Callable[..., Any],
    /,
    *args: Any,
    mode: str | None = None,
    repeat: int | None = None,
    warmup: int | None = None,
    quiet: bool | None = None,
    label: str | None = None,
    **kwargs: Any,
) -> Any:
    """Awaitable counterpart of :func:`bench` for coroutine functions.

    Use this inside an already-running event loop (Jupyter, async apps):

    Example:
        >>> value = await bench_async(fetch, url)   # doctest: +SKIP

    Args:
        func: A coroutine function.
        *args: Positional arguments forwarded to *func*.
        mode: ``"fast"``, ``"default"``, or ``"accurate"``.
        repeat: Timed repetitions (overrides the mode default).
        warmup: Warmup runs (overrides the mode default).
        quiet: Suppress the printed report for this call.
        label: Display name override.
        **kwargs: Keyword arguments forwarded to *func*.

    Returns:
        The awaited return value of *func*.

    Raises:
        BenchError: If *func* is not a coroutine function.
        Exception: Whatever *func* raised, unless ``raise_exceptions`` is
            disabled in the configuration.
    """
    if not inspect.iscoroutinefunction(func):
        raise BenchError("bench_async() requires a coroutine function; use bench() instead.")
    cfg = get_config().merged(mode=mode, repeat=repeat, warmup=warmup, quiet=quiet)
    result = await _run_async(func, args, dict(kwargs), cfg, label)
    _finalise(result, cfg)
    if result.raised is not None and cfg.raise_exceptions:
        raise result.raised
    return result.return_value
