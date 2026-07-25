"""Sandbox tests for Day 19 radar chart geometry and averaging logic."""

import numpy as np
import pandas as pd
import pytest

from src.reports.radar_charts import (
    close_values,
    compute_peer_average,
    compute_universe_average,
    get_axis_angles,
)


def test_get_axis_angles_closes_the_loop():
    angles = get_axis_angles(8)
    assert len(angles) == 9  # 8 axes + 1 repeated to close
    assert angles[0] == pytest.approx(angles[-1])


def test_get_axis_angles_evenly_spaced():
    angles = get_axis_angles(4)
    diffs = np.diff(angles[:-1])
    assert all(d == pytest.approx(diffs[0]) for d in diffs)


def test_close_values_repeats_first_value():
    values = [10, 20, 30]
    closed = close_values(values)
    assert closed == [10, 20, 30, 10]


@pytest.fixture
def sample_universe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "company_id": ["A", "B", "C", "D"],
            "peer_group_name": ["GroupX", "GroupX", "GroupX", None],
            "return_on_equity_pct_score": [80.0, 60.0, 40.0, 50.0],
            "return_on_capital_employed_pct_score": [70.0, 50.0, np.nan, 45.0],
            "net_profit_margin_pct_score": [60.0, 55.0, 50.0, 40.0],
            "de_score": [90.0, 70.0, 60.0, 65.0],
            "fcf_positive_flag": [100.0, 0.0, 100.0, 100.0],
            "pat_cagr_5yr_score": [55.0, 45.0, 35.0, 50.0],
            "revenue_cagr_5yr_score": [50.0, 40.0, 30.0, 60.0],
            "composite_score_sector_relative": [65.0, 55.0, 45.0, 52.0],
        }
    )


def test_peer_average_excludes_self(sample_universe):
    """A's peer average should be the mean of B and C only, not A itself."""
    avg = compute_peer_average(sample_universe, "GroupX", exclude_company_id="A")
    roe_avg = avg[0]  # ROE is first axis
    assert roe_avg == pytest.approx((60.0 + 40.0) / 2)


def test_peer_average_handles_nan_via_nanmean(sample_universe):
    """C has NaN for ROCE — the peer average for a company excluding C
    should still compute correctly from remaining real values."""
    avg = compute_peer_average(sample_universe, "GroupX", exclude_company_id="A")
    roce_avg = avg[
        1
    ]  # ROCE is second axis; only B has a value (C excluded from A's calc, C's own NaN irrelevant here)
    assert roce_avg == pytest.approx(50.0)


def test_universe_average_excludes_self(sample_universe):
    avg = compute_universe_average(sample_universe, exclude_company_id="D")
    roe_avg = avg[0]
    assert roe_avg == pytest.approx((80.0 + 60.0 + 40.0) / 3)
