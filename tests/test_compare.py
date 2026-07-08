"""Tests for bench.compare — ranked head-to-head comparisons."""

from __future__ import annotations

import time

import pytest

import bench
from bench.exceptions import BenchError


def _sleep_ms(ms):
    def f():
        time.sleep(ms / 1000)
        return ms

    f.__name__ = f.__qualname__ = f"sleep_{ms}ms"
    return f


def test_ranking_and_relative():
    cmp = bench.compare(("Slow", _sleep_ms(6)), ("Fast", _sleep_ms(1)), repeat=2, warmup=0)
    assert cmp.winner.name == "Fast"
    assert cmp.entries[0].rank == 1
    assert cmp.entries[0].relative == pytest.approx(1.0)
    assert cmp.entries[1].name == "Slow"
    assert cmp.entries[1].relative > 2.0


def test_bare_callables_autonamed():
    a, b = _sleep_ms(1), _sleep_ms(2)
    cmp = bench.compare(a, b, repeat=1, warmup=0)
    names = {e.name for e in cmp.entries}
    assert names == {"sleep_1ms", "sleep_2ms"}


def test_outputs_match_true():
    cmp = bench.compare(("A", lambda: 42), ("B", lambda: 42), repeat=1, warmup=0)
    assert cmp.outputs_match is True


def test_outputs_match_false():
    cmp = bench.compare(("A", lambda: 1), ("B", lambda: 2), repeat=1, warmup=0)
    assert cmp.outputs_match is False


def test_outputs_match_uncomparable_is_none():
    class Weird:
        def __eq__(self, other):
            raise TypeError("no compare")

    cmp = bench.compare(("A", Weird), ("B", Weird), repeat=1, warmup=0)
    assert cmp.outputs_match is None


def test_check_outputs_disabled():
    cmp = bench.compare(("A", lambda: 1), ("B", lambda: 2), repeat=1, warmup=0, check_outputs=False)
    assert cmp.outputs_match is None


def test_error_candidate_ranked_last():
    def boom():
        raise RuntimeError("x")

    cmp = bench.compare(("OK", lambda: 1), ("Boom", boom), repeat=1, warmup=0)
    assert cmp.winner.name == "OK"
    last = cmp.entries[-1]
    assert last.name == "Boom"
    assert not last.result.ok


def test_fewer_than_two_candidates_raises():
    with pytest.raises(BenchError):
        bench.compare(("Only", lambda: 1), repeat=1, warmup=0)


def test_args_forwarded_to_all():
    cmp = bench.compare(
        ("Sq", lambda n: n * n), ("Cube", lambda n: n**3), args=(3,), repeat=1, warmup=0
    )
    reprs = {e.result.return_repr for e in cmp.entries}
    assert reprs == {"9", "27"}


def test_comparison_table_prints(capsys):
    bench.configure(quiet=False)
    bench.compare(("A", _sleep_ms(1)), ("B", _sleep_ms(2)), repeat=1, warmup=0)
    out = capsys.readouterr().out
    assert "Rank" in out and "Relative" in out
    assert "baseline" in out
    assert "slower" in out


def test_to_dict_shape():
    cmp = bench.compare(("A", lambda: 1), ("B", lambda: 1), repeat=1, warmup=0)
    d = cmp.to_dict()
    assert d["outputs_match"] is True
    assert len(d["entries"]) == 2
    assert d["entries"][0]["rank"] == 1
