"""Day 11 unit tests — cash flow KPIs & capital allocation."""

import pytest
from analytics.cashflow_kpis import (
    free_cash_flow,
    cfo_pat_ratio,
    cfo_quality_label,
    cfo_quality_score,
    compute_cfo_quality_score_window,
    capex_intensity,
    fcf_conversion_rate,
    fcf_conversion_label,
    capital_allocation_pattern,
    compute_cashflow_kpis_single_year,
)

# ---------- Free Cash Flow ----------


def test_fcf_normal():
    assert free_cash_flow(1000, -400) == 600


def test_fcf_negative_allowed():
    assert free_cash_flow(200, -800) == -600


def test_fcf_missing_cfo():
    assert free_cash_flow(None, -400) is None


def test_fcf_missing_cfi():
    assert free_cash_flow(1000, None) is None


# ---------- CFO/PAT single-year ratio ----------


def test_cfo_pat_ratio_normal():
    assert cfo_pat_ratio(1000, 800) == pytest.approx(1.25)


def test_cfo_pat_ratio_pat_zero():
    assert cfo_pat_ratio(1000, 0) is None


def test_cfo_pat_ratio_missing_cfo():
    assert cfo_pat_ratio(None, 800) is None


def test_cfo_pat_ratio_missing_pat():
    assert cfo_pat_ratio(1000, None) is None


# ---------- CFO Quality label thresholds ----------


def test_cfo_quality_label_high_quality():
    assert cfo_quality_label(1.5) == "High Quality Earnings"


def test_cfo_quality_label_moderate_upper_boundary():
    assert cfo_quality_label(1.0) == "Moderate"  # >1.0 required for High Quality


def test_cfo_quality_label_moderate_lower_boundary():
    assert cfo_quality_label(0.5) == "Moderate"


def test_cfo_quality_label_accrual_risk():
    assert cfo_quality_label(0.3) == "Accrual Risk"


def test_cfo_quality_label_none():
    assert cfo_quality_label(None) is None


# ---------- CFO Quality Score averaging ----------


def test_cfo_quality_score_normal_average():
    avg, label = cfo_quality_score([1.2, 1.0, 0.8, 1.1, 0.9])
    assert avg == pytest.approx(1.0)
    assert label == "Moderate"


def test_cfo_quality_score_skips_none_years():
    avg, label = cfo_quality_score([1.2, None, 1.4, None, 1.0])
    assert avg == pytest.approx((1.2 + 1.4 + 1.0) / 3)
    assert label == "High Quality Earnings"


def test_cfo_quality_score_all_none():
    avg, label = cfo_quality_score([None, None, None])
    assert avg is None
    assert label is None


def test_compute_cfo_quality_score_window_full_history():
    cfo_series = {
        "2020-03": 100,
        "2021-03": 110,
        "2022-03": 120,
        "2023-03": 130,
        "2024-03": 140,
    }
    pat_series = {
        "2020-03": 100,
        "2021-03": 100,
        "2022-03": 100,
        "2023-03": 100,
        "2024-03": 100,
    }
    avg, label = compute_cfo_quality_score_window(cfo_series, pat_series, "2024-03")
    assert avg == pytest.approx((1.0 + 1.1 + 1.2 + 1.3 + 1.4) / 5)
    assert label == "High Quality Earnings"


def test_compute_cfo_quality_score_window_partial_history():
    # Only 3 of the 5 trailing years have data -- average over those 3
    cfo_series = {"2022-03": 50, "2023-03": 60, "2024-03": 70}
    pat_series = {"2022-03": 100, "2023-03": 100, "2024-03": 100}
    avg, label = compute_cfo_quality_score_window(cfo_series, pat_series, "2024-03")
    assert avg == pytest.approx((0.5 + 0.6 + 0.7) / 3)


def test_compute_cfo_quality_score_window_no_history():
    avg, label = compute_cfo_quality_score_window({}, {}, "2024-03")
    assert avg is None
    assert label is None


# ---------- CapEx Intensity ----------


def test_capex_intensity_asset_light():
    intensity, label = capex_intensity(-200, 10000)  # 2%
    assert intensity == pytest.approx(2.0)
    assert label == "Asset Light"


def test_capex_intensity_moderate_lower_boundary():
    intensity, label = capex_intensity(-300, 10000)  # exactly 3%
    assert intensity == pytest.approx(3.0)
    assert label == "Moderate"


def test_capex_intensity_moderate_upper_boundary():
    intensity, label = capex_intensity(-800, 10000)  # exactly 8%
    assert intensity == pytest.approx(8.0)
    assert label == "Moderate"


def test_capex_intensity_capital_intensive():
    intensity, label = capex_intensity(-1500, 10000)  # 15%
    assert intensity == pytest.approx(15.0)
    assert label == "Capital Intensive"


def test_capex_intensity_zero_sales():
    assert capex_intensity(-200, 0) == (None, None)


def test_capex_intensity_missing_sales():
    assert capex_intensity(-200, None) == (None, None)


