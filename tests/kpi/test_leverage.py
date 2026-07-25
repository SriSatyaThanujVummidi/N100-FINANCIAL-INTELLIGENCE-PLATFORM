"""Day 9 unit tests — leverage & efficiency ratios."""

import math
from analytics.ratios import (
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    icr_risk_flag,
    net_debt,
    asset_turnover,
    compute_leverage_efficiency_ratios,
)

# ---------- Debt-to-Equity ----------


def test_de_normal():
    assert debt_to_equity(200, 100, 400) == 0.4


def test_de_debtfree_returns_zero_not_none():
    result = debt_to_equity(0, 100, 400)
    assert result == 0.0
    assert result is not None


def test_de_missing_balance_sheet_sbin_case():
    assert debt_to_equity(None, None, None) is None


def test_de_missing_reserves_only():
    # Same convention as return_on_equity: reserves missing -> None
    assert debt_to_equity(100, 200, None) is None


def test_de_missing_borrowings_only():
    assert debt_to_equity(None, 100, 400) is None


def test_de_negative_total_equity_returns_none():
    assert debt_to_equity(100, 10, -50) is None


# ---------- High Leverage Flag ----------


def test_high_leverage_flag_true_for_non_financial():
    assert high_leverage_flag(6.2, "Industrials") is True


def test_high_leverage_flag_false_for_financials_even_if_high():
    assert high_leverage_flag(8.0, "Financials") is False


def test_high_leverage_flag_false_when_de_below_threshold():
    assert high_leverage_flag(2.0, "Industrials") is False


def test_high_leverage_flag_false_when_de_none():
    assert high_leverage_flag(None, "Industrials") is False


def test_high_leverage_flag_hal_anomaly_still_flags():
    # HAL's documented BS anomaly produces extreme D/E; flag still fires.
    # Correction decision is deferred to Day 13 — not handled here.
    assert high_leverage_flag(147.0, "Industrials") is True


# ---------- Interest Coverage Ratio ----------


def test_icr_normal():
    icr, label = interest_coverage_ratio(1000, 100, 200)
    assert math.isclose(icr, 5.5)
    assert label is None


def test_icr_debtfree_interest_zero():
    icr, label = interest_coverage_ratio(1000, 100, 0)
    assert icr is None
    assert label == "Debt Free"


def test_icr_missing_operating_profit_pnb_case():
    icr, label = interest_coverage_ratio(None, 100, 200)
    assert icr is None
    assert label is None


def test_icr_missing_interest_returns_none():
    icr, label = interest_coverage_ratio(1000, 100, None)
    assert icr is None
    assert label is None


def test_icr_missing_other_income_treated_as_zero():
    icr, _ = interest_coverage_ratio(1000, None, 500)
    assert icr == 2.0


def test_icr_risk_flag_true_below_threshold():
    assert icr_risk_flag(1.2) is True


def test_icr_risk_flag_false_above_threshold():
    assert icr_risk_flag(2.0) is False


def test_icr_risk_flag_false_when_icr_none():
    assert icr_risk_flag(None) is False


# ---------- Net Debt ----------


def test_net_debt_normal():
    assert net_debt(500, 200) == 300


def test_net_debt_missing_investments_treated_as_zero():
    assert net_debt(500, None) == 500


def test_net_debt_missing_borrowings_sbin_case():
    assert net_debt(None, 200) is None


def test_net_debt_negative_net_cash_position():
    assert net_debt(100, 400) == -300


# ---------- Asset Turnover ----------


def test_asset_turnover_normal():
    assert asset_turnover(1000, 500) == 2.0


def test_asset_turnover_zero_assets_returns_none():
    assert asset_turnover(1000, 0) is None


def test_asset_turnover_missing_assets_sbin_case():
    assert asset_turnover(1000, None) is None


def test_asset_turnover_missing_sales():
    assert asset_turnover(None, 500) is None


# ---------- Orchestrator ----------


def test_compute_leverage_efficiency_ratios_normal_row():
    row = {
        "company_id": "TCS",
        "year": "2024-03",
        "borrowings": 200,
        "equity_capital": 100,
        "reserves": 400,
        "broad_sector": "Industrials",
        "operating_profit": 1000,
        "other_income": 100,
        "interest": 200,
        "investments": 50,
        "sales": 5000,
        "total_assets": 2500,
    }
    result = compute_leverage_efficiency_ratios(row)
    assert result["debt_to_equity"] == 0.4
    assert result["high_leverage_flag"] is False
    assert math.isclose(result["interest_coverage"], 5.5)
    assert result["icr_label"] is None
    assert result["icr_risk_flag"] is False
    assert result["net_debt_cr"] == 150
    assert result["asset_turnover"] == 2.0


def test_compute_leverage_efficiency_ratios_sbin_case():
    row = {
        "company_id": "SBIN",
        "year": "2024-03",
        "borrowings": None,
        "equity_capital": None,
        "reserves": None,
        "broad_sector": "Financials",
        "operating_profit": 5000,
        "other_income": 200,
        "interest": 0,
        "investments": None,
        "sales": 40000,
        "total_assets": None,
    }
    result = compute_leverage_efficiency_ratios(row)
    assert result["debt_to_equity"] is None
    assert result["high_leverage_flag"] is False
    assert result["icr_label"] == "Debt Free"
    assert result["net_debt_cr"] is None
    assert result["asset_turnover"] is None


def test_compute_leverage_efficiency_ratios_pnb_case():
    row = {
        "company_id": "PNB",
        "year": "2018-03",
        "borrowings": 5000,
        "equity_capital": 800,
        "reserves": 12000,
        "broad_sector": "Financials",
        "operating_profit": None,
        "other_income": 300,
        "interest": 4000,
        "investments": 1000,
        "sales": 60000,
        "total_assets": 900000,
    }
    result = compute_leverage_efficiency_ratios(row)
    assert result["interest_coverage"] is None
    assert result["icr_label"] is None
    assert result["debt_to_equity"] is not None
    assert result["asset_turnover"] is not None
