"""
Financial Ratio Engine — Composite Quality Score (Sprint 2, Day 12)

Implements the Composite Quality Score from spec Section 13:
    composite_quality_score = 0.3*ROE_score + 0.25*FCF_score
                             + 0.25*ROCE_score + 0.20*DE_score
    (0-100 scale; 70-100 = excellent, 40-70 = moderate)

Three judgment calls made here, since the spec gives the formula and
weights but not every implementation detail:

1. WHICH raw metric feeds each sub-score:
     ROE_score  <- return_on_equity_pct
     ROCE_score <- return_on_capital_employed_pct
     FCF_score  <- free_cash_flow_cr
     DE_score   <- debt_to_equity (via the explicit curve below, not
                    winsorisation -- see point 2)
   The spec names the four inputs but doesn't define the exact source
   column for each; these are the most direct, literal matches.

2. DE_score uses the explicit D/E-to-score curve from spec Section 25.1
   (0=100, 0.5=85, 1=70, 2=50, >5=0, piecewise-linear in between) rather
   than P10/P90 winsorisation. That curve is the only D/E-to-score mapping
   anywhere in the spec, and reusing it is more faithful to "0 D/E = best"
   than a purely cross-sectional percentile would be (which would only
   say "best among this year's companies", not "actually debt-free").

3. ROE_score/ROCE_score/FCF_score are computed via P10/P90 winsorisation
   computed PER FISCAL YEAR (i.e. each company is compared only to other
   companies reporting in the same year), not pooled across all 14 years
   of history. Comparing a 2010 ROE to a 2024 ROE on the same scale would
   conflate genuine quality differences with macro/era effects.

If ANY of the four sub-scores is None for a company-year (missing D/E,
missing ROE, etc. -- e.g. SBIN), the composite score is None for that
row rather than silently re-weighting the other three. This matches the
"don't paper over missing data" convention used everywhere else in this
codebase (Day 8/9's ROE, D/E, etc.).
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from analytics.edge_cases import flag_implausible_ratio

# (de_ratio, score) anchor points from spec Section 25.1, piecewise-linear
# between them. D/E ratios at or above the last anchor (5) all score 0.
DE_SCORE_ANCHORS = [(0.0, 100.0), (0.5, 85.0), (1.0, 70.0), (2.0, 50.0), (5.0, 0.0)]


def de_score(de_ratio: Optional[float]) -> Optional[float]:
    """Map a D/E ratio to a 0-100 score via the spec's anchor points,
    piecewise-linear interpolation between them. >=5 -> 0. None if
    de_ratio is missing or negative (a valid D/E is never negative; this
    is a defensive guard, not an expected real case)."""
    if de_ratio is None or de_ratio < 0:
        return None
    if de_ratio >= DE_SCORE_ANCHORS[-1][0]:
        return 0.0
    for (x0, y0), (x1, y1) in zip(DE_SCORE_ANCHORS, DE_SCORE_ANCHORS[1:]):
        if x0 <= de_ratio <= x1:
            fraction = (de_ratio - x0) / (x1 - x0)
            return y0 + fraction * (y1 - y0)
    return None  # unreachable given the >= check above


def winsorized_percentiles(
    values: list[float], lower: float = 10, upper: float = 90
) -> tuple[float, float]:
    """P10/P90 of a list of values. Caller is responsible for filtering
    out None/missing values first."""
    arr = np.array(values, dtype=float)
    return float(np.percentile(arr, lower)), float(np.percentile(arr, upper))


def normalize_winsorized(
    value: Optional[float], p10: float, p90: float
) -> Optional[float]:
    """Clip value to [p10, p90], then min-max scale to 0-100. If p10==p90
    (e.g. only one company in the year-group, or every value tied), every
    value maps to 50 -- there's no meaningful spread to rank against."""
    if value is None:
        return None
    clipped = min(max(value, p10), p90)
    if p90 == p10:
        return 50.0
    return (clipped - p10) / (p90 - p10) * 100


def composite_quality_score(
    roe_score: Optional[float],
    fcf_score: Optional[float],
    roce_score: Optional[float],
    de_score_value: Optional[float],
) -> Optional[float]:
    """0.3*ROE_score + 0.25*FCF_score + 0.25*ROCE_score + 0.20*DE_score.
    None if any sub-score is missing (see module docstring)."""
    if None in (roe_score, fcf_score, roce_score, de_score_value):
        return None
    return (
        0.3 * roe_score + 0.25 * fcf_score + 0.25 * roce_score + 0.20 * de_score_value
    )


