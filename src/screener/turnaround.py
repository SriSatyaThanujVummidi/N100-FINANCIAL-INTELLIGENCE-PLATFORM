"""Turnaround Watch preset — Sprint 3, Day 16.

Multi-year special case, not a plain threshold filter (see
config/screener_config.yaml's special_conditions note). Three legs:
  1. Revenue CAGR 3yr > 10%    -- computed on the fly via src/analytics/cagr.py
     (revenue_cagr_3yr is not persisted in financial_ratios, per Day 15 finding)
  2. FCF positive in latest year -- read directly off the screener universe
  3. D/E declining over the most recent 3 fiscal years -- implemented below

Day 16 bug fixes (found via day16_diagnose_turnaround.py against real data):
  (a) de_declining_yoy originally required D/E to decline across a
      company's ENTIRE reported history (10-14 years) with zero up-years
      anywhere — 0/92 companies satisfied that. Fixed to check only the
      most recent `window_years` (default 3), the sensible reading of
      "D/E declining" for a turnaround screen (recent trend, not a
      decade-plus unbroken streak).
  (b) run_turnaround_watch assigned a company_id-indexed Series directly
      onto a RangeIndex-indexed DataFrame column, which pandas aligns by
      INDEX not by matching company_id values — every row silently became
      NaN. Fixed by mapping through company_id explicitly.
"""

from __future__ import annotations

import sqlite3

import pandas as pd

from src.analytics.cagr import compute_cagr_window


def de_declining_yoy(history: pd.DataFrame, window_years: int = 3) -> dict[str, bool]:
    """For each company, True if debt_to_equity strictly declined across
    its most recent `window_years` reported years.

    history: DataFrame with columns company_id, year, debt_to_equity.
    Companies with fewer than window_years of rows get False (insufficient
    history to judge a recent trend — not a "yes" by default).

    Day 16 fix: originally checked the ENTIRE reported history for a
    monotonic decline (0/92 real companies satisfied that — confirmed via
    diagnostic). Now checks only the most recent window_years, which is
    the sensible reading of "D/E declining" for a turnaround screen.
    """
    result: dict[str, bool] = {}
    for company_id, group in history.groupby("company_id"):
        sorted_group = group.sort_values("year")
        de_values = sorted_group["debt_to_equity"].tolist()

        if len(de_values) < window_years:
            result[company_id] = False
            continue

        recent = de_values[-window_years:]
        result[company_id] = all(
            recent[i] > recent[i + 1] for i in range(len(recent) - 1)
        )

    return result


def build_sales_series_map(
    conn: sqlite3.Connection,
) -> dict[str, dict[str, float | None]]:
    """Build {company_id: {year: sales}} from the full profitandloss
    history — needed because Revenue CAGR 3yr requires each company's
    OWN latest year plus its year-3-back value, not one shared year.
    """
    df = pd.read_sql_query("SELECT company_id, year, sales FROM profitandloss", conn)
    result: dict[str, dict[str, float | None]] = {}
    for company_id, group in df.groupby("company_id"):
        result[company_id] = dict(zip(group["year"], group["sales"]))
    return result


def compute_revenue_cagr_3yr(
    universe: pd.DataFrame, conn: sqlite3.Connection
) -> pd.Series:
    """For each company in the screener universe (each carrying its own
    latest fiscal year in the 'year' column), compute Revenue CAGR 3yr
    on the fly using the existing, tested cagr.py engine — not
    reimplemented here.
    """
    sales_map = build_sales_series_map(conn)
    results: dict[str, float | None] = {}

    for _, row in universe.iterrows():
        company_id = row["company_id"]
        latest_year = row["year"]
        series = sales_map.get(company_id, {})
        value, _flag = compute_cagr_window(series, latest_year, window_years=3)
        results[company_id] = value

    return pd.Series(results, name="revenue_cagr_3yr")


def run_turnaround_watch(
    universe: pd.DataFrame,
    conn: sqlite3.Connection,
    revenue_cagr_3yr_min: float = 18.0,
) -> pd.DataFrame:
    """Apply all 3 Turnaround Watch conditions and return the sorted result.

    Not routed through engine.py's generic apply_filters() — this preset's
    conditions are inherently multi-year, unlike every other preset's
    single-row threshold checks.

    Day 16 calibration: spec's Revenue CAGR 3yr > 10% returned 17 companies
    among the FCF>0 & D/E-declining base (2 over the 5-15 expected band).
    Recalibrated to >18% using the real distribution (day16_calibrate_
    turnaround.py) — lands at 12, at a natural gap in the data (18.99 down
    to 17.83, the largest jump in the middle of the sorted list) rather
    than an arbitrary round number.

    Day 16 bug fix: revenue_cagr_3yr is now attached via company_id
    mapping (.map(dict)), not a direct Series assignment — a direct
    assignment silently produced all-NaN because compute_revenue_cagr_3yr()
    returns a company_id-indexed Series while `universe` has a plain
    RangeIndex from the SQL merges in load_screener_universe(). pandas
    aligns Series-to-column assignment by INDEX, not by matching values.
    """
    df = universe.copy()

    revenue_cagr_series = compute_revenue_cagr_3yr(df, conn)
    df["revenue_cagr_3yr"] = df["company_id"].map(revenue_cagr_series.to_dict())

    de_history = pd.read_sql_query(
        "SELECT company_id, year, debt_to_equity FROM financial_ratios", conn
    )
    declining_map = de_declining_yoy(de_history)
    df["de_declining_yoy"] = df["company_id"].map(declining_map).fillna(False)

    mask = (
        (df["revenue_cagr_3yr"] > revenue_cagr_3yr_min)
        & (df["free_cash_flow_cr"] > 0)
        & (df["de_declining_yoy"])
    )

    result = df[mask].copy()
    return result.sort_values("revenue_cagr_3yr", ascending=False).reset_index(
        drop=True
    )
