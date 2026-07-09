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
from .report import print_complexity, print_space_complexity
from .types import ComplexityFit, ComplexityResult, SpaceComplexityResult

__all__ = [
    "estimate_complexity",
    "estimate_space_complexity",
    "COMPLEXITY_MODELS",
    "const",
    "poly",
    "polylog",
    "loglog",
    "exp_base",
    "factorial",
    "raised",
    "compose",
]

Model = Callable[[float], float]


def const(k: float = 1.0) -> Model:
    """``k`` — a flat model, for O(1)-style baselines."""
    return lambda n: k


def poly(power: float) -> Model:
    """``n**power`` — e.g. ``poly(2)`` is O(n²), ``poly(0.5)`` is O(√n)."""
    return lambda n: n**power


def polylog(power: float, log_power: float = 1.0) -> Model:
    """``n**power * log2(n)**log_power``, e.g. O(n⁴log²n) via ``polylog(4, 2)``."""

    def f(n: float) -> float:
        if n <= 1:
            return n**power
        return n**power * math.log2(n) ** log_power

    return f


def loglog() -> Model:
    """``log2(log2(n))`` — the iterated logarithm, O(log log n)."""
    return lambda n: math.log2(math.log2(n)) if n > 2 else 1.0


def exp_base(base: float) -> Model:
    """``base**n`` — e.g. ``exp_base(2)`` is O(2ⁿ), ``exp_base(math.e)`` is O(eⁿ)."""
    return lambda n: base**n


def factorial() -> Model:
    """``n!`` via the Gamma function — O(n!), for permutation-style brute force."""
    return lambda n: math.gamma(n + 1.0)


def raised(base: Model, exponent: Model) -> Model:
    """``base(n) ** exponent(n)`` — compose a variable base *and* exponent.

    Lets you build models where the exponent itself grows with n, e.g.
    O(n^(2·n!)) via ``raised(poly(1), compose(const(2), factorial()))``.
    """
    return lambda n: base(n) ** exponent(n)


def compose(*models: Model) -> Model:
    """Multiply several component models together, e.g. ``compose(poly(4), polylog(0, 2))``."""

    def f(n: float) -> float:
        result = 1.0
        for model in models:
            result *= model(n)
        return result

    return f


#: The built-in candidate models fitted by :func:`estimate_complexity` when
#: ``models`` is omitted. Import this to extend rather than replace it:
#: ``models=COMPLEXITY_MODELS + [("O(n⁴log²n)", polylog(4, 2))]``.
COMPLEXITY_MODELS: list[tuple[str, Model]] = [
    ("O(1)", const(1.0)),
    ("O(log log n)", loglog()),
    ("O(log n)", lambda n: math.log2(n) if n > 1 else 1.0),
    ("O(n)", poly(1)),
    ("O(n log n)", lambda n: n * math.log2(n) if n > 1 else n),
    ("O(n²)", poly(2)),
    ("O(n³)", poly(3)),
    ("O(2ⁿ)", exp_base(2.0)),
    ("O(3ⁿ)", exp_base(3.0)),
    ("O(eⁿ)", exp_base(math.e)),
    ("O(n!)", factorial()),
]


def _safe_model_values(fn: Model, sizes: Sequence[int]) -> list[float] | None:
    """Evaluate *fn* at every size, or ``None`` if it overflows/diverges.

    Fast-growing or custom-composed models can exceed float range well
    within reach of everyday benchmarks (``170!`` already overflows). Such
    a model isn't a viable candidate at that scale, so it's dropped rather
    than crashing the whole estimate.
    """
    values: list[float] = []
    for n in sizes:
        try:
            v = fn(float(n))
        except (OverflowError, ValueError, ZeroDivisionError):
            return None
        if not math.isfinite(v):
            return None
        values.append(v)
    return values


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


def _fit_candidates(
    name: str,
    sizes: Sequence[int],
    measured: Sequence[float],
    models: Sequence[tuple[str, Model]] | None,
) -> list[ComplexityFit]:
    """Fit every candidate model against *measured* values, ranked by R².

    Shared by :func:`estimate_complexity` and :func:`estimate_space_complexity`
    — *measured* is either per-size timings or per-size peak memory.
    """
    candidates = models if models is not None else COMPLEXITY_MODELS
    fits = []
    for label_, fn in candidates:
        xs = _safe_model_values(fn, sizes)
        if xs is None:
            continue  # overflows or diverges at these sizes — not viable here
        c, r2 = _fit_through_origin(xs, measured)
        fits.append(ComplexityFit(label=label_, coefficient=c, r_squared=r2))
    if not fits:
        raise BenchError(
            f"{name}: every candidate model overflowed or diverged at sizes {list(sizes)}"
        )
    fits.sort(key=lambda f: f.r_squared, reverse=True)  # stable → simpler model wins ties
    return fits


