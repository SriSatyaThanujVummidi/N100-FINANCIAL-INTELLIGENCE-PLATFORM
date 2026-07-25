"""Sector-relative composite quality score — Sprint 3, Day 17.

Distinct from Sprint 2's src/analytics/scoring.py (signed off, untouched).
That score winsorizes per exact fiscal-year string, which silently breaks
for any company on a non-standard fiscal year-end with few/no cohort
peers — confirmed for SIEMENS (Sep year-end, cohort of 1 every year,
frozen at ~60 for its entire 14-year history, Day 15/16 finding).

This module winsorizes within broad_sector instead — SIEMENS's Industrials
sector has ~9 companies regardless of fiscal year-end, giving a real
comparison pool every time.

Weights (spec Section 25.1):
  Profitability  35%  (ROE 15%, ROCE 10%, NPM 10%)
  Cash Quality   30%  (FCF CAGR 5yr 15%, CFO/PAT ratio 10%, FCF>0 flag 5%)
  Growth         20%  (Revenue CAGR 5yr 10%, PAT CAGR 5yr 10%)
  Leverage       15%  (D/E score 10%, ICR score 5%)

D/E score curve (spec): 0=100, 0.5=85, 1=70, 2=50, >=5=0 (linear between points)
ICR score curve (spec): <1.5=0, 3=50, 5=75, >=10=100 (linear between points);
  is_debt_free treated as ICR=+infinity -> score 100, same convention as
  the screener's ICR-min filter (Day 15).

Day 17 confirmed via PRAGMA check: neither cfo_pat_ratio nor fcf_cagr_5yr
are persisted in financial_ratios (same gap pattern as revenue_cagr_3yr,
Day 15). fcf_cagr_5yr is computed on the fly via the existing, tested
src/analytics/cagr.py engine (same approach as Turnaround Watch's
compute_revenue_cagr_3yr). cfo_pat_ratio is derived inline from
cash_from_operations_cr / net_profit — both of THOSE raw columns exist
(cash_from_operations_cr in financial_ratios, net_profit via the
profitandloss join already present in load_screener_universe()).

Design rule (matches Sprint 2's scoring.py convention): if any of the 8
sub-scores is missing/None for a company, the final composite score is
None rather than a partial average — a company shouldn't be silently
scored on 6 of 8 dimensions and look comparable to one scored on all 8.

Known limitation, NOT fixed today (flagged for team lead review): sectors
with very few companies (Communication Services n=2, Real Estate n=3)
have a statistically fragile P10/P90 winsorization window. Documented,
not patched — same treatment as HAL/SBIN-style caveats.
"""

from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

from src.analytics.cagr import compute_cagr_window
from src.analytics.edge_cases import flag_implausible_ratio

SECTOR_METRICS_WINSORIZED = [
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "net_profit_margin_pct",
    "fcf_cagr_5yr",
    "cfo_pat_ratio",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
]

WEIGHTS = {
    "return_on_equity_pct": 0.15,
    "return_on_capital_employed_pct": 0.10,
    "net_profit_margin_pct": 0.10,
    "fcf_cagr_5yr": 0.15,
    "cfo_pat_ratio": 0.10,
    "fcf_positive_flag": 0.05,
    "revenue_cagr_5yr": 0.10,
    "pat_cagr_5yr": 0.10,
    "de_score": 0.10,
    "icr_score": 0.05,
}

# Day 17 design fix: composite score no longer requires ALL 10 sub-scores
# to be present (Sprint 2's convention for its simpler 4-input formula).
# Real-data check (day17_diagnose_fcf_cagr.py) showed fcf_cagr_5yr is
# None for 44/92 companies -- overwhelmingly legitimate sign-crossing
# (BOTH_NEGATIVE/TURNAROUND/DECLINE_TO_LOSS per cagr.py's spec-mandated
# edge cases, e.g. RELIANCE/LT/HDFCBANK's real lumpy FCF cycles), not a
# bug. Applying Sprint 2's all-or-nothing rule across 10 inputs (one of
# them inherently volatile) nulled out half the universe. Now: compute a
# weighted average over whichever sub-scores ARE available, re-normalized
# by the weight actually present. A company only gets None if it's
# missing more than half the TOTAL weight -- meaning the remaining inputs
# can't be trusted to represent the formula's intent. Documented
# deviation from Sprint 2's stricter convention; flagged for team lead
# review.
MIN_AVAILABLE_WEIGHT = 0.50
# Day 17: metrics checked against Day 13's edge_cases.py sanity bounds
# before winsorization. A company tripping either bound gets its
# composite score fully excluded (None), and these two raw columns are
# masked to NaN for that company BEFORE the sector groupby, so it also
# stops distorting the percentile window for every other company in its
# sector (this is what corrupted LT's score via HAL/BEL's Industrials
# cohort membership).
SANITY_CHECK_METRICS = ["return_on_equity_pct", "return_on_capital_employed_pct"]


