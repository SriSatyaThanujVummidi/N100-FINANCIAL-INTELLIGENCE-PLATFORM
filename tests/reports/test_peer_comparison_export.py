"""Sandbox tests for Day 20 percentile colour-coding thresholds."""

from src.reports.peer_comparison_export import (
    GREEN_FILL,
    RED_FILL,
    YELLOW_FILL,
    _percentile_fill,
)


def test_high_percentile_green():
    assert _percentile_fill(0.75) == GREEN_FILL
    assert _percentile_fill(0.9) == GREEN_FILL


def test_low_percentile_red():
    assert _percentile_fill(0.25) == RED_FILL
    assert _percentile_fill(0.1) == RED_FILL


def test_mid_percentile_yellow():
    assert _percentile_fill(0.5) == YELLOW_FILL


def test_missing_percentile_no_fill():
    assert _percentile_fill(None) is None
    import numpy as np

    assert _percentile_fill(np.nan) is None