def composite_quality_label(score: Optional[float]) -> Optional[str]:
    """70-100 = Excellent, 40-70 = Moderate, <40 = Weak. The spec (Section
    13) only names the top two bands; "Weak" for <40 is the natural
    complement, added here for completeness."""
    if score is None:
        return None
    if score >= 70:
        return "Excellent"
    if score >= 40:
        return "Moderate"
    return "Weak"


def compute_quality_scores_for_year(rows: list[dict]) -> list[dict]:
    """Given all company rows for ONE fiscal year (each a dict with at
    least company_id, return_on_equity_pct, return_on_capital_employed_pct,
    free_cash_flow_cr, debt_to_equity), compute that year's P10/P90 for
    ROE/ROCE/FCF and return a list of
    {company_id, composite_quality_score, composite_quality_label} dicts,
    one per input row (same order, by company_id).

    Day 13 fix: any row whose ROE or ROCE is flagged implausible by
    edge_cases.flag_implausible_ratio() (e.g. HAL's ~147x equity
    discrepancy producing a 3800%+ ROE) is excluded from BOTH the P10/P90
    percentile pool AND given a None composite score. Without this, two
    things go wrong: (1) the company's own score gets built from garbage
    input, producing a misleadingly high or low "Excellent"/"Weak" label
    for a company whose underlying data is known to be broken; (2) the
    implausible value distorts that year's P90, silently compressing the
    scores of every OTHER company reporting that same year. This mirrors
    the existing convention used everywhere else in this codebase
    (SBIN gets None, not a fabricated number) rather than introducing a
    new behavior."""
    plausible_rows = [
        r
        for r in rows
        if not flag_implausible_ratio(
            "return_on_equity_pct", r.get("return_on_equity_pct")
        )
        and not flag_implausible_ratio(
            "return_on_capital_employed_pct", r.get("return_on_capital_employed_pct")
        )
    ]

    roe_values = [
        r["return_on_equity_pct"]
        for r in plausible_rows
        if r.get("return_on_equity_pct") is not None
    ]
    roce_values = [
        r["return_on_capital_employed_pct"]
        for r in plausible_rows
        if r.get("return_on_capital_employed_pct") is not None
    ]
    fcf_values = [
        r["free_cash_flow_cr"]
        for r in plausible_rows
        if r.get("free_cash_flow_cr") is not None
    ]

    roe_p10, roe_p90 = (
        winsorized_percentiles(roe_values) if roe_values else (None, None)
    )
    roce_p10, roce_p90 = (
        winsorized_percentiles(roce_values) if roce_values else (None, None)
    )
    fcf_p10, fcf_p90 = (
        winsorized_percentiles(fcf_values) if fcf_values else (None, None)
    )

    results = []
    for r in rows:
        is_implausible = flag_implausible_ratio(
            "return_on_equity_pct", r.get("return_on_equity_pct")
        ) or flag_implausible_ratio(
            "return_on_capital_employed_pct", r.get("return_on_capital_employed_pct")
        )

        if is_implausible:
            results.append(
                {
                    "company_id": r.get("company_id"),
                    "composite_quality_score": None,
                    "composite_quality_label": None,
                }
            )
            continue

        roe_s = (
            normalize_winsorized(r.get("return_on_equity_pct"), roe_p10, roe_p90)
            if roe_values
            else None
        )
        roce_s = (
            normalize_winsorized(
                r.get("return_on_capital_employed_pct"), roce_p10, roce_p90
            )
            if roce_values
            else None
        )
        fcf_s = (
            normalize_winsorized(r.get("free_cash_flow_cr"), fcf_p10, fcf_p90)
            if fcf_values
            else None
        )
        de_s = de_score(r.get("debt_to_equity"))

        score = composite_quality_score(roe_s, fcf_s, roce_s, de_s)
        results.append(
            {
                "company_id": r.get("company_id"),
                "composite_quality_score": score,
                "composite_quality_label": composite_quality_label(score),
            }
        )
    return results