def estimate_complexity(
    func: Callable[..., Any],
    sizes: Sequence[int],
    *,
    args_for: Callable[[int], Any] | None = None,
    repeat: int = 3,
    warmup: int = 1,
    quiet: bool | None = None,
    label: str | None = None,
    models: Sequence[tuple[str, Model]] | None = None,
) -> ComplexityResult:
    """Estimate the asymptotic time complexity of *func* empirically.

    Example:
        >>> from bench import estimate_complexity
        >>> est = estimate_complexity(sorted_scan, sizes=[1_000, 5_000,
        ...                           20_000, 80_000])       # doctest: +SKIP
        >>> est.best.label                                    # doctest: +SKIP
        'O(n)'

    Any Python callable ``n -> float`` is a valid candidate model, so exotic
    or composite shapes are supported via the builders in this module::

        >>> from bench.complexity import COMPLEXITY_MODELS, polylog
        >>> custom = COMPLEXITY_MODELS + [("O(n⁴log²n)", polylog(4, 2))]
        >>> est = estimate_complexity(f, sizes=[...], models=custom)  # doctest: +SKIP

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
        models: Candidate ``(label, fn)`` pairs to fit against, replacing
            the built-in :data:`COMPLEXITY_MODELS`. Any model that
            overflows or diverges at the given sizes is silently excluded
            rather than raising.

    Returns:
        A :class:`bench.types.ComplexityResult` with fits ranked best-first.

    Raises:
        BenchError: If fewer than three distinct sizes (or any size < 1)
            are supplied, if the function fails on some size, or if every
            candidate model overflows/diverges at the given sizes.
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

    fits = _fit_candidates(name, unique_sizes, times_ns, models)

    estimate = ComplexityResult(
        name=name,
        sizes=tuple(unique_sizes),
        times_ns=tuple(times_ns),
        fits=fits,
    )
    if not cfg.quiet:
        print_complexity(estimate, cfg)
    return estimate


def estimate_space_complexity(
    func: Callable[..., Any],
    sizes: Sequence[int],
    *,
    args_for: Callable[[int], Any] | None = None,
    warmup: int = 0,
    quiet: bool | None = None,
    label: str | None = None,
    models: Sequence[tuple[str, Model]] | None = None,
) -> SpaceComplexityResult:
    """Estimate the asymptotic *space* (peak memory) complexity of *func*.

    Same fitting machinery as :func:`estimate_complexity` — candidate models,
    the ``models=`` override, and the overflow guard all behave identically —
    but each size is measured for peak traced heap usage (via
    :mod:`tracemalloc`, one instrumented call per size) instead of wall time.

    Example:
        >>> from bench import estimate_space_complexity
        >>> est = estimate_space_complexity(build_table, sizes=[100, 200,
        ...                                 400, 800, 1600])  # doctest: +SKIP
        >>> est.best.label                                    # doctest: +SKIP
        'O(n²)'

    Args:
        func: The function under test.
        sizes: At least three distinct positive input sizes. Spread them
            over an order of magnitude or more for a trustworthy fit.
        args_for: Maps a size ``n`` to the call arguments. Defaults to
            passing ``n`` itself; a non-tuple return value is wrapped as a
            single argument.
        warmup: Untimed warmup runs before the single instrumented call
            (lets caches/memoisation tables settle if that's the scenario
            you're measuring; default 0 measures a true cold call).
        quiet: Suppress the printed report.
        label: Display name override.
        models: Candidate ``(label, fn)`` pairs to fit against, replacing
            the built-in :data:`COMPLEXITY_MODELS`.

    Returns:
        A :class:`bench.types.SpaceComplexityResult` with fits ranked
        best-first.

    Raises:
        BenchError: If fewer than three distinct sizes (or any size < 1)
            are supplied, if the function fails on some size, or if every
            candidate model overflows/diverges at the given sizes.
    """
    unique_sizes = sorted(set(int(s) for s in sizes))
    if len(unique_sizes) < 3:
        raise BenchError("estimate_space_complexity() needs at least 3 distinct sizes")
    if unique_sizes[0] < 1:
        raise BenchError("sizes must be >= 1")

    cfg = get_config().merged(quiet=quiet)
    name = label or getattr(func, "__qualname__", None) or getattr(func, "__name__", "function")

    peak_bytes: list[float] = []
    for n in unique_sizes:
        call_args = args_for(n) if args_for else (n,)
        if not isinstance(call_args, tuple):
            call_args = (call_args,)
        result = run(
            func,
            call_args,
            config=cfg.merged(memory=True, profile=False, cpu=False, mode="fast"),
            repeat=1,
            warmup=max(0, warmup),
            label=name,
        )
        if result.exception is not None or result.memory is None:
            detail = result.exception.message if result.exception else "no memory captured"
            raise BenchError(f"{name} failed at n={n}: {detail}")
        peak_bytes.append(float(result.memory.peak_bytes))

    fits = _fit_candidates(name, unique_sizes, peak_bytes, models)

    estimate = SpaceComplexityResult(
        name=name,
        sizes=tuple(unique_sizes),
        peak_bytes=tuple(peak_bytes),
        fits=fits,
    )
    if not cfg.quiet:
        print_space_complexity(estimate, cfg)
    return estimate
