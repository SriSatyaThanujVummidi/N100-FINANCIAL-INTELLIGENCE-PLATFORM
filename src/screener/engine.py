"""Screener filter engine — Sprint 3, Day 15/16.

Loads thresholds from config/screener_config.yaml and applies them against
financial_ratios, joined with profitandloss (net_profit, sales) and
market_cap (pe, pb, dividend_yield, market_cap_crore, ev_ebitda).

Design decisions documented in PROGRESS.md:

Day 15:
- Debt-free = total_debt_cr == 0 (tolerance), NOT null interest_coverage.
  A null ICR with real debt outstanding is treated as missing data.
- Fiscal year (financial_ratios.year, e.g. "2024-03") is mapped to the
  market_cap calendar year by taking the fiscal year-end's calendar year
  (e.g. "2024-03" -> 2024) — closest annual snapshot available.
- revenue_cagr_3yr is not in financial_ratios; computed on demand via
  src/analytics/cagr.py for the Turnaround Watch preset only.
- load_screener_universe() joins each company to its OWN latest
  financial_ratios row (per-company MAX(year)) rather than filtering to
  one shared year string — SIEMENS reports on a September fiscal
  year-end for its entire history and would otherwise be silently
  dropped from every screen (a real AC-01 coverage gap).

Day 16:
- apply_filters()'s D/E handling has two distinct modes:
  (a) MAX-filter carve-out (op in "<", "<="): Financials companies pass
      the D/E condition unconditionally, since high leverage is
      structurally normal for lenders (spec Module 3, feature 3.1).
      Used by Quality Compounder, Value Pick, Growth Accelerator.
  (b) exclude_sectors: some presets (Debt-Free Blue Chip) need Financials
      EXCLUDED ENTIRELY rather than carved out — D/E is structurally
      meaningless for lenders/insurers, and auto-passing them via the
      carve-out would let a high-leverage bank pass a screen literally
      named "Debt-Free Blue Chip". These two modes are mutually exclusive
      per-call (exclude_sectors, when set, disables the carve-out).
- rank_by in screener_config.yaml is a metric KEY (e.g. 'dividend_yield'),
  not necessarily the real DataFrame column (e.g. 'dividend_yield_pct') —
  translated through config['metrics'] before both filtering-result
  column access and final sort.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

logger = logging.getLogger(__name__)

DB_PATH = Path("data/nifty100.db")
CONFIG_PATH = Path("config/screener_config.yaml")

_OPS = {
    ">": lambda s, v: s > v,
    "<": lambda s, v: s < v,
    ">=": lambda s, v: s >= v,
    "<=": lambda s, v: s <= v,
    "==": lambda s, v: s == v,
}


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load screener_config.yaml. Raises FileNotFoundError with a clear message if missing."""
    if not path.exists():
        raise FileNotFoundError(f"screener_config.yaml not found at {path.resolve()}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fiscal_year_to_calendar_year(fiscal_year: str) -> int | None:
    """Map financial_ratios.year ('YYYY-MM') to market_cap.year (calendar int).

    Uses the fiscal year-end's calendar year, e.g. '2024-03' -> 2024.
    Returns None if the string can't be parsed (defensive — should not happen
    post-ETL, but screener must not crash on a bad row).
    """
    try:
        return int(fiscal_year.split("-")[0])
    except (AttributeError, ValueError, IndexError):
        logger.warning(
            "Could not parse fiscal year for calendar mapping: %r", fiscal_year
        )
        return None


def get_latest_year(
    conn: sqlite3.Connection,
    table: str = "financial_ratios",
    min_coverage: int = 50,
) -> str:
    """Return the most recent year string with real company coverage.

    Day 15 finding: a plain MAX(year) string comparison is unsafe — year is
    stored as text ('YYYY-MM'), and a fiscal-year-end like SIEMENS's '-09'
    can lexicographically outrank '-03' even when only 1 company reports
    on it. min_coverage filters those out: take the latest year with at
    least min_coverage companies reporting, not just the latest string.
    Not currently called by load_screener_universe() (which uses a
    per-company latest-year join instead), kept here for any future code
    path that needs a single shared snapshot year.
    """
    df = pd.read_sql_query(
        f"SELECT year, COUNT(*) AS company_count FROM {table} "
        f"GROUP BY year ORDER BY year DESC",
        conn,
    )
    if df.empty:
        raise ValueError(f"No rows found in {table} — cannot determine latest year")

    covered = df[df["company_count"] >= min_coverage]
    if covered.empty:
        logger.warning(
            "No year in %s has >= %d companies; falling back to year with max coverage: %s",
            table,
            min_coverage,
            df.loc[df["company_count"].idxmax(), "year"],
        )
        return df.loc[df["company_count"].idxmax(), "year"]

    return covered.iloc[0]["year"]


def load_screener_universe(
    conn: sqlite3.Connection,
    year: str | None = None,
) -> pd.DataFrame:
    """Build the full screener universe.

    Default mode (year=None): pulls each company's OWN most recent
    financial_ratios row, rather than one shared fiscal-year string.

    Day 15 finding: SIEMENS reports on a September fiscal year-end for its
    entire 14-year history and has zero rows under '2024-03' (or any
    March-labeled year). A single global year filter therefore silently
    drops SIEMENS from every screen — a real AC-01 coverage gap, not a
    data quality issue (confirmed via day15_diagnose_fiscal_years.py:
    HCLTECH/SHREECEM used June FY-end 2013-2015 only; NESTLEIND/AMBUJACEM/
    EICHERMOT/BOSCHLTD/ABB use December FY-end, matching spec Section 23's
    own NESTLEIND example). Per-company latest-year join fixes this for
    all four fiscal-year-end conventions at once.

    Pass an explicit year (e.g. '2024-03') for single fiscal-year snapshot
    mode — used later if a screen needs one common reporting date.
    """
    if year is not None:
        fr = pd.read_sql_query(
            "SELECT * FROM financial_ratios WHERE year = ?", conn, params=(year,)
        )
        if fr.empty:
            raise ValueError(f"No financial_ratios rows for year={year!r}")
    else:
        fr = pd.read_sql_query(
            """
            SELECT fr.* FROM financial_ratios fr
            INNER JOIN (
                SELECT company_id, MAX(year) AS latest_year
                FROM financial_ratios GROUP BY company_id
            ) latest
            ON fr.company_id = latest.company_id AND fr.year = latest.latest_year
            """,
            conn,
        )

    sectors = pd.read_sql_query(
        "SELECT company_id, broad_sector, sub_sector FROM sectors", conn
    )

    # Full profitandloss, joined on (company_id, year) per-row. Must NOT be
    # filtered to one year now that fr rows carry different fiscal years
    # per company (Mar/Jun/Sep/Dec).
    pl = pd.read_sql_query(
        "SELECT company_id, year, net_profit, sales FROM profitandloss", conn
    )

    df = fr.merge(sectors, on="company_id", how="left")
    df = df.merge(pl, on=["company_id", "year"], how="left")

    # calendar_year mapping is now per-row (each row can carry a different
    # fiscal year), not one global value.
    df["calendar_year"] = df["year"].apply(fiscal_year_to_calendar_year)

    mc = pd.read_sql_query(
        "SELECT company_id, year AS calendar_year, market_cap_crore, pe_ratio, "
        "pb_ratio, ev_ebitda, dividend_yield_pct FROM market_cap",
        conn,
    )
    df = df.merge(mc, on=["company_id", "calendar_year"], how="left")

    df["is_debt_free"] = df["total_debt_cr"].abs() < 0.01
    df["fcf_yield_pct"] = (
        df["free_cash_flow_cr"] / df["market_cap_crore"].replace(0, pd.NA)
    ) * 100

    return df


def apply_single_filter(
    df: pd.DataFrame,
    metric_col: str,
    op: str,
    value: float,
    icr_metric: bool = False,
) -> pd.Series:
    """Return a boolean mask for one filter condition.

    icr_metric=True applies the debt-free-always-passes rule for ICR-min
    filters specifically (op in ('>', '>=')). A null ICR with real debt
    outstanding fails the filter (missing data, not a pass).
    """
    if op not in _OPS:
        raise ValueError(f"Unsupported operator: {op!r}")

    condition = _OPS[op](df[metric_col], value)

    if icr_metric and op in (">", ">="):
        condition = condition | df["is_debt_free"]

    # NaN comparisons are always False in pandas — that's already the
    # correct "missing data fails the filter" behaviour, no extra handling.
    return condition.fillna(False)


def apply_filters(
    df: pd.DataFrame,
    filters: list[dict[str, Any]],
    config: dict[str, Any],
    exclude_sectors: list[str] | None = None,
) -> pd.DataFrame:
    """Apply a list of {metric, op, value} filters, with the D/E-Financials
    max-filter carve-out and ICR-debt-free handling baked in.

    Day 16 regression fix: an earlier edit that scoped the D/E carve-out to
    max-type operators only accidentally dropped the elif/else branches for
    every other metric (icr, roe, fcf, etc.) — those filters were silently
    doing nothing (mask stayed all-True for them). Caught via the sandbox
    regression suite (test_icr_missing_data_fails_min_filter,
    test_combined_filters_roe_and_de) before it reached real preset output.
    Full if/elif/else structure restored below.

    exclude_sectors (Day 16, Debt-Free Blue Chip): unlike the D/E carve-out
    (which lets Financials PASS a max filter regardless of value, since
    high leverage is normal for them), some presets need to EXCLUDE
    Financials entirely — a bank at D/E=6 auto-passing a screen literally
    named "Debt-Free Blue Chip" via the carve-out defeats the preset's
    purpose. D/E is structurally meaningless for lenders/insurers, so they
    shouldn't be scored on it at all here, not given a free pass. When
    exclude_sectors is set, the D/E carve-out is disabled for this call
    (the two modes are mutually exclusive).
    """
    metrics_map = config["metrics"]

    working_df = df
    if exclude_sectors:
        working_df = df[~df["broad_sector"].isin(exclude_sectors)]

    mask = pd.Series(True, index=working_df.index)

    for f in filters:
        metric_key, op, value = f["metric"], f["op"], f["value"]
        col = metrics_map[metric_key]

        if metric_key == "de" and not exclude_sectors:
            de_mask = apply_single_filter(working_df, col, op, value)
            # Financials carve-out (spec Module 3, 3.1) only applies to
            # D/E MAX filters (e.g. D/E < 2.0) — the intent is "don't
            # penalise Financials for structurally high leverage". It must
            # NOT apply to equality checks like an exact D/E == 0 (that
            # blanket-passed every Financials company regardless of real
            # D/E — PFC D/E=8.52, PNB D/E=3.68 both slipped into a
            # "debt-free" screen before this scoping fix, confirmed via
            # day16_diagnose_debtfree.py against raw balancesheet.xlsx
            # borrowings).
            if op in ("<", "<="):
                is_financials = working_df["broad_sector"] == "Financials"
                combined = de_mask | is_financials
                mask &= combined.fillna(False)
            else:
                mask &= de_mask.fillna(False)

        elif metric_key == "icr":
            mask &= apply_single_filter(working_df, col, op, value, icr_metric=True)

        else:
            mask &= apply_single_filter(working_df, col, op, value)

    return working_df[mask].copy()


def rank_and_sort(df: pd.DataFrame, rank_by: str) -> pd.DataFrame:
    """Sort descending by the preset's rank_by column. NaNs sink to the bottom."""
    if rank_by not in df.columns:
        raise KeyError(f"rank_by column {rank_by!r} not found in screener universe")
    return df.sort_values(by=rank_by, ascending=False, na_position="last").reset_index(
        drop=True
    )


def run_custom_screen(
    df: pd.DataFrame,
    filters: list[dict[str, Any]],
    rank_by: str,
    config: dict[str, Any],
    exclude_sectors: list[str] | None = None,
) -> pd.DataFrame:
    """Public entry point: apply filters, then sort by rank_by.

    Day 16 bug fix: rank_by in screener_config.yaml is a metric KEY
    (e.g. 'dividend_yield'), not necessarily the real DataFrame column
    (e.g. 'dividend_yield_pct'). Translate through config['metrics'] first;
    fall back to using rank_by as-is for computed columns not in the
    metrics map (e.g. fcf_yield_pct, which is derived in
    load_screener_universe() and has no metric-key alias).
    """
    filtered = apply_filters(df, filters, config, exclude_sectors=exclude_sectors)
    resolved_rank_by = config["metrics"].get(rank_by, rank_by)
    return rank_and_sort(filtered, resolved_rank_by)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    with sqlite3.connect(DB_PATH) as conn:
        universe = load_screener_universe(conn)
        year_counts = universe["year"].value_counts().sort_index(ascending=False)
        print(f"Screener universe loaded: {len(universe)} companies")
        print(f"Fiscal year distribution (top 5): \n{year_counts.head().to_string()}")
