"""Package configuration.

A single module-level :class:`Config` instance holds the defaults used by
:func:`bench.bench`, the :func:`bench.benchmark` decorator, and
:func:`bench.compare`. Users adjust it with :func:`configure` and read it
with :func:`get_config`; per-call keyword arguments always win over the
global configuration.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, fields, replace
from typing import Any

from .exceptions import ConfigurationError
from .types import MODE_DEFAULTS, Mode

__all__ = ["Config", "configure", "get_config", "reset_config"]

_VALID_EXPORTS = {"json", "csv", "md", "markdown"}


@dataclass(slots=True)
class Config:
    """Runtime configuration for benchmarking.

    Attributes:
        mode: Default precision mode (fast / default / accurate).
        repeat: Timed repetitions; ``None`` means "use the mode default".
        warmup: Untimed warmup runs; ``None`` means "use the mode default".
        color: Whether reports use ANSI colors.
        memory: Whether to measure heap memory (tracemalloc pass).
        cpu: Whether to measure CPU time and utilisation.
        profile: Whether to count calls/recursion/GC (profiled pass).
        quiet: Suppress printed reports (results are still returned).
        raise_exceptions: Re-raise exceptions from the target after
            reporting; when ``False`` the exception is only recorded.
        export: Automatic export format (``"json"``, ``"csv"``, ``"md"``)
            applied after every benchmark, or ``None``.
        export_dir: Directory for automatic exports.
        precision: Decimal places used in reports.
        max_repr_length: Truncation length for argument/return reprs.
        show_args: Include the argument list in reports.
    """

    mode: Mode = Mode.DEFAULT
    repeat: int | None = None
    warmup: int | None = None
    color: bool = True
    memory: bool = True
    cpu: bool = True
    profile: bool = True
    quiet: bool = False
    raise_exceptions: bool = True
    export: str | None = None
    export_dir: str = "."
    precision: int = 3
    max_repr_length: int = 80
    show_args: bool = True

    # -- resolution -----------------------------------------------------------
    def resolved_repeat(self) -> int:
        """Return the effective repetition count for the current mode."""
        return self.repeat if self.repeat is not None else MODE_DEFAULTS[self.mode][0]

    def resolved_warmup(self) -> int:
        """Return the effective warmup count for the current mode."""
        return self.warmup if self.warmup is not None else MODE_DEFAULTS[self.mode][1]

    # -- validation -------------------------------------------------------------
    def validate(self) -> None:
        """Raise :class:`ConfigurationError` if any field is invalid."""
        if self.repeat is not None and self.repeat < 1:
            raise ConfigurationError("repeat must be >= 1")
        if self.warmup is not None and self.warmup < 0:
            raise ConfigurationError("warmup must be >= 0")
        if self.precision < 0:
            raise ConfigurationError("precision must be >= 0")
        if self.max_repr_length < 8:
            raise ConfigurationError("max_repr_length must be >= 8")
        if self.export is not None and self.export.lower() not in _VALID_EXPORTS:
            valid = ", ".join(sorted(_VALID_EXPORTS))
            raise ConfigurationError(f"export must be one of: {valid} (got {self.export!r})")

    # -- derivation -------------------------------------------------------------
    def merged(self, **overrides: Any) -> Config:
        """Return a copy with non-``None`` *overrides* applied and validated.

        Args:
            **overrides: Any :class:`Config` field. ``None`` values are
                ignored so callers can pass through optional keyword
                arguments untouched. ``mode`` accepts a string.

        Returns:
            A new validated :class:`Config`.

        Raises:
            ConfigurationError: On unknown fields or invalid values.
        """
        cleaned: dict[str, Any] = {}
        valid_names = {f.name for f in fields(Config)}
        for key, value in overrides.items():
            if key not in valid_names:
                raise ConfigurationError(f"Unknown configuration option: {key!r}")
            if value is None:
                continue
            if key == "mode":
                value = Mode.from_value(value)
            cleaned[key] = value
        merged = replace(self, **cleaned)
        merged.validate()
        return merged


_lock = threading.Lock()
_config = Config()


def configure(**options: Any) -> Config:
    """Update the global configuration.

    Example:
        >>> import bench
        >>> bench.configure(repeat=100, warmup=5, color=True,
        ...                 memory=True, cpu=True, export="json")

    Args:
        **options: Any :class:`Config` field.

    Returns:
        The new global :class:`Config`.

    Raises:
        ConfigurationError: On unknown options or invalid values.
    """
    global _config
    with _lock:
        _config = _config.merged(**options)
        return _config


def get_config() -> Config:
    """Return the current global :class:`Config`."""
    return _config


def reset_config() -> Config:
    """Restore the global configuration to factory defaults."""
    global _config
    with _lock:
        _config = Config()
        return _config
