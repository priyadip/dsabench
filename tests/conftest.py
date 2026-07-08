"""Shared fixtures: every test runs with a fresh, quiet, colorless config."""

from __future__ import annotations

import pytest

import bench


@pytest.fixture(autouse=True)
def clean_config():
    """Reset global state around every test."""
    bench.reset_config()
    bench.configure(quiet=True, color=False)
    yield
    bench.stop_auto(print_summary=False)
    bench.reset_config()
