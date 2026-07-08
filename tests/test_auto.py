"""Tests for bench.auto — automatic benchmarking of user functions."""

from __future__ import annotations

import json
import sys

import bench
from bench.auto import AutoBench


def test_auto_records_user_calls():
    bench.auto(live=False)

    def workload():
        return sum(range(200))

    workload()
    workload()
    report = bench.stop_auto(print_summary=False)
    rec = next(r for r in report.records if "workload" in r.name)
    assert rec.calls == 2
    assert rec.total_wall_ns > 0
    assert rec.min_wall_ns <= rec.max_wall_ns


def test_auto_excludes_stdlib():
    bench.auto(live=False)
    json.dumps({"k": [1, 2, 3]})
    report = bench.stop_auto(print_summary=False)
    assert all("json" not in r.location for r in report.records)


def test_auto_restores_previous_profile_hook():
    prev = sys.getprofile()
    bench.auto(live=False)
    bench.stop_auto(print_summary=False)
    assert sys.getprofile() is prev


def test_auto_replaces_active_instance():
    first = bench.auto(live=False)
    second = bench.auto(live=False)
    assert not first.active
    assert second.active
    bench.stop_auto(print_summary=False)


def test_auto_include_filter():
    bench.auto(live=False, include=["wanted*"])

    def wanted_fn():
        return 1

    def unwanted_fn():
        return 2

    wanted_fn()
    unwanted_fn()
    report = bench.stop_auto(print_summary=False)
    names = [r.name for r in report.records]
    assert any("wanted_fn" in n for n in names)
    assert not any("unwanted_fn" in n for n in names)


def test_auto_exclude_filter():
    bench.auto(live=False, exclude=["noisy*"])

    def noisy_fn():
        return 1

    def keep_fn():
        return 2

    noisy_fn()
    keep_fn()
    report = bench.stop_auto(print_summary=False)
    names = [r.name for r in report.records]
    assert not any("noisy_fn" in n for n in names)
    assert any("keep_fn" in n for n in names)


def test_auto_live_prints_line(capsys):
    bench.configure(quiet=False)
    bench.auto(live=True)

    def visible_fn():
        return 3

    visible_fn()
    bench.stop_auto(print_summary=False)
    assert "visible_fn" in capsys.readouterr().out


def test_stop_summary_table(capsys):
    bench.configure(quiet=False)
    bench.auto(live=False)

    def tabled_fn():
        return 4

    tabled_fn()
    bench.stop_auto(print_summary=True)
    out = capsys.readouterr().out
    assert "Auto Benchmark Summary" in out
    assert "Calls" in out and "Total" in out


def test_context_manager_form():
    with AutoBench(live=False) as ab:

        def cm_fn():
            return 5

        cm_fn()
    assert not ab.active
    report = ab.last_report
    assert report is not None
    assert any("cm_fn" in r.name for r in report.records)


def test_stop_auto_when_inactive_returns_none():
    assert bench.stop_auto(print_summary=False) is None
