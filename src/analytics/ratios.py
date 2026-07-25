"""
Financial Ratio Engine — Profitability Ratios (Sprint 2, Day 8)

Implements: Net Profit Margin, Operating Profit Margin (+ source cross-check),
Return on Equity, Return on Capital Employed (with Financials sector-relative
benchmark), and Return on Assets.

Rule carried forward from Sprint 1 (see PROGRESS.md): the source
`opm_percentage` field is unreliable (diverges by orders of magnitude for
~216 rows / 21 companies). This module ALWAYS computes OPM from raw fields
(operating_profit / sales) for downstream use. opm_cross_check() exists only
to detect and log divergence — it never overrides the computed value.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

FINANCIALS_SECTOR_NAME = "Financials"

# Universal (non-financial) ROCE benchmark band, per spec Section 13 / 28.
UNIVERSAL_ROCE_BAND = (15.0, 25.0)

# Sector-relative ROCE benchmark band for Financials (banks/NBFC/insurance),
# per spec Section 28 — D/E and ROCE behave structurally differently here.
FINANCIALS_ROCE_BAND = (12.0, 22.0)


def net_profit_margin(
    net_profit: Optional[float], sales: Optional[float]
) -> Optional[float]:
    """NPM % = net_profit / sales * 100. None if sales is 0/None or net_profit is None."""
    if sales is None or sales == 0:
        return None
    if net_profit is None:
        return None
    return (net_profit / sales) * 100


def operating_profit_margin(
    operating_profit: Optional[float], sales: Optional[float]
) -> Optional[float]:
    """OPM % = operating_profit / sales * 100 (always computed, never read from source).
    None if sales is 0/None or operating_profit is None (e.g. PNB, ADANIENSOL nulls)."""
    if sales is None or sales == 0:
        return None
    if operating_profit is None:
        return None
    return (operating_profit / sales) * 100


def opm_cross_check(
    computed_opm: Optional[float],
    source_opm: Optional[float],
    company_id: str = "",
    year: str = "",
    tolerance: float = 1.0,
) -> Optional[float]:
    """DQ-05: compare computed OPM vs source opm_percentage field.

    Returns the absolute difference (for logging/auditing only) or None if
    either side is unavailable. The computed value is always what gets used
    downstream — this function never changes that, it only flags divergence.
    """
    if computed_opm is None or source_opm is None:
        return None
    diff = abs(computed_opm - source_opm)
    if diff > tolerance:
        logger.warning(
            "OPM mismatch company_id=%s year=%s computed=%.2f source=%.2f diff=%.2f",
            company_id,
            year,
            computed_opm,
            source_opm,
            diff,
        )
    return diff


def return_on_equity(
    net_profit: Optional[float],
    equity_capital: Optional[float],
    reserves: Optional[float],
) -> Optional[float]:
    """ROE % = net_profit / (equity_capital + reserves) * 100.
    None if equity_capital/reserves missing, or equity+reserves <= 0 (negative equity).
    """
    if equity_capital is None or reserves is None:
        return None
    equity = equity_capital + reserves
    if equity <= 0:
        return None
    if net_profit is None:
        return None
    return (net_profit / equity) * 100


def ebit(
    operating_profit: Optional[float], depreciation: Optional[float]
) -> Optional[float]:
    """EBIT = operating_profit - depreciation. Missing depreciation is treated as 0
    (D&A not separately reported for some companies); missing operating_profit -> None.
    """
    if operating_profit is None:
        return None
    dep = depreciation if depreciation is not None else 0
    return operating_profit - dep


def is_financials_sector(broad_sector: Optional[str]) -> bool:
    """Is financials sector."""
    return broad_sector == FINANCIALS_SECTOR_NAME


def roce_benchmark_band(broad_sector: Optional[str]) -> tuple[float, float]:
    """Returns the (low, high) ROCE benchmark band to use for this company.
    Financials get a sector-relative band; everyone else gets the universal band."""
    if is_financials_sector(broad_sector):
        return FINANCIALS_ROCE_BAND
    return UNIVERSAL_ROCE_BAND


def return_on_capital_employed(
    ebit_value: Optional[float],
    equity_capital: Optional[float],
    reserves: Optional[float],
    borrowings: Optional[float],
) -> Optional[float]:
    """ROCE % = EBIT / (equity_capital + reserves + borrowings) * 100.
    None if capital employed <= 0, or equity/EBIT data missing."""
    if equity_capital is None or reserves is None:
        return None
    borrow = borrowings if borrowings is not None else 0
    capital_employed = equity_capital + reserves + borrow
    if capital_employed <= 0:
        return None
    if ebit_value is None:
        return None
    return (ebit_value / capital_employed) * 100


def return_on_assets(
    net_profit: Optional[float], total_assets: Optional[float]
) -> Optional[float]:
    """ROA % = net_profit / total_assets * 100. None if total_assets is 0/None."""
    if total_assets is None or total_assets == 0:
        return None
    if net_profit is None:
        return None
    return (net_profit / total_assets) * 100


def compute_profitability_ratios(row: dict) -> dict:
    """Compute all Day-8 profitability KPIs for one company-year row.

    Expected keys in `row` (missing/None values are handled gracefully,
    consistent with known source gaps -- SBIN has no balance sheet at all,
    HAL's balance sheet starts in 2016, PNB/ADANIENSOL have null
    operating_profit/opm_percentage for some years):

      company_id, year, sales, net_profit, operating_profit, opm_percentage,
      depreciation, equity_capital, reserves, borrowings, total_assets,
      broad_sector
    """
    company_id = row.get("company_id")
    year = row.get("year")
    sales = row.get("sales")
    net_profit = row.get("net_profit")
    op_profit = row.get("operating_profit")
    source_opm = row.get("opm_percentage")
    depreciation = row.get("depreciation")
    equity_capital = row.get("equity_capital")
    reserves = row.get("reserves")
    borrowings = row.get("borrowings")
    total_assets = row.get("total_assets")
    broad_sector = row.get("broad_sector")

    npm = net_profit_margin(net_profit, sales)
    opm_computed = operating_profit_margin(op_profit, sales)
    opm_diff = opm_cross_check(opm_computed, source_opm, company_id, year)
    roe = return_on_equity(net_profit, equity_capital, reserves)
    ebit_value = ebit(op_profit, depreciation)
    roce = return_on_capital_employed(ebit_value, equity_capital, reserves, borrowings)
    roa = return_on_assets(net_profit, total_assets)
    band_low, band_high = roce_benchmark_band(broad_sector)

    return {
        "company_id": company_id,
        "year": year,
        "net_profit_margin_pct": npm,
        "operating_profit_margin_pct": opm_computed,
        "opm_source_pct": source_opm,
        "opm_diff_vs_source": opm_diff,
        "return_on_equity_pct": roe,
        "ebit_cr": ebit_value,
        "return_on_capital_employed_pct": roce,
        "roce_benchmark_low": band_low,
        "roce_benchmark_high": band_high,
        "is_financials_sector": is_financials_sector(broad_sector),
        "return_on_assets_pct": roa,
    }


# ============================================================
# Day 9 — Leverage & Efficiency Ratios
# ============================================================


def debt_to_equity(
    borrowings: Optional[float],
    equity_capital: Optional[float],
    reserves: Optional[float],
) -> Optional[float]:
    """D/E = borrowings / (equity_capital + reserves).
    Returns 0.0 (not None) if borrowings = 0 (debt-free). None if
    equity_capital/reserves/borrowings missing (e.g. SBIN — no balance
    sheet at all), or if equity+reserves <= 0 (same convention as
    return_on_equity)."""
    if equity_capital is None or reserves is None:
        return None
    if borrowings is None:
        return None
    if borrowings == 0:
        return 0.0
    equity = equity_capital + reserves
    if equity <= 0:
        return None
    return borrowings / equity


def high_leverage_flag(de_ratio: Optional[float], broad_sector: Optional[str]) -> bool:
    """True if D/E > 5 and the company is NOT in the Financials sector
    (banks/NBFCs structurally run high leverage — see roce_benchmark_band)."""
    if de_ratio is None:
        return False
    if is_financials_sector(broad_sector):
        return False
    return de_ratio > 5


def interest_coverage_ratio(
    operating_profit: Optional[float],
    other_income: Optional[float],
    interest: Optional[float],
) -> tuple[Optional[float], Optional[str]]:
    """ICR = (operating_profit + other_income) / interest.
    Returns (icr_value, icr_label). interest = 0 -> (None, "Debt Free").
    operating_profit/interest missing -> (None, None) (e.g. PNB,
    ADANIENSOL nulls). Missing other_income is treated as 0."""
    if operating_profit is None or interest is None:
        return None, None
    if interest == 0:
        return None, "Debt Free"
    income = other_income if other_income is not None else 0
    return (operating_profit + income) / interest, None


def icr_risk_flag(icr_value: Optional[float]) -> bool:
    """True if ICR < 1.5 — at risk of not covering interest payments."""
    if icr_value is None:
        return False
    return icr_value < 1.5


def net_debt(
    borrowings: Optional[float], investments: Optional[float]
) -> Optional[float]:
    """Net Debt = borrowings - investments (investments used as liquid-
    asset proxy). None if borrowings missing (e.g. SBIN — no balance
    sheet at all). Missing investments is treated as 0."""
    if borrowings is None:
        return None
    inv = investments if investments is not None else 0
    return borrowings - inv


def asset_turnover(
    sales: Optional[float], total_assets: Optional[float]
) -> Optional[float]:
    """Asset Turnover = sales / total_assets. None if total_assets is
    0/None or sales is None."""
    if total_assets is None or total_assets == 0:
        return None
    if sales is None:
        return None
    return sales / total_assets


def compute_leverage_efficiency_ratios(row: dict) -> dict:
    """Compute all Day-9 leverage & efficiency KPIs for one company-year row.

    Expected keys in `row` (missing/None values handled gracefully,
    consistent with known source gaps -- SBIN has no balance sheet at all,
    PNB/ADANIENSOL have null operating_profit for some years):

      company_id, year, sales, operating_profit, other_income, interest,
      equity_capital, reserves, borrowings, investments, total_assets,
      broad_sector
    """
    company_id = row.get("company_id")
    year = row.get("year")
    sales = row.get("sales")
    op_profit = row.get("operating_profit")
    other_income = row.get("other_income")
    interest = row.get("interest")
    equity_capital = row.get("equity_capital")
    reserves = row.get("reserves")
    borrowings = row.get("borrowings")
    investments = row.get("investments")
    total_assets = row.get("total_assets")
    broad_sector = row.get("broad_sector")

    de = debt_to_equity(borrowings, equity_capital, reserves)
    high_lev = high_leverage_flag(de, broad_sector)
    icr_value, icr_label = interest_coverage_ratio(op_profit, other_income, interest)
    icr_risk = icr_risk_flag(icr_value)
    nd = net_debt(borrowings, investments)
    at = asset_turnover(sales, total_assets)

    return {
        "company_id": company_id,
        "year": year,
        "debt_to_equity": de,
        "high_leverage_flag": high_lev,
        "interest_coverage": icr_value,
        "icr_label": icr_label,
        "icr_risk_flag": icr_risk,
        "net_debt_cr": nd,
        "asset_turnover": at,
    }


def book_value_per_share(
    equity_capital: Optional[float],
    reserves: Optional[float],
    face_value: Optional[float],
) -> Optional[float]:
    """BVPS = (equity_capital + reserves) / (equity_capital / face_value).
    The (equity_capital / face_value) term is a proxy for shares
    outstanding (spec Section 6.4 -- there's no direct share-count field
    in companies.xlsx). None if any input is missing, or if face_value/
    equity_capital is 0 (can't derive a share count from a 0 base)."""
    if equity_capital is None or reserves is None or face_value is None:
        return None
    if face_value == 0 or equity_capital == 0:
        return None
    shares_proxy = equity_capital / face_value
    return (equity_capital + reserves) / shares_proxy
