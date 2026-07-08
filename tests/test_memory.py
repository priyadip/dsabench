"""Unit tests for bench.memory — tracemalloc wrapper and RSS probe."""

from __future__ import annotations

import tracemalloc

from bench.memory import MemoryTracker, get_process_rss


def test_tracker_detects_allocation():
    with MemoryTracker() as trk:
        block = bytearray(512 * 1024)  # 512 KB
        assert block is not None
    stats = trk.as_stats()
    assert stats.peak_bytes >= 400 * 1024


def test_tracker_peak_nonnegative_after_free():
    with MemoryTracker() as trk:
        tmp = [0] * 50_000
        del tmp
    stats = trk.as_stats()
    assert stats.peak_bytes >= 0
    assert stats.current_bytes >= 0


def test_tracker_delta_reflects_retained_memory():
    keep = []
    with MemoryTracker() as trk:
        keep.append(bytearray(256 * 1024))
    stats = trk.as_stats()
    assert stats.delta_bytes >= 200 * 1024
    del keep


def test_tracker_stops_tracemalloc_it_started():
    assert not tracemalloc.is_tracing()
    with MemoryTracker():
        assert tracemalloc.is_tracing()
    assert not tracemalloc.is_tracing()


def test_tracker_respects_existing_tracing():
    tracemalloc.start()
    try:
        with MemoryTracker():
            pass
        assert tracemalloc.is_tracing()  # did not stop what it didn't start
    finally:
        tracemalloc.stop()


def test_as_stats_carries_process_rss():
    with MemoryTracker() as trk:
        pass
    stats = trk.as_stats(process_rss_bytes=12345)
    assert stats.process_rss_bytes == 12345


def test_get_process_rss_plausible():
    rss = get_process_rss()
    # On Linux this should resolve via /proc; allow None for exotic platforms.
    if rss is not None:
        assert rss > 1024 * 1024  # more than 1 MB for a CPython process
