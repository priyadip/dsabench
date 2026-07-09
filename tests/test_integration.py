"""End-to-end integration tests across the public API."""

from __future__ import annotations

import json

import bench


def test_version_and_all():
    assert bench.__version__ == "0.2.1"
    for name in bench.__all__:
        assert hasattr(bench, name), f"missing export {name}"


def test_spec_quickstart_flow(capsys):
    bench.configure(quiet=False)

    def solve(a, b):
        return a + b

    answer = bench.bench(solve, 20, 22, repeat=2, warmup=0)
    assert answer == 42
    assert "Benchmark Report" in capsys.readouterr().out


def test_configure_applies_globally():
    bench.configure(repeat=3, warmup=0)
    r = bench.run(lambda: 1)
    assert len(r.timing.runs_ns) == 3


def test_compare_then_export(tmp_path):
    cmp = bench.compare(
        ("Sum", lambda: sum(range(500))),
        ("Loop", lambda: [x for x in range(500)] and 0),
        repeat=2,
        warmup=0,
    )
    path = bench.export_result(cmp, tmp_path / "cmp.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["entries"]) == 2


def test_decorator_and_manual_agree():
    def work(n):
        return sum(range(n))

    manual = bench.run(work, args=(1_000,), repeat=2, warmup=0)
    decorated = bench.benchmark(repeat=2, warmup=0)(work)
    assert decorated(1_000) == manual.return_value


def test_full_pipeline_result_to_all_formats(tmp_path):
    r = bench.run(lambda: 99, repeat=2, warmup=0, label="pipeline")
    for suffix in (".json", ".csv", ".md"):
        out = bench.export_result(r, tmp_path / f"r{suffix}")
        assert out.exists()
