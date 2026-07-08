"""Custom exceptions raised by the :mod:`bench` package.

All exceptions inherit from :class:`BenchError` so callers can catch a single
base class when they want to handle any bench-related failure.
"""

from __future__ import annotations

__all__ = [
    "BenchError",
    "ConfigurationError",
    "ExportError",
    "GraphError",
]


class BenchError(Exception):
    """Base class for every error raised by the bench package."""


class ConfigurationError(BenchError):
    """Raised when invalid configuration values or options are supplied."""


class ExportError(BenchError):
    """Raised when a result cannot be exported (bad format, IO failure, ...)."""


class GraphError(BenchError):
    """Raised when a plot cannot be produced (missing matplotlib, no data)."""
