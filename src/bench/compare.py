"""Side-by-side comparison of competing implementations."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .benchmark import run
from .config import get_config
from .exceptions import BenchError
from .report import print_comparison
from .types import BenchmarkResult, ComparisonEntry, ComparisonResult
from .utils import format_args

__all__ = ["compare"]

Candidate = "Callable[..., Any] | tuple[str, Callable[..., Any]]"


def _normalise(candidate: Any, index: int) -> tuple[str, Callable[..., Any]]:
    """Return ``(name, callable)`` for a candidate spec."""
    if isinstance(candidate, tuple):
        if len(candidate) != 2 or not callable(candidate[1]):
            raise BenchError(f"Candidate #{index + 1} must be (name, callable); got {candidate!r}")
        return str(candidate[0]), candidate[1]
    if callable(candidate):
        name = getattr(candidate, "__qualname__", None) or getattr(
            candidate, "__name__", f"candidate_{index + 1}"
        )
        return name, candidate
    raise BenchError(
        f"Candidate #{index + 1} must be callable or (name, callable); got {candidate!r}"
    )


def _outputs_match(results: Sequence[BenchmarkResult]) -> bool | None:
    """Best-effort equality check across successful results."""
    ok = [r for r in results if r.exception is None]
    if len(ok) < 2:
        return None
    first = ok[0].return_value
    try:
        for other in ok[1:]:
            if not bool(first == other.return_value):
                return False
        return True
    except Exception:  # noqa: BLE001 - exotic __eq__ (e.g. ndarray) → unknown
        return None


def compare(
    *candidates: Any,
    args: Sequence[Any] = (),
    kwargs: Mapping[str, Any] | None = None,
    mode: str | None = None,
    repeat: int | None = None,
    warmup: int | None = None,
    quiet: bool | None = None,
    check_outputs: bool = True,
) -> ComparisonResult:
    """Benchmark several implementations on the same input and rank them.

    Example:
        >>> from bench import compare
        >>> result = compare(("Memo", fib_memo), ("Tabulation", fib_tab),
        ...                  args=(30,))                     # doctest: +SKIP
        >>> result.winner.name                               # doctest: +SKIP
        'Tabulation'

    Args:
        *candidates: Two or more callables, or ``(name, callable)`` pairs.
        args: Positional arguments passed to every candidate.
        kwargs: Keyword arguments passed to every candidate.
        mode: ``"fast"``, ``"default"``, or ``"accurate"``.
        repeat: Timed repetitions (overrides the mode default).
        warmup: Warmup runs (overrides the mode default).
        quiet: Suppress the printed ranking table.
        check_outputs: Verify all candidates return equal values.

    Returns:
        A :class:`bench.types.ComparisonResult` with entries ranked fastest
        first (failed candidates last).

    Raises:
        BenchError: If fewer than two candidates are given or a candidate
            spec is malformed.
    """
    if len(candidates) < 2:
        raise BenchError("compare() needs at least two candidates")

    named = [_normalise(c, i) for i, c in enumerate(candidates)]
    cfg = get_config().merged(mode=mode, repeat=repeat, warmup=warmup, quiet=quiet)

    results: list[tuple[str, BenchmarkResult]] = []
    for name, func in named:
        results.append((name, run(func, args, kwargs, config=cfg, label=name)))

    successes = [(n, r) for n, r in results if r.exception is None and r.timing is not None]
    failures = [(n, r) for n, r in results if r.exception is not None or r.timing is None]
    successes.sort(key=lambda item: item[1].timing.average_ns)  # type: ignore[union-attr]

    best_avg = successes[0][1].timing.average_ns if successes else float("nan")
    entries: list[ComparisonEntry] = []
    for rank, (name, res) in enumerate(successes, start=1):
        relative = res.timing.average_ns / best_avg if best_avg else float("nan")
        entries.append(ComparisonEntry(name=name, result=res, rank=rank, relative=relative))
    for offset, (name, res) in enumerate(failures, start=len(successes) + 1):
        entries.append(ComparisonEntry(name=name, result=res, rank=offset, relative=math.nan))

    comparison = ComparisonResult(
        entries=entries,
        args_repr=format_args(args, kwargs, cfg.max_repr_length),
        outputs_match=_outputs_match([r for _, r in results]) if check_outputs else None,
    )
    if not cfg.quiet:
        print_comparison(comparison, cfg)
    return comparison
