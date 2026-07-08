"""Unit tests for bench.utils — formatting and file-classification helpers."""

from __future__ import annotations

import sysconfig

import pytest

from bench.utils import format_args, format_bytes, format_time_ns, is_user_file, safe_repr


@pytest.mark.parametrize(
    ("ns", "expected"),
    [
        (500, "500.000 ns"),
        (1_500, "1.500 µs"),
        (2_500_000, "2.500 ms"),
        (3_200_000_000, "3.200 s"),
        (0, "0.000 ns"),
    ],
)
def test_format_time_ns_units(ns, expected):
    assert format_time_ns(ns) == expected


def test_format_time_ns_precision():
    assert format_time_ns(1_234, precision=1) == "1.2 µs"


def test_format_time_ns_none_is_dash():
    assert format_time_ns(None) == "—"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (512, "512 B"),
        (2048, "2.00 KB"),
        (5 * 1024 * 1024, "5.00 MB"),
        (int(3.5 * 1024**3), "3.50 GB"),
        (0, "0 B"),
    ],
)
def test_format_bytes_units(value, expected):
    assert format_bytes(value) == expected


def test_format_bytes_negative():
    assert format_bytes(-2048) == "-2.00 KB"


def test_format_bytes_none_is_dash():
    assert format_bytes(None) == "—"


def test_safe_repr_truncates():
    text = safe_repr("x" * 500, max_length=20)
    assert len(text) <= 21  # includes ellipsis character
    assert text.endswith("…")


def test_safe_repr_survives_broken_repr():
    class Broken:
        def __repr__(self):
            raise RuntimeError("nope")

    assert "unrepresentable" in safe_repr(Broken()).lower() or safe_repr(Broken())


def test_format_args_positional_and_kw():
    text = format_args((1, "ab"), {"k": 3})
    assert "1" in text and "'ab'" in text and "k=3" in text


def test_format_args_empty():
    assert format_args((), {}) == "()"


def test_is_user_file_accepts_repl_sources():
    assert is_user_file("<ipython-input-3-abc>")
    assert is_user_file("<stdin>")
    assert is_user_file("<string>")


def test_is_user_file_rejects_frozen_and_stdlib():
    assert not is_user_file("<frozen importlib._bootstrap>")
    stdlib = sysconfig.get_paths()["stdlib"]
    assert not is_user_file(f"{stdlib}/json/__init__.py")


def test_is_user_file_rejects_bench_itself():
    import bench.utils as mod

    assert not is_user_file(mod.__file__)


def test_is_user_file_accepts_this_test(tmp_path):
    target = tmp_path / "user_algo.py"
    target.write_text("x = 1\n")
    assert is_user_file(str(target))
