"""
Financial Ratio Engine — Cash Flow KPIs & Capital Allocation (Sprint 2, Day 11)

Implements: Free Cash Flow, CFO Quality Score (5yr-averaged CFO/PAT), CapEx
Intensity, FCF Conversion Rate, and the 8-pattern capital allocation
classifier based on the sign of (CFO, CFI, CFF).

Two documented judgment calls made in this module (neither is a literal
requirement from the spec text):

1. Zero-sign convention: a cash flow value of exactly 0 is treated as the
   "+" bucket (e.g. financing_activity=0 for a company with no debt/dividend
   activity this year). The spec's pattern table only defines strict +/-
   combinations, so a convention had to be picked for the zero case.

2. The (-, +, -) sign combination -- CFO<0, CFI>0, CFF<0 -- isn't named in
   the spec's pattern list (only 7 of the 8 possible sign combinations are
   explicitly labelled there). It's been added here as "Distressed
   Deleveraging" (operating losses, funded by selling off assets/
   investments, while still paying down debt/financing -- a more severe
   cousin of "Distress Signal", which raises additional financing instead
   of paying it down) so that every company-year gets *some* label rather
   than silently falling through. Flag this label specifically if you want
   to confirm the name with your team lead.
"""

from __future__ import annotations

from typing import Optional

from analytics.cagr import shift_fiscal_year

# ============================================================
# Free Cash Flow
# ============================================================


def free_cash_flow(
    operating_activity: Optional[float],
    investing_activity: Optional[float],
) -> Optional[float]:
    """FCF = operating_activity + investing_activity. Negative FCF is
    allowed and meaningful (a company investing more than it generates).
    None if either input is missing."""
    if operating_activity is None or investing_activity is None:
        return None
    return operating_activity + investing_activity


# ============================================================
# CFO Quality Score (5yr-averaged CFO/PAT)
# ============================================================


def cfo_pat_ratio(cfo: Optional[float], net_profit: Optional[float]) -> Optional[float]:
    """CFO/PAT for a single year. None if either input is missing, or
    net_profit == 0 (ratio undefined, not a divide-by-zero we can paper
    over with a default)."""
    if cfo is None or net_profit is None:
        return None
    if net_profit == 0:
        return None
    return cfo / net_profit


def cfo_quality_label(avg_ratio: Optional[float]) -> Optional[str]:
    """>1.0 = High Quality Earnings, 0.5-1.0 = Moderate, <0.5 = Accrual Risk."""
    if avg_ratio is None:
        return None
    if avg_ratio > 1.0:
        return "High Quality Earnings"
    if avg_ratio >= 0.5:
        return "Moderate"
    return "Accrual Risk"


def cfo_quality_score(
    cfo_pat_ratios: list[Optional[float]],
) -> tuple[Optional[float], Optional[str]]:
    """Average a list of per-year CFO/PAT ratios. Years that were None
    (missing data or PAT=0) are skipped entirely, not treated as zero --
    a single bad year shouldn't silently drag down or invalidate the
    whole average. None/None if there are no valid years to average."""
    valid = [r for r in cfo_pat_ratios if r is not None]
    if not valid:
        return None, None
    avg = sum(valid) / len(valid)
    return avg, cfo_quality_label(avg)


def compute_cfo_quality_score_window(
    cfo_series: dict[str, Optional[float]],
    pat_series: dict[str, Optional[float]],
    latest_year: str,
    window_years: int = 5,
) -> tuple[Optional[float], Optional[str]]:
    """Average CFO/PAT over the trailing `window_years` fiscal years
    (latest_year and the window_years-1 years before it). Reuses
    shift_fiscal_year() from the Day 10 CAGR engine for the year
    arithmetic so the fiscal-year-end convention stays consistent across
    modules. Missing years/values are skipped (see cfo_quality_score)."""
    ratios = []
    for offset in range(window_years):
        year = shift_fiscal_year(latest_year, offset)
        ratios.append(cfo_pat_ratio(cfo_series.get(year), pat_series.get(year)))
    return cfo_quality_score(ratios)


# ============================================================
# CapEx Intensity
# ============================================================


def capex_intensity(
    investing_activity: Optional[float],
    sales: Optional[float],
) -> tuple[Optional[float], Optional[str]]:
    """abs(investing_activity)/sales*100. <3% = Asset Light,
    3-8% = Moderate, >8% = Capital Intensive. None/None if sales is
    missing/0 or investing_activity is missing."""
    if investing_activity is None or sales is None or sales == 0:
        return None, None
    intensity = abs(investing_activity) / sales * 100
    if intensity < 3:
        label = "Asset Light"
    elif intensity <= 8:
        label = "Moderate"
    else:
        label = "Capital Intensive"
    return intensity, label


# ============================================================
# FCF Conversion Rate
# ============================================================


def fcf_conversion_rate(
    fcf: Optional[float], operating_profit: Optional[float]
) -> Optional[float]:
    """FCF/operating_profit*100. None if either input is missing or
    operating_profit == 0."""
    if fcf is None or operating_profit is None or operating_profit == 0:
        return None
    return (fcf / operating_profit) * 100


