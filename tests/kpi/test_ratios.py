"""Unit tests for src/analytics/ratios.py (Sprint 2, Day 8 — Profitability Ratios)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    opm_cross_check,
    return_on_equity,
    ebit,
    return_on_capital_employed,
    return_on_assets,
    roce_benchmark_band,
    is_financials_sector,
    compute_profitability_ratios,
)

# ---------- Net Profit Margin ----------


def test_npm_normal():
    assert net_profit_margin(net_profit=200, sales=1000) == 20.0


def test_npm_zero_sales_returns_none():
    assert net_profit_margin(net_profit=200, sales=0) is None


def test_npm_missing_sales_returns_none():
    assert net_profit_margin(net_profit=200, sales=None) is None


# ---------- Operating Profit Margin ----------


def test_opm_normal():
    assert operating_profit_margin(operating_profit=210, sales=1000) == 21.0


def test_opm_missing_operating_profit_returns_none():
    # Mirrors PNB / ADANIENSOL real-data nulls
    assert operating_profit_margin(operating_profit=None, sales=1000) is None


def test_opm_zero_sales_returns_none():
    assert operating_profit_margin(operating_profit=210, sales=0) is None


# ---------- OPM cross-check (DQ-05) ----------


def test_opm_cross_check_within_tolerance_no_warning(caplog):
    diff = opm_cross_check(
        computed_opm=21.0, source_opm=21.5, company_id="TCS", year="2023-03"
    )
    assert diff == 0.5
    assert "OPM mismatch" not in caplog.text


def test_opm_cross_check_mismatch_logs_warning(caplog):
    diff = opm_cross_check(
        computed_opm=21.5, source_opm=3.0, company_id="XYZ", year="2022-03"
    )
    assert diff == 18.5
    assert "OPM mismatch" in caplog.text


def test_opm_cross_check_missing_source_returns_none():
    assert opm_cross_check(computed_opm=21.5, source_opm=None) is None


# ---------- Return on Equity ----------


def test_roe_normal():
    assert return_on_equity(net_profit=100, equity_capital=100, reserves=400) == 20.0


def test_roe_negative_equity_returns_none():
    assert return_on_equity(net_profit=100, equity_capital=50, reserves=-200) is None


def test_roe_zero_equity_returns_none():
    assert return_on_equity(net_profit=100, equity_capital=0, reserves=0) is None


def test_roe_missing_reserves_returns_none():
    assert return_on_equity(net_profit=100, equity_capital=50, reserves=None) is None


# ---------- EBIT / ROCE ----------


def test_ebit_normal():
    assert ebit(operating_profit=500, depreciation=100) == 400


def test_ebit_missing_depreciation_treated_as_zero():
    assert ebit(operating_profit=500, depreciation=None) == 500


def test_ebit_missing_operating_profit_returns_none():
    assert ebit(operating_profit=None, depreciation=100) is None


def test_roce_normal():
    # EBIT=400, capital employed = 100+400+500=1000 -> 40%
    assert (
        return_on_capital_employed(
            ebit_value=400, equity_capital=100, reserves=400, borrowings=500
        )
        == 40.0
    )


def test_roce_zero_capital_employed_returns_none():
    assert (
        return_on_capital_employed(
            ebit_value=400, equity_capital=0, reserves=0, borrowings=0
        )
        is None
    )


def test_roce_financials_sector_band():
    assert roce_benchmark_band("Financials") == (12.0, 22.0)


def test_roce_universal_band_for_non_financials():
    assert roce_benchmark_band("Information Technology") == (15.0, 25.0)


def test_is_financials_sector():
    assert is_financials_sector("Financials") is True
    assert is_financials_sector("Energy") is False
    assert is_financials_sector(None) is False


# ---------- Return on Assets ----------


def test_roa_normal():
    assert return_on_assets(net_profit=100, total_assets=2000) == 5.0


def test_roa_zero_total_assets_returns_none():
    # Mirrors SBIN: zero balance sheet rows -> total_assets unavailable
    assert return_on_assets(net_profit=100, total_assets=0) is None


def test_roa_missing_total_assets_returns_none():
    assert return_on_assets(net_profit=100, total_assets=None) is None


# ---------- End-to-end row computation ----------


def test_compute_profitability_ratios_normal_row():
    row = {
        "company_id": "TCS",
        "year": "2023-03",
        "sales": 225458,
        "net_profit": 34990,
        "operating_profit": 48534,
        "opm_percentage": 21.5,
        "depreciation": 5800,
        "equity_capital": 366,
        "reserves": 81000,
        "borrowings": 0,
        "total_assets": 95000,
        "broad_sector": "Information Technology",
    }
    result = compute_profitability_ratios(row)
    assert result["company_id"] == "TCS"
    assert round(result["net_profit_margin_pct"], 2) == round(34990 / 225458 * 100, 2)
    assert result["is_financials_sector"] is False
    assert result["return_on_equity_pct"] is not None
    assert result["return_on_capital_employed_pct"] is not None


def test_compute_profitability_ratios_handles_sbin_style_missing_bs():
    # SBIN: zero balance-sheet rows -> equity_capital/reserves/total_assets all None
    row = {
        "company_id": "SBIN",
        "year": "2023-03",
        "sales": 400000,
        "net_profit": 50000,
        "operating_profit": 90000,
        "opm_percentage": 22.0,
        "depreciation": 4000,
        "equity_capital": None,
        "reserves": None,
        "borrowings": None,
        "total_assets": None,
        "broad_sector": "Financials",
    }
    result = compute_profitability_ratios(row)
    # P&L-only ratios still compute...
    assert result["net_profit_margin_pct"] is not None
    assert result["operating_profit_margin_pct"] is not None
    # ...but every BS-anchored ratio is None, as documented in PROGRESS.md
    assert result["return_on_equity_pct"] is None
    assert result["return_on_capital_employed_pct"] is None
    assert result["return_on_assets_pct"] is None
    assert result["is_financials_sector"] is True
