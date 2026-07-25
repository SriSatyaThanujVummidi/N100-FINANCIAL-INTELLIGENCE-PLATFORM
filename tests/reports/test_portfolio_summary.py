import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.reports.portfolio_summary import trend_arrow, is_implausible_pct


def test_trend_arrow_up_higher_is_better():
    assert trend_arrow(120, 100, "higher") == "up"


def test_trend_arrow_down_higher_is_better():
    assert trend_arrow(80, 100, "higher") == "down"


def test_trend_arrow_flat_within_band():
    assert trend_arrow(101, 100, "higher") == "flat"
    assert trend_arrow(99, 100, "higher") == "flat"


def test_trend_arrow_up_lower_is_better():
    # D/E dropping from 1.0 to 0.8 is an IMPROVEMENT -> arrow should be up
    assert trend_arrow(0.8, 1.0, "lower") == "up"


def test_trend_arrow_down_lower_is_better():
    # D/E rising from 1.0 to 1.5 is a DECLINE -> arrow should be down
    assert trend_arrow(1.5, 1.0, "lower") == "down"


def test_trend_arrow_missing_latest_returns_na():
    assert trend_arrow(None, 100, "higher") == "na"


def test_trend_arrow_missing_prior_returns_na():
    assert trend_arrow(100, None, "higher") == "na"


def test_trend_arrow_zero_base_nonzero_latest():
    assert trend_arrow(50, 0, "higher") == "up"
    assert trend_arrow(-50, 0, "higher") == "down"


def test_trend_arrow_zero_base_zero_latest():
    assert trend_arrow(0, 0, "higher") == "flat"


def test_is_implausible_pct():
    assert is_implausible_pct(600.0) is True
    assert is_implausible_pct(25.0) is False
