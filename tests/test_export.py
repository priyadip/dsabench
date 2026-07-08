"""Tests for bench.export — JSON/CSV/Markdown serialisation."""

from __future__ import annotations

import csv
import io
import json

import pytest

import bench
from bench import run
from bench.exceptions import ExportError
from bench.export import export_result, to_csv, to_json, to_markdown


def _result():
    return run(lambda: sum(range(50)), repeat=2, warmup=0, label="workload")


def _comparison():
    return bench.compare(("A", lambda: 1), ("B", lambda: 2), repeat=1, warmup=0)


def _complexity():
    return bench.estimate_complexity(
        lambda n: sum(range(n)), sizes=[10, 20, 40], repeat=1, warmup=0
    )


def test_to_json_round_trip():
    data = json.loads(to_json(_result()))
    assert data["name"] == "workload"
    assert data["timing"]["average_ns"] > 0
    assert data["mode"] == "default"


def test_to_csv_result_parses():
    rows = list(csv.reader(io.StringIO(to_csv(_result()))))
    assert rows[0] == ["metric", "value"]
    metrics = {r[0] for r in rows[1:]}
    assert {"name", "timing.average_ns", "memory.peak_bytes"} <= metrics


def test_to_csv_comparison_ranked_rows():
    rows = list(csv.reader(io.StringIO(to_csv(_comparison()))))
    header, first = rows[0], rows[1]
    assert "rank" in header and "average_ns" in header
    assert first[header.index("rank")] == "1"


def test_to_markdown_contains_tables():
    md = to_markdown(_result())
    assert "|" in md and "Metric" in md
    md_cmp = to_markdown(_comparison())
    assert "Rank" in md_cmp


def test_to_markdown_complexity():
    md = to_markdown(_complexity())
    assert "n" in md and "O(" in md


@pytest.mark.parametrize("suffix", [".json", ".csv", ".md", ".markdown"])
def test_export_result_suffix_inference(tmp_path, suffix):
    path = export_result(_result(), tmp_path / f"out{suffix}")
    assert path.exists()
    assert path.read_text(encoding="utf-8").strip()


def test_export_result_explicit_format_overrides_suffix(tmp_path):
    path = export_result(_result(), tmp_path / "data.txt", format="json")
    json.loads(path.read_text(encoding="utf-8"))


def test_export_unknown_suffix_raises(tmp_path):
    with pytest.raises(ExportError):
        export_result(_result(), tmp_path / "out.xml")


def test_export_creates_parent_dirs(tmp_path):
    path = export_result(_result(), tmp_path / "deep" / "nested" / "out.json")
    assert path.exists()


def test_auto_export_via_configure(tmp_path):
    bench.configure(export="json", export_dir=str(tmp_path))
    bench.bench(lambda: 7, repeat=1, warmup=0)
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert "lambda" in data["name"]


def test_auto_export_sanitises_names(tmp_path):
    bench.configure(export="json", export_dir=str(tmp_path))
    bench.bench(lambda: 1, repeat=1, warmup=0, label="weird name/§!")
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    assert "/" not in files[0].name.replace(str(tmp_path), "")


def test_complexity_export_json():
    data = json.loads(to_json(_complexity()))
    assert data["sizes"] == [10, 20, 40]
    assert data["best"].startswith("O(")  # best is serialised as its label
    assert data["fits"][0]["label"] == data["best"]