def test_capex_intensity_missing_investing():
    assert capex_intensity(None, 10000) == (None, None)


# ---------- FCF Conversion Rate ----------


def test_fcf_conversion_rate_normal():
    assert fcf_conversion_rate(600, 1000) == pytest.approx(60.0)


def test_fcf_conversion_rate_zero_operating_profit():
    assert fcf_conversion_rate(600, 0) is None


def test_fcf_conversion_rate_missing_fcf():
    assert fcf_conversion_rate(None, 1000) is None


def test_fcf_conversion_label_efficient():
    assert fcf_conversion_label(75.0) == "Efficient"


def test_fcf_conversion_label_moderate():
    assert fcf_conversion_label(45.0) == "Moderate"


def test_fcf_conversion_label_capex_heavy():
    assert fcf_conversion_label(20.0) == "CapEx Heavy"


def test_fcf_conversion_label_none():
    assert fcf_conversion_label(None) is None


# ---------- Capital Allocation 8-Pattern Classifier ----------


def test_pattern_cash_accumulator():
    assert capital_allocation_pattern(100, 50, 50) == (
        "+",
        "+",
        "+",
        "Cash Accumulator",
    )


def test_pattern_liquidating_assets():
    assert capital_allocation_pattern(100, 50, -50) == (
        "+",
        "+",
        "-",
        "Liquidating Assets",
    )


def test_pattern_mixed():
    assert capital_allocation_pattern(100, -50, 50) == ("+", "-", "+", "Mixed")


def test_pattern_reinvestor_default():
    # CFO/PAT not provided (None) -> stays the general "Reinvestor" label
    assert capital_allocation_pattern(100, -50, -50) == ("+", "-", "-", "Reinvestor")


def test_pattern_shareholder_returns_subclassification():
    # Same (+,-,-) sign pattern, but CFO/PAT > 1.0 -> sub-classified
    assert capital_allocation_pattern(100, -50, -50, cfo_pat_ratio_value=1.5) == (
        "+",
        "-",
        "-",
        "Shareholder Returns",
    )


def test_pattern_reinvestor_low_cfo_pat_stays_reinvestor():
    assert capital_allocation_pattern(100, -50, -50, cfo_pat_ratio_value=0.8) == (
        "+",
        "-",
        "-",
        "Reinvestor",
    )


def test_pattern_distress_signal():
    assert capital_allocation_pattern(-100, 50, 50) == (
        "-",
        "+",
        "+",
        "Distress Signal",
    )


def test_pattern_distressed_deleveraging():
    assert capital_allocation_pattern(-100, 50, -50) == (
        "-",
        "+",
        "-",
        "Distressed Deleveraging",
    )


def test_pattern_growth_funded_by_debt():
    assert capital_allocation_pattern(-100, -50, 50) == (
        "-",
        "-",
        "+",
        "Growth Funded by Debt",
    )


def test_pattern_pre_revenue():
    assert capital_allocation_pattern(-100, -50, -50) == ("-", "-", "-", "Pre-Revenue")


def test_pattern_zero_treated_as_positive():
    # financing_activity = 0 -> "+" sign (judgment call documented in module)
    assert capital_allocation_pattern(100, -50, 0) == ("+", "-", "+", "Mixed")


def test_pattern_missing_data_returns_none_label():
    cfo_sign, cfi_sign, cff_sign, label = capital_allocation_pattern(None, 50, -50)
    assert cfo_sign is None
    assert cfi_sign == "+"
    assert cff_sign == "-"
    assert label is None


# ---------- Single-year orchestrator ----------


def test_compute_cashflow_kpis_single_year_normal_row():
    row = {
        "company_id": "TCS",
        "year": "2024-03",
        "operating_activity": 45000,
        "investing_activity": -10000,
        "financing_activity": -20000,
        "sales": 240000,
        "operating_profit": 60000,
        "net_profit": 46000,
    }
    result = compute_cashflow_kpis_single_year(row)
    assert result["free_cash_flow_cr"] == 35000
    assert result["capex_intensity_label"] in (
        "Asset Light",
        "Moderate",
        "Capital Intensive",
    )
    assert result["fcf_conversion_rate_pct"] == pytest.approx((35000 / 60000) * 100)
    assert result["cfo_sign"] == "+"
    assert result["cfi_sign"] == "-"
    assert result["cff_sign"] == "-"
    assert result["capital_allocation_pattern"] in ("Reinvestor", "Shareholder Returns")


def test_compute_cashflow_kpis_single_year_missing_cashflow_row():
    # SBIN-style: no cash flow data at all for this row
    row = {
        "company_id": "SBIN",
        "year": "2024-03",
        "operating_activity": None,
        "investing_activity": None,
        "financing_activity": None,
        "sales": 500000,
        "operating_profit": None,
        "net_profit": 60000,
    }
    result = compute_cashflow_kpis_single_year(row)
    assert result["free_cash_flow_cr"] is None
    assert result["capital_allocation_pattern"] is None
