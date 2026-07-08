"""Unit tests for bench.config — options, validation, global state."""

from __future__ import annotations

import pytest

import bench
from bench.config import Config, configure, get_config, reset_config
from bench.exceptions import ConfigurationError
from bench.types import Mode


def test_defaults():
    cfg = Config()
    assert cfg.mode is Mode.DEFAULT
    assert cfg.repeat is None and cfg.warmup is None
    assert cfg.color and cfg.memory and cfg.cpu and cfg.profile
    assert not cfg.quiet
    assert cfg.raise_exceptions
    assert cfg.export is None


@pytest.mark.parametrize(
    ("mode", "repeat", "warmup"),
    [(Mode.FAST, 1, 0), (Mode.DEFAULT, 10, 1), (Mode.ACCURATE, 100, 5)],
)
def test_mode_default_resolution(mode, repeat, warmup):
    cfg = Config(mode=mode)
    assert cfg.resolved_repeat() == repeat
    assert cfg.resolved_warmup() == warmup


def test_explicit_repeat_overrides_mode():
    cfg = Config(mode=Mode.FAST, repeat=7, warmup=2)
    assert cfg.resolved_repeat() == 7
    assert cfg.resolved_warmup() == 2


def test_configure_spec_example():
    cfg = configure(repeat=100, warmup=5, color=True, memory=True, cpu=True, export="json")
    assert cfg.repeat == 100 and cfg.warmup == 5 and cfg.export == "json"
    assert get_config().repeat == 100


def test_configure_unknown_key_raises():
    with pytest.raises(ConfigurationError):
        configure(not_an_option=True)


def test_configure_mode_string_coercion():
    cfg = configure(mode="accurate")
    assert cfg.mode is Mode.ACCURATE


def test_configure_invalid_mode_raises():
    with pytest.raises(ConfigurationError):
        configure(mode="warp-speed")


@pytest.mark.parametrize(
    "bad",
    [
        {"repeat": 0},
        {"repeat": -3},
        {"warmup": -1},
        {"precision": -2},
        {"export": "xml"},
        {"max_repr_length": 2},
    ],
)
def test_validate_rejects_bad_values(bad):
    with pytest.raises(ConfigurationError):
        configure(**bad)


def test_merged_skips_none_and_coerces_mode():
    base = Config()
    merged = base.merged(repeat=None, mode="fast", quiet=True)
    assert merged.repeat is None
    assert merged.mode is Mode.FAST
    assert merged.quiet
    assert base.mode is Mode.DEFAULT  # original untouched


def test_reset_config_restores_defaults():
    configure(repeat=99, quiet=True)
    reset_config()
    cfg = get_config()
    assert cfg.repeat is None
    # conftest re-applies quiet=True afterwards; only assert on repeat here.


def test_public_reexports():
    assert bench.configure is configure
    assert isinstance(bench.get_config(), Config)
