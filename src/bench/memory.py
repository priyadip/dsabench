"""Heap and process memory measurement.

Heap usage is measured with :mod:`tracemalloc`, which tracks Python-level
allocations only (fast and portable, but blind to raw C allocations).
Process resident set size (RSS) is obtained best-effort from ``psutil``,
``/proc/self/status``, or :mod:`resource`, in that order.
"""

from __future__ import annotations

import sys
import tracemalloc
from types import TracebackType

from .types import MemoryStats

__all__ = ["MemoryTracker", "get_process_rss"]


class MemoryTracker:
    """Context manager measuring heap usage of the enclosed block.

    Starts :mod:`tracemalloc` if it is not already tracing (and stops it
    again only if it started it), resets the peak counter, and reports peak,
    current, and delta usage relative to the entry baseline.

    Example:
        >>> with MemoryTracker() as tracker:
        ...     data = [0] * 100_000
        >>> tracker.peak_bytes > 0
        True
    """

    __slots__ = ("_baseline", "_started_tracing", "peak_bytes", "current_bytes", "delta_bytes")

    def __init__(self) -> None:
        self._baseline = 0
        self._started_tracing = False
        self.peak_bytes = 0
        self.current_bytes = 0
        self.delta_bytes = 0

    def __enter__(self) -> MemoryTracker:
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            self._started_tracing = True
        current, _peak = tracemalloc.get_traced_memory()
        self._baseline = current
        tracemalloc.reset_peak()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        current, peak = tracemalloc.get_traced_memory()
        self.peak_bytes = max(0, peak - self._baseline)
        self.current_bytes = max(0, current)
        self.delta_bytes = current - self._baseline
        if self._started_tracing:
            tracemalloc.stop()
            self._started_tracing = False

    def as_stats(self, process_rss_bytes: int | None = None) -> MemoryStats:
        """Return the collected numbers as a :class:`bench.types.MemoryStats`.

        Args:
            process_rss_bytes: Optional process RSS to attach.

        Returns:
            A populated :class:`bench.types.MemoryStats`.
        """
        return MemoryStats(
            peak_bytes=self.peak_bytes,
            current_bytes=self.current_bytes,
            delta_bytes=self.delta_bytes,
            process_rss_bytes=process_rss_bytes,
        )


def get_process_rss() -> int | None:
    """Return the current process resident set size in bytes, if knowable.

    Tries ``psutil`` first, then ``/proc/self/status`` (Linux), then
    :func:`resource.getrusage`. Returns ``None`` when no method works.
    """
    try:  # psutil, if the user happens to have it installed
        import psutil  # type: ignore[import-not-found]

        return int(psutil.Process().memory_info().rss)
    except Exception:  # noqa: BLE001 - any failure just falls through
        pass

    try:  # Linux procfs
        with open("/proc/self/status", encoding="ascii", errors="ignore") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
    except OSError:
        pass

    try:  # POSIX resource module (ru_maxrss is peak, closest available proxy)
        import resource

        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            return int(rss)  # macOS reports bytes
        return int(rss) * 1024  # Linux reports kilobytes
    except Exception:  # noqa: BLE001
        return None
    return None
