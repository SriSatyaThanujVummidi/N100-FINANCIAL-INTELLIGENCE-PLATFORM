"""
Financial Ratio Engine — CAGR (Compound Annual Growth Rate) Engine (Sprint 2, Day 10)

Implements the CAGR formula and its 6 documented edge cases (spec Section
23.1), used for Revenue, PAT (net profit), and EPS growth across 3yr, 5yr,
and 10yr windows.

CAGR % = ((end_value / start_value) ** (1 / n_years) - 1) * 100

Edge case handling (spec Section 23.1), generalised to cover every sign
combination of (start_value, end_value):

  start     end       result                flag
  --------  --------  --------------------  ----------------
  zero      any       None                  ZERO_BASE
  positive  positive  computed normally     None
  positive  zero/neg  None                  DECLINE_TO_LOSS
  negative  positive  None                  TURNAROUND
  negative  zero/neg  None                  BOTH_NEGATIVE
  missing   any       None                  INSUFFICIENT
  any       missing   None                  INSUFFICIENT

Note: the spec's decision table only lists strictly-negative end values for
DECLINE_TO_LOSS and strictly-negative start values for BOTH_NEGATIVE. An
end value of exactly zero isn't explicitly listed there, so this module
extends the same flag to that case (a company whose profit drops to exactly
zero is "declining to a loss" in spirit -- not meaningfully different from
one rupee of profit turning into a one-rupee loss). This is a documented
interpretation, not a literal requirement from the spec table.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

CAGR_WINDOWS = (3, 5, 10)

# Flags worth surfacing in ratio_edge_cases.log (Day 13/14 deliverable).
# INSUFFICIENT is deliberately excluded -- it's expected and common for
# short-history companies (e.g. JIOFIN) and would flood the log with noise
# that isn't a real anomaly.
NOTABLE_FLAGS = {"ZERO_BASE", "DECLINE_TO_LOSS", "TURNAROUND", "BOTH_NEGATIVE"}


def cagr(
    start_value: Optional[float],
    end_value: Optional[float],
    n_years: int,
) -> tuple[Optional[float], Optional[str]]:
    """Core CAGR formula with the 6 documented edge cases.

    Returns (cagr_pct, flag). flag is None only when a value was actually
    computed; every None value is accompanied by a flag explaining why.
    """
    if n_years is None or n_years <= 0:
        return None, "INSUFFICIENT"
    if start_value is None or end_value is None:
        return None, "INSUFFICIENT"

    if start_value == 0:
        return None, "ZERO_BASE"

    if start_value > 0:
        if end_value > 0:
            return ((end_value / start_value) ** (1 / n_years) - 1) * 100, None
        return None, "DECLINE_TO_LOSS"

    # start_value < 0
    if end_value > 0:
        return None, "TURNAROUND"
    return None, "BOTH_NEGATIVE"


def shift_fiscal_year(year_str: str, n_years: int) -> str:
    """Shift a normalised 'YYYY-MM' year label back by n_years, keeping the
    company's fiscal year-end month unchanged (e.g. '2024-03' - 5 ->
    '2019-03'; '2024-12' - 3 -> '2021-12' for Dec year-end companies)."""
    year, month = year_str.split("-")
    return f"{int(year) - n_years:04d}-{month}"


def compute_cagr_window(
    time_series: dict[str, Optional[float]],
    latest_year: str,
    window_years: int,
) -> tuple[Optional[float], Optional[str]]:
    """Look up the start/end values for one CAGR window from a
    {year: value} time series and compute CAGR + flag.

    INSUFFICIENT if either the latest year or the exact start year is
    missing from the series (gap years, <n years of history, or a company
    with fewer years than the window requires -- e.g. JIOFIN's 2-3yr
    history can never produce a 5yr or 10yr CAGR)."""
    if latest_year not in time_series:
        return None, "INSUFFICIENT"
    end_value = time_series.get(latest_year)

    start_year = shift_fiscal_year(latest_year, window_years)
    if start_year not in time_series:
        return None, "INSUFFICIENT"
    start_value = time_series.get(start_year)

    return cagr(start_value, end_value, window_years)


def compute_growth_metrics(
    company_id: str,
    latest_year: str,
    sales_series: dict[str, Optional[float]],
    net_profit_series: dict[str, Optional[float]],
    eps_series: dict[str, Optional[float]],
) -> dict:
    """Compute Revenue, PAT, and EPS CAGR (+ flag) for 3yr/5yr/10yr windows
    for one company, anchored on `latest_year`.

    Each *_series is a {year: value} dict built from that company's full
    profitandloss history (sales/net_profit/eps respectively). Produces 18
    columns: {revenue,pat,eps}_cagr_{3,5,10}yr and the matching _flag column.
    """
    result: dict = {"company_id": company_id, "year": latest_year}

    metric_series = {
        "revenue": sales_series,
        "pat": net_profit_series,
        "eps": eps_series,
    }

    for prefix, series in metric_series.items():
        for window in CAGR_WINDOWS:
            value, flag = compute_cagr_window(series, latest_year, window)
            result[f"{prefix}_cagr_{window}yr"] = value
            result[f"{prefix}_cagr_{window}yr_flag"] = flag
            if flag in NOTABLE_FLAGS:
                logger.warning(
                    "CAGR edge case company_id=%s year=%s metric=%s window=%dyr flag=%s",
                    company_id,
                    latest_year,
                    prefix,
                    window,
                    flag,
                )

    return result