def fcf_conversion_label(rate: Optional[float]) -> Optional[str]:
    """>60% = Efficient, 30-60% = Moderate, <30% = CapEx Heavy (spec
    Section 13 benchmark bands). This label column isn't explicitly
    requested by the Day 11 task list, but is added for consistency with
    capex_intensity()/cfo_quality_label() above, which both get one."""
    if rate is None:
        return None
    if rate > 60:
        return "Efficient"
    if rate >= 30:
        return "Moderate"
    return "CapEx Heavy"


# ============================================================
# Capital Allocation 8-Pattern Classifier
# ============================================================


def _sign(value: Optional[float]) -> Optional[str]:
    """'+' for value >= 0, '-' for value < 0. None if value is missing.
    Zero is grouped with '+' -- see module docstring, judgment call #1."""
    if value is None:
        return None
    return "+" if value >= 0 else "-"


PATTERN_LABELS: dict[tuple[str, str, str], str] = {
    ("+", "+", "+"): "Cash Accumulator",
    ("+", "+", "-"): "Liquidating Assets",
    ("+", "-", "+"): "Mixed",
    ("+", "-", "-"): "Reinvestor",  # sub-classified to "Shareholder Returns" below
    ("-", "+", "+"): "Distress Signal",
    ("-", "+", "-"): "Distressed Deleveraging",  # not named in spec -- judgment call #2
    ("-", "-", "+"): "Growth Funded by Debt",
    ("-", "-", "-"): "Pre-Revenue",
}


def capital_allocation_pattern(
    cfo: Optional[float],
    cfi: Optional[float],
    cff: Optional[float],
    cfo_pat_ratio_value: Optional[float] = None,
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Classify one company-year into one of the 8 capital allocation
    patterns from the sign of (CFO, CFI, CFF).

    Returns (cfo_sign, cfi_sign, cff_sign, pattern_label) -- matches the
    column order required for output/capital_allocation.csv.

    `cfo_pat_ratio_value` should be this company-year's single-year
    CFO/PAT ratio (from cfo_pat_ratio(), NOT the 5yr-averaged quality
    score). It's only used to sub-classify the (+,-,-) pattern: if it's
    > 1.0, the label becomes "Shareholder Returns" instead of
    "Reinvestor" (spec Section 13 -- same sign pattern, sub-classified by
    CFO/PAT). Pass None (the default) if you don't have it -- the
    pattern still gets the general "Reinvestor" label.
    """
    cfo_sign = _sign(cfo)
    cfi_sign = _sign(cfi)
    cff_sign = _sign(cff)

    if cfo_sign is None or cfi_sign is None or cff_sign is None:
        return cfo_sign, cfi_sign, cff_sign, None

    label = PATTERN_LABELS[(cfo_sign, cfi_sign, cff_sign)]

    if (cfo_sign, cfi_sign, cff_sign) == ("+", "-", "-"):
        if cfo_pat_ratio_value is not None and cfo_pat_ratio_value > 1.0:
            label = "Shareholder Returns"

    return cfo_sign, cfi_sign, cff_sign, label


# ============================================================
# Single-year orchestrator
# ============================================================


def compute_cashflow_kpis_single_year(row: dict) -> dict:
    """Compute all Day-11 single-year cash flow KPIs for one company-year
    row. Does NOT include the 5yr CFO Quality Score, which needs a
    multi-year window -- see compute_cfo_quality_score_window().

    Expected keys in `row`:
      company_id, year, operating_activity, investing_activity,
      financing_activity, sales, operating_profit, net_profit
    """
    company_id = row.get("company_id")
    year = row.get("year")
    cfo = row.get("operating_activity")
    cfi = row.get("investing_activity")
    cff = row.get("financing_activity")
    sales = row.get("sales")
    op_profit = row.get("operating_profit")
    net_profit = row.get("net_profit")

    fcf = free_cash_flow(cfo, cfi)
    capex_pct, capex_label = capex_intensity(cfi, sales)
    fcf_conv = fcf_conversion_rate(fcf, op_profit)
    fcf_conv_label = fcf_conversion_label(fcf_conv)
    this_year_ratio = cfo_pat_ratio(cfo, net_profit)
    cfo_sign, cfi_sign, cff_sign, pattern_label = capital_allocation_pattern(
        cfo, cfi, cff, this_year_ratio
    )

    return {
        "company_id": company_id,
        "year": year,
        "free_cash_flow_cr": fcf,
        "capex_intensity_pct": capex_pct,
        "capex_intensity_label": capex_label,
        "fcf_conversion_rate_pct": fcf_conv,
        "fcf_conversion_label": fcf_conv_label,
        "cfo_sign": cfo_sign,
        "cfi_sign": cfi_sign,
        "cff_sign": cff_sign,
        "capital_allocation_pattern": pattern_label,
    }


def capex_cr(investing_activity: Optional[float]) -> Optional[float]:
    """CapEx proxy = abs(investing_activity), in Cr. None if missing.
    Per spec Section 6.4 -- a simple proxy since the raw datasets don't
    separately break out CapEx from other investing-activity line items."""
    if investing_activity is None:
        return None
    return abs(investing_activity)
