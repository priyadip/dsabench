"""Formatting helpers and user-code detection used across the package."""

from __future__ import annotations

import math
import os
import sys
import sysconfig
from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Any

__all__ = [
    "format_time_ns",
    "format_bytes",
    "safe_repr",
    "format_args",
    "is_user_file",
    "describe_location",
]

_INTERACTIVE_PREFIXES = ("<ipython", "<stdin", "<string")


def format_time_ns(value_ns: float | None, precision: int = 3) -> str:
    """Render a nanosecond duration with an automatically chosen unit.

    Args:
        value_ns: Duration in nanoseconds (``None``/NaN renders as an em dash).
        precision: Number of decimal places.

    Returns:
        A human-readable string such as ``"1.234 ms"``.
    """
    if value_ns is None or (isinstance(value_ns, float) and math.isnan(value_ns)):
        return "—"
    value = float(value_ns)
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000_000:
        return f"{sign}{value / 1_000_000_000:.{precision}f} s"
    if value >= 1_000_000:
        return f"{sign}{value / 1_000_000:.{precision}f} ms"
    if value >= 1_000:
        return f"{sign}{value / 1_000:.{precision}f} µs"
    return f"{sign}{value:.{precision}f} ns"


def format_bytes(value: int | float | None, precision: int = 2) -> str:
    """Render a byte count with an automatically chosen binary unit.

    Args:
        value: Size in bytes (``None`` renders as an em dash).
        precision: Decimal places for KB and above (bytes always show 0).

    Returns:
        A human-readable string such as ``"1.50 MB"``.
    """
    if value is None:
        return "—"
    size = float(value)
    sign = "-" if size < 0 else ""
    size = abs(size)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024.0 or unit == "GB":
            if unit == "B":
                return f"{sign}{size:.0f} B"
            return f"{sign}{size:.{precision}f} {unit}"
        size /= 1024.0
    return f"{sign}{size:.{precision}f} TB"  # pragma: no cover - defensive


def safe_repr(value: Any, max_length: int = 80) -> str:
    """Return ``repr(value)`` guarded against raising and truncated.

    Args:
        value: Any object.
        max_length: Maximum returned length (must be at least 8; longer
            reprs are truncated with an ellipsis).

    Returns:
        A repr string never longer than *max_length*.
    """
    try:
        text = repr(value)
    except Exception as exc:  # noqa: BLE001 - user __repr__ may raise anything
        text = f"<unrepresentable {type(value).__name__}: {type(exc).__name__}>"
    if len(text) > max_length:
        return text[: max_length - 1] + "…"
    return text


def format_args(
    args: Sequence[Any] = (),
    kwargs: Mapping[str, Any] | None = None,
    max_length: int = 80,
) -> str:
    """Render a call's arguments as ``(a, b, key=value)``.

    Args:
        args: Positional arguments.
        kwargs: Keyword arguments.
        max_length: Maximum length of the final string.

    Returns:
        A truncated, human-readable argument list including parentheses.
    """
    parts = [safe_repr(a, max_length) for a in args]
    for key, val in (kwargs or {}).items():
        parts.append(f"{key}={safe_repr(val, max_length)}")
    text = "(" + ", ".join(parts) + ")"
    if len(text) > max_length:
        return text[: max_length - 2] + "…)"
    return text


@lru_cache(maxsize=1)
def _system_prefixes() -> tuple[str, ...]:
    """Return normalised path prefixes considered non-user code."""
    prefixes: set[str] = set()
    for key in ("stdlib", "platstdlib", "purelib", "platlib"):
        try:
            path = sysconfig.get_path(key)
        except (KeyError, OSError):  # pragma: no cover - platform specific
            path = None
        if path:
            prefixes.add(os.path.normcase(os.path.abspath(path)))
    for prefix in (sys.prefix, sys.exec_prefix, getattr(sys, "base_prefix", sys.prefix)):
        if prefix:
            prefixes.add(os.path.normcase(os.path.abspath(prefix)))
    # The bench package itself is never "user code".
    prefixes.add(os.path.normcase(os.path.dirname(os.path.abspath(__file__))))
    return tuple(sorted(prefixes, key=len, reverse=True))


@lru_cache(maxsize=4096)
def is_user_file(filename: str) -> bool:
    """Return ``True`` when *filename* looks like user-authored code.

    Interactive sources (``<ipython-...>``, ``<stdin>``, ``<string>``) count
    as user code; other pseudo-files (``<frozen ...>``) and anything living
    under the interpreter/site-packages prefixes (including this package) do
    not.

    Args:
        filename: A code object's ``co_filename``.

    Returns:
        ``True`` for user code, ``False`` otherwise.
    """
    if not filename:
        return False
    if filename.startswith("<"):
        return filename.startswith(_INTERACTIVE_PREFIXES)
    path = os.path.normcase(os.path.abspath(filename))
    for prefix in _system_prefixes():
        if path == prefix or path.startswith(prefix + os.sep):
            return False
    return True


def describe_location(filename: str, lineno: int) -> str:
    """Return a compact ``file.py:lineno`` location string.

    Args:
        filename: Source file path (or pseudo-filename).
        lineno: Line number.

    Returns:
        ``"basename:lineno"``.
    """
    return f"{os.path.basename(filename)}:{lineno}"
