"""
Financial Ratio Engine — Day 13: Bank ROCE Carve-Out & Edge Case Log

Three things happen today:

1. Bank/NBFC D/E warning suppression -- already implemented on Day 9
   (high_leverage_flag() checks is_financials_sector() before flagging).
   Nothing new to write here; this module just re-exports a confirmation
   helper so it shows up in the same place as everything else Day 13
   touches.

2. Cross-check computed ROCE/ROE against companies.xlsx's pre-computed
   roce_percentage/roe_percentage columns. Differences > 5% get written
   to ratio_edge_cases.log with a category guess (data source issue /
   version difference / formula discrepancy).

3. HAL anomaly resolution (deferred from Day 8/9 -- see PROGRESS.md).
   DECISION: Option B -- a generic sanity-bound check across all 92
   companies, not a HAL-specific exclusion.

   Reasoning: HAL's ~147x equity discrepancy was only caught by manual
   inspection on Day 8 (day9_preview.py's Asset Turnover output is what
   surfaced it a second time, independently, on Day 9). A HAL-specific
   `if company_id == "HAL"` exclusion would only catch the ONE company
   that happened to get manually reviewed -- it does nothing for any
   other company in the universe with a similar undetected balance-sheet
   data-entry error. A bound that applies uniformly to all 92 companies'
   computed ratios is more defensible, doesn't require updating code
   every time a new anomaly is found by chance, and matches the existing
   codebase pattern of preferring generic checks over company-specific
   carve-outs (e.g. Sprint 1's _filter_to_schema_columns() introspecting
   PRAGMA table_info() generically rather than hardcoding column lists
   per file).

   The bounds chosen below are deliberately generous -- wide enough that
   no genuinely high-performing real company should ever trip them, but
   tight enough to catch a >100x unit/data-entry error like HAL's. They
   are NOT the same as the sector benchmark bands in roce_benchmark_band()
   (spec Section 28) -- those describe what's *typical*; these describe
   what's *physically plausible*. A company can legitimately be well
   outside the typical band (e.g. an exceptional ROE year) without ever
   approaching these bounds.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Plausibility bounds for ratios that become nonsensical when a balance
# sheet figure is off by a unit-conversion-style factor (Lakh vs Crore,
# a misplaced decimal, etc.). Chosen well outside any real Nifty 100
# company's historical range (see spec Section 28's sector tables, which
# top out around 50% ROE for FMCG/IT in good years).
SANITY_BOUNDS = {
    "return_on_equity_pct": (-500.0, 500.0),
    "return_on_capital_employed_pct": (-500.0, 500.0),
    "return_on_assets_pct": (-200.0, 200.0),
    "asset_turnover": (0.0, 20.0),
}

CROSS_CHECK_TOLERANCE_PCT = 5.0


def flag_implausible_ratio(metric_name: str, value: Optional[float]) -> bool:
    """True if `value` falls outside the plausibility bound for
    `metric_name`. Returns False (not flagged) if the metric has no
    defined bound, or if value is None."""
    if value is None:
        return False
    bounds = SANITY_BOUNDS.get(metric_name)
    if bounds is None:
        return False
    low, high = bounds
    return value < low or value > high


def categorize_anomaly(
    diff_pct: float, computed_value: Optional[float], source_value: Optional[float]
) -> str:
    """Best-effort categorization of a ROE/ROCE cross-check anomaly, per
    spec Day 13's three buckets. This is a heuristic, not a certainty --
    every anomaly should still be read by a human (see
    review_edge_cases.py) before being filed away.

      - "data source issue": one side is None/clearly broken, or the
        computed value itself is outside SANITY_BOUNDS (e.g. HAL-style).
      - "version difference": both values are in a plausible range and
        reasonably close in sign/order of magnitude, just outside the 5%
        tolerance -- consistent with the source field being computed at
        a different point in time, or off a slightly different formula
        version, than this engine's live computation.
      - "formula discrepancy": both values are plausible but far apart
        (sign flip, or one is a small multiple of the other) -- suggests
        the two sides are computing genuinely different things, not just
        drifting due to staleness.
    """
    if computed_value is None or source_value is None:
        return "data source issue"

    if flag_implausible_ratio(
        "return_on_equity_pct", computed_value
    ) or flag_implausible_ratio("return_on_capital_employed_pct", computed_value):
        return "data source issue"

    # A source value that's implausibly tiny relative to the computed one
    # (e.g. companies.xlsx's documented TCS case: roe_percentage=0.52
    # against a computed ROE of ~50%) is a strong signal the source field
    # itself has a decimal-place or percentage-formatting error, not that
    # the two sides are measuring genuinely different things.
    if abs(source_value) > 0 and abs(computed_value) / abs(source_value) >= 10:
        return "data source issue"

    # Sign flip (one positive, one negative) is a strong signal of a
    # genuine formula/definition mismatch, not gradual drift.
    if (computed_value >= 0) != (source_value >= 0):
        return "formula discrepancy"

    if diff_pct <= 20:
        return "version difference"

    return "formula discrepancy"


def roce_cross_check(
    company_id: str,
    year: str,
    computed_roce_pct: Optional[float],
    source_roce_pct: Optional[float],
) -> Optional[dict]:
    """Compare computed ROCE (Day 8's return_on_capital_employed_pct) vs
    companies.xlsx's pre-computed roce_percentage. Returns an edge-case
    record dict if the absolute difference exceeds
    CROSS_CHECK_TOLERANCE_PCT, else None (no anomaly to log).

    Note: companies.xlsx's roce_percentage is a CURRENT-SNAPSHOT value
    (spec Section 5.1), not a per-year time series, so this should only
    be called for each company's LATEST year -- comparing it against
    every historical year would manufacture false anomalies for any
    company whose ROCE has simply changed over time."""
    if computed_roce_pct is None or source_roce_pct is None:
        diff = None
    else:
        diff = abs(computed_roce_pct - source_roce_pct)

    if diff is None or diff > CROSS_CHECK_TOLERANCE_PCT:
        diff_for_category = diff if diff is not None else float("inf")
        category = categorize_anomaly(
            diff_for_category, computed_roce_pct, source_roce_pct
        )
        record = {
            "company_id": company_id,
            "year": year,
            "metric": "ROCE",
            "computed_value": computed_roce_pct,
            "source_value": source_roce_pct,
            "diff_pct": diff,
            "category": category,
        }
        logger.warning(
            "ROCE cross-check anomaly company_id=%s year=%s computed=%s source=%s diff=%s category=%s",
            company_id,
            year,
            computed_roce_pct,
            source_roce_pct,
            diff,
            category,
        )
        return record
    return None


def roe_cross_check(
    company_id: str,
    year: str,
    computed_roe_pct: Optional[float],
    source_roe_pct: Optional[float],
) -> Optional[dict]:
    """Same as roce_cross_check(), for ROE vs companies.xlsx's
    roe_percentage. Per spec Section 5.1, this source field is known to
    be unreliable for some companies (e.g. TCS shows 0.52, an obvious
    decimal/percentage-formatting error) -- the engine's computed value
    is always what's used for analytics; the source field is display-
    only. This cross-check exists purely to document/log the divergence,
    same convention as Day 8's OPM cross-check."""
    if computed_roe_pct is None or source_roe_pct is None:
        diff = None
    else:
        diff = abs(computed_roe_pct - source_roe_pct)

    if diff is None or diff > CROSS_CHECK_TOLERANCE_PCT:
        diff_for_category = diff if diff is not None else float("inf")
        category = categorize_anomaly(
            diff_for_category, computed_roe_pct, source_roe_pct
        )
        record = {
            "company_id": company_id,
            "year": year,
            "metric": "ROE",
            "computed_value": computed_roe_pct,
            "source_value": source_roe_pct,
            "diff_pct": diff,
            "category": category,
        }
        logger.warning(
            "ROE cross-check anomaly company_id=%s year=%s computed=%s source=%s diff=%s category=%s",
            company_id,
            year,
            computed_roe_pct,
            source_roe_pct,
            diff,
            category,
        )
        return record
    return None