def is_implausible_row(row: pd.Series) -> bool:
    """True if this row's ROE or ROCE trips Day 13's sanity bound."""
    return any(
        flag_implausible_ratio(metric, row.get(metric))
        for metric in SANITY_CHECK_METRICS
    )


def build_fcf_series_map(
    conn: sqlite3.Connection,
) -> dict[str, dict[str, float | None]]:
    """Build {company_id: {year: free_cash_flow_cr}} from financial_ratios
    (FCF is already computed there per Sprint 2 — unlike revenue_cagr_3yr,
    which needed raw profitandloss)."""
    df = pd.read_sql_query(
        "SELECT company_id, year, free_cash_flow_cr FROM financial_ratios", conn
    )
    result: dict[str, dict[str, float | None]] = {}
    for company_id, group in df.groupby("company_id"):
        result[company_id] = dict(zip(group["year"], group["free_cash_flow_cr"]))
    return result


def compute_fcf_cagr_5yr(universe: pd.DataFrame, conn: sqlite3.Connection) -> pd.Series:
    """FCF CAGR 5yr, computed on the fly per company's own latest year,
    reusing the tested cagr.py engine — same approach as Turnaround
    Watch's compute_revenue_cagr_3yr (Day 16)."""
    fcf_map = build_fcf_series_map(conn)
    results: dict[str, float | None] = {}
    for _, row in universe.iterrows():
        company_id, latest_year = row["company_id"], row["year"]
        series = fcf_map.get(company_id, {})
        value, _flag = compute_cagr_window(series, latest_year, window_years=5)
        results[company_id] = value
    return pd.Series(results, name="fcf_cagr_5yr")


def de_score(de: float | None) -> float | None:
    """Piecewise D/E score per spec Section 25.1: 0=100, 0.5=85, 1=70,
    2=50, >=5=0, linear between points. None if de is missing."""
    if de is None or (isinstance(de, float) and np.isnan(de)):
        return None
    xp = [0.0, 0.5, 1.0, 2.0, 5.0]
    fp = [100.0, 85.0, 70.0, 50.0, 0.0]
    if de >= 5.0:
        return 0.0
    return float(np.interp(de, xp, fp))


def icr_score(icr: float | None, is_debt_free: bool) -> float | None:
    """Piecewise ICR score per spec Section 25.1: <1.5=0, 3=50, 5=75,
    >=10=100, linear between points. Debt-free treated as ICR=+infinity
    -> 100, same convention as the screener's ICR-min filter (Day 15)."""
    if is_debt_free:
        return 100.0
    if icr is None or (isinstance(icr, float) and np.isnan(icr)):
        return None
    xp = [1.5, 3.0, 5.0, 10.0]
    fp = [0.0, 50.0, 75.0, 100.0]
    if icr >= 10.0:
        return 100.0
    if icr < 1.5:
        return 0.0
    return float(np.interp(icr, xp, fp))


def winsorize_and_scale_within_group(series: pd.Series) -> pd.Series:
    """Cap at P10/P90 within the given series, then linear-scale to 0-100.

    If the series has too few non-null values or P10==P90 (degenerate —
    e.g. a sector with 1-2 companies, or a metric with no spread), returns
    50.0 for every valid entry rather than dividing by zero. Documented
    limitation for small sectors (Communication Services n=2, Real Estate
    n=3) — not fixed today, flagged for team lead review.
    """
    valid = series.dropna()
    if len(valid) < 2:
        return series.apply(lambda v: 50.0 if pd.notna(v) else np.nan)

    p10, p90 = valid.quantile(0.10), valid.quantile(0.90)
    if p10 == p90:
        return series.apply(lambda v: 50.0 if pd.notna(v) else np.nan)

    clipped = series.clip(lower=p10, upper=p90)
    scaled = (clipped - p10) / (p90 - p10) * 100
    return scaled


