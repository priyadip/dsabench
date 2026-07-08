"""The :func:`benchmark` decorator.

Supports both bare (``@benchmark``) and parameterised
(``@benchmark(repeat=50)``) forms, works on sync, recursive, and async
functions, and stores the most recent :class:`bench.types.BenchmarkResult`
on ``wrapper.last_result``.

A thread-local depth guard ensures that recursive or nested calls of a
decorated function execute the *original*, un-instrumented function: exactly
one report is produced per outermost call, and recursion statistics stay
correct.
"""

from __future__ import annotations

import functools
import inspect
import threading
from collections.abc import Callable
from typing import Any, TypeVar, overload

from .benchmark import _finalise, _run_async, run
from .config import get_config

__all__ = ["benchmark"]

F = TypeVar("F", bound=Callable[..., Any])

#: Shared, thread-local re-entrancy guard. One guard for *all* decorated
#: functions: while any decorated function is being benchmarked in the
#: current thread, every other decorated call (recursive or nested) runs
#: its original, un-instrumented function. Exactly one report per
#: outermost call, and no benchmarking machinery inside timed regions.
_guard = threading.local()


@overload
def benchmark(func: F) -> F: ...


@overload
def benchmark(
    *,
    mode: str | None = ...,
    repeat: int | None = ...,
    warmup: int | None = ...,
    quiet: bool | None = ...,
    label: str | None = ...,
) -> Callable[[F], F]: ...


def benchmark(
    func: Callable[..., Any] | None = None,
    /,
    *,
    mode: str | None = None,
    repeat: int | None = None,
    warmup: int | None = None,
    quiet: bool | None = None,
    label: str | None = None,
) -> Any:
    """Decorate a function so every call is benchmarked and reported.

    Example:
        >>> from bench import benchmark
        >>> @benchmark
        ... def solve(n):
        ...     return sum(range(n))
        >>> @benchmark(mode="accurate", repeat=200)
        ... def hot_path(xs):
        ...     return sorted(xs)

    Args:
        func: The function when used bare (``@benchmark``); leave unset when
            passing options (``@benchmark(...)``).
        mode: ``"fast"``, ``"default"``, or ``"accurate"``.
        repeat: Timed repetitions (overrides the mode default).
        warmup: Warmup runs (overrides the mode default).
        quiet: Suppress printed reports for this function.
        label: Display name override.

    Returns:
        The wrapped function. Its return value is always the original
        function's return value; the latest :class:`BenchmarkResult` is
        available as ``wrapper.last_result`` and the raw function as
        ``wrapper.original``.
    """

    def decorate(target: Callable[..., Any]) -> Callable[..., Any]:

        if inspect.iscoroutinefunction(target):

            @functools.wraps(target)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                if getattr(_guard, "depth", 0) > 0:
                    return await target(*args, **kwargs)
                _guard.depth = 1
                try:
                    cfg = get_config().merged(mode=mode, repeat=repeat, warmup=warmup, quiet=quiet)
                    result = await _run_async(target, args, kwargs, cfg, label)
                    async_wrapper.last_result = result  # type: ignore[attr-defined]
                    _finalise(result, cfg)
                    if result.raised is not None and cfg.raise_exceptions:
                        raise result.raised
                    return result.return_value
                finally:
                    _guard.depth = 0

            async_wrapper.last_result = None  # type: ignore[attr-defined]
            async_wrapper.original = target  # type: ignore[attr-defined]
            return async_wrapper

        @functools.wraps(target)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if getattr(_guard, "depth", 0) > 0:
                # Nested/recursive call: run the raw function untouched.
                return target(*args, **kwargs)
            _guard.depth = 1
            try:
                cfg = get_config().merged(mode=mode, repeat=repeat, warmup=warmup, quiet=quiet)
                result = run(target, args, kwargs, config=cfg, label=label)
                wrapper.last_result = result  # type: ignore[attr-defined]
                _finalise(result, cfg)
                if result.raised is not None and cfg.raise_exceptions:
                    raise result.raised
                if inspect.isgeneratorfunction(target):
                    return target(*args, **kwargs)
                return result.return_value
            finally:
                _guard.depth = 0

        wrapper.last_result = None  # type: ignore[attr-defined]
        wrapper.original = target  # type: ignore[attr-defined]
        return wrapper

    if func is not None:
        return decorate(func)
    return decorate
