"""Empirical asymptotic complexity estimation.

The target function is timed on several input sizes; each candidate model
``t ≈ c · f(n)`` is fitted by least squares through the origin and ranked by
R². The best-scoring label is reported. This is an *empirical hint*, not a
proof — constant factors, caches, and small sizes can mislead it.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import Any

from .benchmark import run
from .config import get_config
from .exceptions import BenchError
from .report import print_complexity
from .types import ComplexityFit, ComplexityResult

__all__ = ["estimate_complexity"]

_MODELS: list[tuple[str, Callable[[float], float]]] = [
    ("O(1)", lambda n: 1.0),
    ("O(log n)", lambda n: math.log2(n) if n > 1 else 1.0),
    ("O(n)", lambda n: n),
    ("O(n log n)", lambda n: n * math.log2(n) if n > 1 else n),
    ("O(n²)", lambda n: n * n),
    ("O(n³)", lambda n: n * n * n),
]


def _fit_through_origin(xs: Sequence[float], ys: Sequence[float]) -> tuple[float, float]:
    """Least-squares fit of ``y = c·x`` returning ``(c, r_squared)``."""
    sxx = math.fsum(x * x for x in xs)
    sxy = math.fsum(x * y for x, y in zip(xs, ys, strict=True))
    c = sxy / sxx if sxx > 0 else 0.0
    mean_y = math.fsum(ys) / len(ys)
    ss_tot = math.fsum((y - mean_y) ** 2 for y in ys)
    ss_res = math.fsum((y - c * x) ** 2 for x, y in zip(xs, ys, strict=True))
    r_squared = 1.0 - ss_res / max(ss_tot, 1e-9)
    return c, r_squared


def estimate_complexity(
    func: Callable[..., Any],
    sizes: Sequence[int],
    *,
    args_for: Callable[[int], Any] | None = None,
    repeat: int = 3,
    warmup: int = 1,
    quiet: bool | None = None,
    label: str | None = None,
) -> ComplexityResult:
    """Estimate the asymptotic time complexity of *func* empirically.

    Example:
        >>> from bench import estimate_complexity
        >>> est = estimate_complexity(sorted_scan, sizes=[1_000, 5_000,
        ...                           20_000, 80_000])       # doctest: +SKIP
        >>> est.best.label                                    # doctest: +SKIP
        'O(n)'

    Args:
        func: The function under test.
        sizes: At least three distinct positive input sizes. Spread them
            over an order of magnitude or more for a trustworthy fit.
        args_for: Maps a size ``n`` to the call arguments. Defaults to
            passing ``n`` itself; a non-tuple return value is wrapped as a
            single argument.
        repeat: Timed repetitions per size (the minimum is used).
        warmup: Warmup runs per size.
        quiet: Suppress the printed report.
        label: Display name override.

    Returns:
        A :class:`bench.types.ComplexityResult` with fits ranked best-first.

    Raises:
        BenchError: If fewer than three distinct sizes (or any size < 1)
            are supplied, or if the function fails on some size.
    """
    unique_sizes = sorted(set(int(s) for s in sizes))
    if len(unique_sizes) < 3:
        raise BenchError("estimate_complexity() needs at least 3 distinct sizes")
    if unique_sizes[0] < 1:
        raise BenchError("sizes must be >= 1")

    cfg = get_config().merged(quiet=quiet)
    name = label or getattr(func, "__qualname__", None) or getattr(func, "__name__", "function")

    times_ns: list[float] = []
    for n in unique_sizes:
        call_args = args_for(n) if args_for else (n,)
        if not isinstance(call_args, tuple):
            call_args = (call_args,)
        result = run(
            func,
            call_args,
            config=cfg.merged(memory=False, profile=False, mode="fast"),
            repeat=max(1, repeat),
            warmup=max(0, warmup),
            label=name,
        )
        if result.exception is not None or result.timing is None:
            detail = result.exception.message if result.exception else "no timing captured"
            raise BenchError(f"{name} failed at n={n}: {detail}")
        times_ns.append(result.timing.fastest_ns)

    xs_by_model = {label_: [fn(float(n)) for n in unique_sizes] for label_, fn in _MODELS}
    fits = []
    for label_, _fn in _MODELS:
        c, r2 = _fit_through_origin(xs_by_model[label_], times_ns)
        fits.append(ComplexityFit(label=label_, coefficient=c, r_squared=r2))
    fits.sort(key=lambda f: f.r_squared, reverse=True)  # stable → simpler model wins ties

    estimate = ComplexityResult(
        name=name,
        sizes=tuple(unique_sizes),
        times_ns=tuple(times_ns),
        fits=fits,
    )
    if not cfg.quiet:
        print_complexity(estimate, cfg)
    return estimate