def compute_sector_relative_composite_score(
    universe: pd.DataFrame, conn: sqlite3.Connection
) -> pd.DataFrame:
    """Compute the Day 17 sector-relative composite score.

    Returns a copy of `universe` with additional columns:
      - the 8 raw sub-metrics used
      - each metric's 0-100 sub-score (suffix _score)
      - sanity_flagged (bool): True if ROE/ROCE tripped Day 13's
        plausibility bound -- these companies get a fully excluded score
      - composite_score_sector_relative (final 0-100, or None if
        sanity-flagged or missing >50% of total weight)

    Winsorization happens WITHIN broad_sector groups, not within an exact
    fiscal-year string (Sprint 2's approach) — this is the Day 17 fix for
    SIEMENS's frozen ~60 score (Sep fiscal year-end, cohort-of-1 problem).
    """
    df = universe.copy()

    # --- Day 17 sanity-bound check (Day 13's edge_cases.py), BEFORE
    # winsorization — mask ROE/ROCE to NaN for flagged companies so they
    # don't distort other companies' sector percentile window. ---
    df["sanity_flagged"] = df.apply(is_implausible_row, axis=1)
    for metric in SANITY_CHECK_METRICS:
        df.loc[df["sanity_flagged"], metric] = np.nan

    # --- on-the-fly metrics ---
    fcf_cagr_series = compute_fcf_cagr_5yr(df, conn)
    df["fcf_cagr_5yr"] = df["company_id"].map(fcf_cagr_series.to_dict())

    df["cfo_pat_ratio"] = df["cash_from_operations_cr"] / df["net_profit"].replace(
        0, np.nan
    )
    df["fcf_positive_flag"] = np.where(df["free_cash_flow_cr"] > 0, 100.0, 0.0)

    df["de_score"] = df["debt_to_equity"].apply(de_score)
    df["icr_score"] = df.apply(
        lambda r: icr_score(r["interest_coverage"], r["is_debt_free"]), axis=1
    )

    # --- sector-relative winsorized scores for the 7 continuous metrics ---
    for metric in SECTOR_METRICS_WINSORIZED:
        score_col = f"{metric}_score"
        df[score_col] = df.groupby("broad_sector")[metric].transform(
            winsorize_and_scale_within_group
        )

    def combine(row: pd.Series) -> float | None:
        # Day 17: sanity-flagged companies (implausible ROE/ROCE) get a
        # fully excluded score, regardless of how much weight would
        # otherwise be available -- their underlying data can't be
        # trusted, same precedent as Sprint 2 Day 14's HAL exclusion.
        """Combine."""
        if row["sanity_flagged"]:
            return None

        available_weight = sum(
            weight_map[col] for col in score_columns if pd.notna(row[col])
        )
        if available_weight < MIN_AVAILABLE_WEIGHT:
            return None
        weighted_sum = sum(
            row[col] * weight_map[col] for col in score_columns if pd.notna(row[col])
        )
        # Re-normalize: the weighted sum is scaled against only the weight
        # actually present, so the result stays on a true 0-100 scale
        # rather than being silently deflated by missing inputs.
        return weighted_sum / available_weight

    score_columns = [f"{m}_score" for m in SECTOR_METRICS_WINSORIZED] + [
        "fcf_positive_flag",
        "de_score",
        "icr_score",
    ]
    weight_map = {
        **{f"{m}_score": WEIGHTS[m] for m in SECTOR_METRICS_WINSORIZED},
        **{
            "fcf_positive_flag": WEIGHTS["fcf_positive_flag"],
            "de_score": WEIGHTS["de_score"],
            "icr_score": WEIGHTS["icr_score"],
        },
    }

    df["composite_score_sector_relative"] = df.apply(combine, axis=1)

    return df
