"""Day 10 unit tests — CAGR engine."""

import pytest
from analytics.cagr import (
    cagr,
    shift_fiscal_year,
    compute_cagr_window,
    compute_growth_metrics,
)

# ---------- Core cagr() formula ----------


def test_cagr_normal():
    # Spec reference case (Section 27): base=100, end=161, n=5 -> CAGR ~10.0%
    value, flag = cagr(100, 161, 5)
    assert value == pytest.approx(10.0, abs=0.1)
    assert flag is None


def test_cagr_normal_precise_known_value():
    # 100 -> 200 over 1 year is an exact, easy-to-hand-check case: +100%
    value, flag = cagr(100, 200, 1)
    assert value == pytest.approx(100.0)
    assert flag is None


def test_cagr_zero_base():
    value, flag = cagr(0, 500, 5)
    assert value is None
    assert flag == "ZERO_BASE"


def test_cagr_decline_to_loss_negative_end():
    value, flag = cagr(100, -50, 3)
    assert value is None
    assert flag == "DECLINE_TO_LOSS"


def test_cagr_decline_to_loss_zero_end():
    # End value of exactly 0 from a positive base -- documented extension
    # of the spec's DECLINE_TO_LOSS rule (see module docstring).
    value, flag = cagr(100, 0, 3)
    assert value is None
    assert flag == "DECLINE_TO_LOSS"


def test_cagr_turnaround():
    # Spec reference case (Section 27): base=-100, end=200 -> None, TURNAROUND
    value, flag = cagr(-100, 200, 5)
    assert value is None
    assert flag == "TURNAROUND"


def test_cagr_both_negative():
    value, flag = cagr(-100, -50, 5)
    assert value is None
    assert flag == "BOTH_NEGATIVE"


def test_cagr_both_negative_zero_end():
    # End value of exactly 0 from a negative base -- documented extension,
    # same reasoning as the zero-end DECLINE_TO_LOSS case above.
    value, flag = cagr(-100, 0, 5)
    assert value is None
    assert flag == "BOTH_NEGATIVE"


def test_cagr_insufficient_missing_start():
    value, flag = cagr(None, 200, 5)
    assert value is None
    assert flag == "INSUFFICIENT"


def test_cagr_insufficient_missing_end():
    value, flag = cagr(100, None, 5)
    assert value is None
    assert flag == "INSUFFICIENT"


def test_cagr_insufficient_zero_years():
    value, flag = cagr(100, 200, 0)
    assert value is None
    assert flag == "INSUFFICIENT"


def test_cagr_insufficient_none_years():
    value, flag = cagr(100, 200, None)
    assert value is None
    assert flag == "INSUFFICIENT"


# ---------- shift_fiscal_year() ----------


def test_shift_fiscal_year_standard_march_end():
    assert shift_fiscal_year("2024-03", 5) == "2019-03"


def test_shift_fiscal_year_three_year_window():
    assert shift_fiscal_year("2024-03", 3) == "2021-03"


def test_shift_fiscal_year_december_year_end():
    # e.g. NESTLEIND's Dec fiscal year-end
    assert shift_fiscal_year("2024-12", 10) == "2014-12"


# ---------- compute_cagr_window() ----------


def test_compute_cagr_window_normal():
    series = {"2019-03": 1610, "2024-03": 3000}
    value, flag = compute_cagr_window(series, "2024-03", 5)
    expected = ((3000 / 1610) ** (1 / 5) - 1) * 100
    assert value == pytest.approx(expected)
    assert flag is None


def test_compute_cagr_window_missing_latest_year():
    series = {"2019-03": 1610}
    value, flag = compute_cagr_window(series, "2024-03", 5)
    assert value is None
    assert flag == "INSUFFICIENT"


def test_compute_cagr_window_missing_start_year_short_history():
    # JIOFIN-style case: only 2 years of history, asking for a 5yr window
    series = {"2023-03": 10, "2024-03": 12}
    value, flag = compute_cagr_window(series, "2024-03", 5)
    assert value is None
    assert flag == "INSUFFICIENT"


def test_compute_cagr_window_start_year_present_but_value_none():
    # Year exists in the series but the field itself is null in the source
    series = {"2019-03": None, "2024-03": 3000}
    value, flag = compute_cagr_window(series, "2024-03", 5)
    assert value is None
    assert flag == "INSUFFICIENT"


# ---------- compute_growth_metrics() orchestrator ----------


def test_compute_growth_metrics_full_history_all_normal():
    sales = {"2014-03": 1000, "2019-03": 1610, "2021-03": 2000, "2024-03": 3000}
    net_profit = {"2014-03": 100, "2019-03": 161, "2021-03": 200, "2024-03": 300}
    eps = {"2014-03": 10, "2019-03": 16.1, "2021-03": 20, "2024-03": 30}

    result = compute_growth_metrics("DEMO", "2024-03", sales, net_profit, eps)

    assert result["company_id"] == "DEMO"
    assert result["year"] == "2024-03"

    # 5yr revenue CAGR: 1610 -> 3000
    assert result["revenue_cagr_5yr"] == pytest.approx(
        ((3000 / 1610) ** (1 / 5) - 1) * 100
    )
    assert result["revenue_cagr_5yr_flag"] is None

    # 10yr PAT CAGR: 100 -> 300
    assert result["pat_cagr_10yr"] == pytest.approx(((300 / 100) ** (1 / 10) - 1) * 100)
    assert result["pat_cagr_10yr_flag"] is None

    # 3yr EPS CAGR: 20 -> 30
    assert result["eps_cagr_3yr"] == pytest.approx(((30 / 20) ** (1 / 3) - 1) * 100)
    assert result["eps_cagr_3yr_flag"] is None


def test_compute_growth_metrics_short_history_insufficient():
    # JIOFIN-style company: only 2 years of data -> every window is INSUFFICIENT
    sales = {"2023-03": 5000, "2024-03": 6000}
    net_profit = {"2023-03": 400, "2024-03": 500}
    eps = {"2023-03": 4.0, "2024-03": 5.0}

    result = compute_growth_metrics("JIOFIN", "2024-03", sales, net_profit, eps)

    for prefix in ("revenue", "pat", "eps"):
        for window in (3, 5, 10):
            assert result[f"{prefix}_cagr_{window}yr"] is None
            assert result[f"{prefix}_cagr_{window}yr_flag"] == "INSUFFICIENT"


def test_compute_growth_metrics_mixed_flags_across_metrics():
    # Revenue grows normally; PAT shows a turnaround (loss -> profit);
    # EPS has a zero base. All anchored on the same 5yr window.
    sales = {"2019-03": 1000, "2024-03": 2000}
    net_profit = {"2019-03": -50, "2024-03": 100}
    eps = {"2019-03": 0, "2024-03": 5}

    result = compute_growth_metrics("MIXED", "2024-03", sales, net_profit, eps)

    assert result["revenue_cagr_5yr"] is not None
    assert result["revenue_cagr_5yr_flag"] is None

    assert result["pat_cagr_5yr"] is None
    assert result["pat_cagr_5yr_flag"] == "TURNAROUND"

    assert result["eps_cagr_5yr"] is None
    assert result["eps_cagr_5yr_flag"] == "ZERO_BASE"
