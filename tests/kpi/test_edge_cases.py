"""Day 13 unit tests — edge case cross-checks and sanity bounds."""

import pytest
from analytics.edge_cases import (
    flag_implausible_ratio,
    categorize_anomaly,
    roce_cross_check,
    roe_cross_check,
)

# ---------- flag_implausible_ratio() ----------


def test_flag_implausible_ratio_normal_value_not_flagged():
    assert flag_implausible_ratio("return_on_equity_pct", 45.0) is False


def test_flag_implausible_ratio_hal_style_extreme_roe_flagged():
    # HAL's documented ~147x equity discrepancy produces ROE in the
    # thousands of percent
    assert flag_implausible_ratio("return_on_equity_pct", 1200.0) is True


def test_flag_implausible_ratio_hal_style_extreme_asset_turnover_flagged():
    # Day 9 finding: HAL's Asset Turnover came out to 67.5x
    assert flag_implausible_ratio("asset_turnover", 67.5) is True


def test_flag_implausible_ratio_normal_asset_turnover_not_flagged():
    assert flag_implausible_ratio("asset_turnover", 1.7) is False


def test_flag_implausible_ratio_none_value_not_flagged():
    assert flag_implausible_ratio("return_on_equity_pct", None) is False


def test_flag_implausible_ratio_unknown_metric_not_flagged():
    assert flag_implausible_ratio("some_unrelated_metric", 99999.0) is False


def test_flag_implausible_ratio_extreme_negative_flagged():
    assert flag_implausible_ratio("return_on_equity_pct", -800.0) is True


# ---------- categorize_anomaly() ----------


def test_categorize_anomaly_missing_value_is_data_source_issue():
    assert (
        categorize_anomaly(diff_pct=999, computed_value=None, source_value=50.0)
        == "data source issue"
    )


def test_categorize_anomaly_implausible_computed_value_is_data_source_issue():
    # HAL-style: computed value itself is outside sanity bounds
    assert (
        categorize_anomaly(diff_pct=1000, computed_value=1200.0, source_value=12.0)
        == "data source issue"
    )


def test_categorize_anomaly_tcs_style_tiny_source_value():
    # Documented spec case: companies.xlsx roe_percentage=0.52 for TCS,
    # computed ROE ~50% -- source field itself looks like a formatting bug
    assert (
        categorize_anomaly(diff_pct=49.48, computed_value=50.0, source_value=0.52)
        == "data source issue"
    )


def test_categorize_anomaly_sign_flip_is_formula_discrepancy():
    assert (
        categorize_anomaly(diff_pct=30, computed_value=15.0, source_value=-15.0)
        == "formula discrepancy"
    )


def test_categorize_anomaly_small_diff_is_version_difference():
    assert (
        categorize_anomaly(diff_pct=12, computed_value=22.0, source_value=18.0)
        == "version difference"
    )


def test_categorize_anomaly_large_diff_same_sign_is_formula_discrepancy():
    assert (
        categorize_anomaly(diff_pct=35, computed_value=45.0, source_value=10.0)
        == "formula discrepancy"
    )


# ---------- roce_cross_check() ----------


def test_roce_cross_check_within_tolerance_returns_none():
    result = roce_cross_check(
        "TCS", "2024-03", computed_roce_pct=60.0, source_roce_pct=64.3
    )
    assert result is None


def test_roce_cross_check_exceeds_tolerance_returns_record():
    result = roce_cross_check(
        "DEMO", "2024-03", computed_roce_pct=30.0, source_roce_pct=10.0
    )
    assert result is not None
    assert result["company_id"] == "DEMO"
    assert result["metric"] == "ROCE"
    assert result["diff_pct"] == pytest.approx(20.0)
    assert result["category"] in (
        "version difference",
        "formula discrepancy",
        "data source issue",
    )


def test_roce_cross_check_missing_computed_returns_record():
    result = roce_cross_check(
        "SBIN", "2024-03", computed_roce_pct=None, source_roce_pct=15.0
    )
    assert result is not None
    assert result["category"] == "data source issue"
    assert result["diff_pct"] is None


def test_roce_cross_check_hal_style_flagged_as_data_source_issue():
    result = roce_cross_check(
        "HAL", "2024-03", computed_roce_pct=1500.0, source_roce_pct=18.0
    )
    assert result is not None
    assert result["category"] == "data source issue"


# ---------- roe_cross_check() ----------


def test_roe_cross_check_within_tolerance_returns_none():
    result = roe_cross_check(
        "INFY", "2024-03", computed_roe_pct=29.8, source_roe_pct=27.0
    )
    assert result is None


def test_roe_cross_check_tcs_documented_anomaly():
    # Exact documented spec case (Section 5.1): TCS source roe_percentage=0.52
    result = roe_cross_check(
        "TCS", "2024-03", computed_roe_pct=50.94, source_roe_pct=0.52
    )
    assert result is not None
    assert result["category"] == "data source issue"
    assert result["computed_value"] == 50.94
    assert result["source_value"] == 0.52
