"""
src/nlp/pros_cons_generator.py

Day 30 — Sprint 5, Module 9 (NLP & Qualitative Analysis)
Auto-generates pros/cons for all 92 companies using 12 pro rules + 12 con
rules (spec Day 30), with a 0-100 confidence score per rule and a >60%
inclusion filter.

Output: output/pros_cons_generated.csv
    columns: company_id, type (pro/con), rule_id, text, confidence_pct

=== Documented judgment calls (see chat for full rationale) ===

1. PRO11 spec contradiction: rule title says "Revenue CAGR > PAT CAGR"
   but rule text says "Revenue growing slower than profits ... improving
   operating leverage" (the opposite inequality). Implemented per the
   TEXT's meaning: PAT CAGR > Revenue CAGR. Flag for team lead review.

2. CON11 (Net Debt > 3x EBITDA): balancesheet has no explicit cash
   column. Approximated net_debt = borrowings - investments - other_asset
   (other_asset as a cash-like proxy), per the KPI Reference formula.
   This is a LOCAL calculation, independent of Day 9's net_debt() in
   ratios.py (exact signature not available here) — reconcile the two
   once this has run, in case they diverge.

3. Confidence scoring: no formula given in spec beyond "0-100 based on
   signal strength". Implemented as scaled_confidence(): value exactly
   at threshold -> 60 (excluded by the >60 filter); scales linearly to
   100 as the metric moves further past threshold by `scale` units.
   Binary/deterministic rules (debt-free, net loss, payout>100%) use a
   flat confidence since there's no natural gradient.

4. Fallback guarantee: spec requires >60% confidence AND >=1 pro/con per
   company — these conflict for companies with thin data (JIOFIN 2yr
   history, SBIN missing balance sheet, HAL/BEL/INDIGO/ICICIPRULI/
   HDFCLIFE sanity-masked ROE/ROCE). If a company has zero passing
   pros (or cons) after normal evaluation, its single highest-confidence
   candidate is kept anyway and rule_id is suffixed "_FALLBACK". A
   company with literally zero evaluable candidates gets a generic
   data-availability note instead (rule_id="NODATA_FALLBACK").

5. Sanity-bound masking: ROE/ROCE magnitudes beyond +/-500% (Day 13/17/18
   convention: HAL/BEL/INDIGO/ICICIPRULI/HDFCLIFE) are treated as
   unavailable for any rule that reads them, so implausible balance-sheet
   artifacts can't manufacture a false pro or con.
"""

import csv
import logging
import sqlite3
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

SANITY_BOUND_PCT = 500.0
CONFIDENCE_FILTER = 60.0

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

REQUIRED_FR_COLUMNS = [
    "company_id",
    "year",
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "debt_to_equity",
    "interest_coverage",
    "free_cash_flow_cr",
    "dividend_payout_ratio_pct",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "eps_cagr_5yr",
    "total_debt_cr",
    "cash_from_operations_cr",
]


def get_connection() -> sqlite3.Connection:
    """Get connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def assert_schema(conn: sqlite3.Connection) -> None:
    """Fail fast with a clear message if financial_ratios doesn't have the
    columns this module depends on, rather than crashing deep in a rule."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(financial_ratios)")}
    missing = [c for c in REQUIRED_FR_COLUMNS if c not in cols]
    if missing:
        raise RuntimeError(
            f"financial_ratios is missing expected columns: {missing}. "
            f"Actual columns: {sorted(cols)}"
        )


def is_implausible_pct(value: Optional[float]) -> bool:
    """Day 13/17/18 sanity bound: |ROE| or |ROCE| > 500% is a balance-sheet
    artifact (HAL/BEL/INDIGO/ICICIPRULI/HDFCLIFE), not a real signal."""
    return value is not None and abs(value) > SANITY_BOUND_PCT


def scaled_confidence(
    excess: float, scale: float, base: float = 60.0, span: float = 40.0
) -> float:
    """excess=0 (at threshold) -> base (60, excluded by the >60 filter).
    excess>=scale -> base+span (100). Linear in between."""
    if excess <= 0:
        return base
    frac = min(1.0, excess / scale)
    return round(base + span * frac, 1)


# --------------------------------------------------------------------------
# Data gathering — one context dict per company, built once, reused by all
# 24 rules (avoids 24x the queries per company).
# --------------------------------------------------------------------------


def build_company_context(conn: sqlite3.Connection, company_id: str) -> dict:
    """Build company context."""
    fr_rows = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year ASC",
            (company_id,),
        )
    ]
    pl_rows = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM profitandloss WHERE company_id = ? ORDER BY year ASC",
            (company_id,),
        )
    ]
    bs_rows = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM balancesheet WHERE company_id = ? ORDER BY year ASC",
            (company_id,),
        )
    ]
    mkt_row = conn.execute(
        "SELECT * FROM market_cap WHERE company_id = ? ORDER BY year DESC LIMIT 1",
        (company_id,),
    ).fetchone()
    sector_row = conn.execute(
        "SELECT broad_sector FROM sectors WHERE company_id = ?", (company_id,)
    ).fetchone()

    return {
        "company_id": company_id,
        "sector": sector_row["broad_sector"] if sector_row else None,
        "fr": fr_rows,
        "pl": pl_rows,
        "bs": bs_rows,
        "mkt": dict(mkt_row) if mkt_row else None,
    }


def last_n(rows: list[dict], n: int) -> Optional[list[dict]]:
    """Returns the last n rows, or None if fewer than n are available —
    lets every rule cleanly say 'insufficient history' instead of guessing."""
    if len(rows) < n:
        return None
    return rows[-n:]


# --------------------------------------------------------------------------
# PRO RULES — each returns (text, confidence) or None if it doesn't apply.
# --------------------------------------------------------------------------


def pro01_roe_sustained(ctx: dict) -> Optional[tuple[str, float]]:
    """Pro01 roe sustained."""
    window = last_n(ctx["fr"], 3)
    if window is None:
        return None
    vals = [r["return_on_equity_pct"] for r in window]
    if any(v is None or is_implausible_pct(v) for v in vals):
        return None
    if all(v > 20 for v in vals):
        avg = sum(vals) / len(vals)
        conf = scaled_confidence(avg - 20, scale=15)
        return (
            "Consistently high return on equity above 20% demonstrates exceptional capital efficiency",
            conf,
        )
    return None


def pro02_fcf_positive_5yr(ctx: dict) -> Optional[tuple[str, float]]:
    """Pro02 fcf positive 5yr."""
    window = last_n(ctx["fr"], 5)
    if window is None:
        return None
    vals = [r["free_cash_flow_cr"] for r in window]
    if any(v is None for v in vals):
        return None
    if all(v > 0 for v in vals):
        # streak beyond the whole available history, capped at all fr rows
        all_vals = [r["free_cash_flow_cr"] for r in ctx["fr"]]
        streak = 0
        for v in reversed(all_vals):
            if v is not None and v > 0:
                streak += 1
            else:
                break
        conf = min(100.0, 70 + 5 * (streak - 5))
        return (
            "Strong free cash flow generation over 5 years signals healthy business fundamentals",
            conf,
        )
    return None


def pro03_debt_free_latest(ctx: dict) -> Optional[tuple[str, float]]:
    """Pro03 debt free latest."""
    if not ctx["fr"]:
        return None
    latest = ctx["fr"][-1]
    de = latest["debt_to_equity"]
    if de is not None and de == 0:
        return (
            "Debt-free balance sheet provides financial flexibility and eliminates interest burden",
            85.0,
        )
    return None


def pro04_revenue_cagr_5yr(ctx: dict) -> Optional[tuple[str, float]]:
    """Pro04 revenue cagr 5yr."""
    if not ctx["fr"]:
        return None
    val = ctx["fr"][-1]["revenue_cagr_5yr"]
    if val is None or val <= 15:
        return None
    conf = scaled_confidence(val - 15, scale=15)
    return (
        "Revenue growing at above 15% CAGR over 5 years reflects strong business momentum",
        conf,
    )


def pro05_opm_latest(ctx: dict) -> Optional[tuple[str, float]]:
    """Pro05 opm latest."""
    if not ctx["fr"]:
        return None
    val = ctx["fr"][-1]["operating_profit_margin_pct"]
    if val is None or val <= 25:
        return None
    conf = scaled_confidence(val - 25, scale=20)
    return (
        "Operating profit margin above 25% indicates strong pricing power and cost discipline",
        conf,
    )


def pro06_pat_cagr_5yr(ctx: dict) -> Optional[tuple[str, float]]:
    """Pro06 pat cagr 5yr."""
    if not ctx["fr"]:
        return None
    val = ctx["fr"][-1]["pat_cagr_5yr"]
    if val is None or val <= 20:
        return None
    conf = scaled_confidence(val - 20, scale=20)
    return (
        "Net profit compounding at above 20% over 5 years creates significant shareholder value",
        conf,
    )


def pro07_icr_strong_or_debtfree(ctx: dict) -> Optional[tuple[str, float]]:
    """Pro07 icr strong or debtfree."""
    if not ctx["fr"]:
        return None
    latest = ctx["fr"][-1]
    icr = latest["interest_coverage"]
    de = latest["debt_to_equity"]
    if icr is None and de is not None and de == 0:
        return (
            "Very high interest coverage ratio reflects negligible financial stress from debt servicing",
            90.0,
        )
    if icr is not None and icr > 10:
        conf = scaled_confidence(icr - 10, scale=15)
        return (
            "Very high interest coverage ratio reflects negligible financial stress from debt servicing",
            conf,
        )
    return None


def pro08_dividend_yield_with_fcf(ctx: dict) -> Optional[tuple[str, float]]:
    """Pro08 dividend yield with fcf."""
    if not ctx["mkt"] or not ctx["fr"]:
        return None
    div_yield = ctx["mkt"].get("dividend_yield_pct")
    fcf = ctx["fr"][-1]["free_cash_flow_cr"]
    if div_yield is None or fcf is None:
        return None
    if div_yield > 2 and fcf > 0:
        conf = scaled_confidence(div_yield - 2, scale=3)
        return (
            "Consistent dividend yield above 2% backed by positive free cash flow",
            conf,
        )
    return None


def pro09_eps_cagr_5yr(ctx: dict) -> Optional[tuple[str, float]]:
    """Pro09 eps cagr 5yr."""
    if not ctx["fr"]:
        return None
    val = ctx["fr"][-1]["eps_cagr_5yr"]
    if val is None or val <= 15:
        return None
    conf = scaled_confidence(val - 15, scale=15)
    return (
        "Earnings per share growing above 15% CAGR indicates strong earnings quality and compounding",
        conf,
    )


def pro10_roe_improving_3yr(ctx: dict) -> Optional[tuple[str, float]]:
    """Pro10 roe improving 3yr."""
    window = last_n(ctx["fr"], 3)
    if window is None:
        return None
    vals = [r["return_on_equity_pct"] for r in window]
    if any(v is None or is_implausible_pct(v) for v in vals):
        return None
    if vals[0] < vals[1] < vals[2]:
        conf = scaled_confidence(vals[2] - vals[0], scale=10)
        return (
            "Return on equity improving for 3 consecutive years shows strengthening business quality",
            conf,
        )
    return None


def pro11_operating_leverage(ctx: dict) -> Optional[tuple[str, float]]:
    """Implemented per the RULE TEXT (PAT CAGR > Revenue CAGR), which
    contradicts the rule TITLE as written in the spec — see module
    docstring point 1."""
    if not ctx["fr"]:
        return None
    latest = ctx["fr"][-1]
    rev_cagr = latest["revenue_cagr_5yr"]
    pat_cagr = latest["pat_cagr_5yr"]
    if rev_cagr is None or pat_cagr is None:
        return None
    if pat_cagr > rev_cagr:
        conf = scaled_confidence(pat_cagr - rev_cagr, scale=10)
        return (
            "Revenue growing slower than profits shows improving operating leverage and scale benefits",
            conf,
        )
    return None


def pro12_assets_growing_debt_declining(ctx: dict) -> Optional[tuple[str, float]]:
    """Pro12 assets growing debt declining."""
    window = last_n(ctx["bs"], 4)  # latest + 3yr-ago comparison point
    if window is None:
        return None
    start, end = window[0], window[-1]
    assets_start, assets_end = start.get("total_assets"), end.get("total_assets")
    debt_start, debt_end = start.get("borrowings"), end.get("borrowings")
    if None in (assets_start, assets_end, debt_start, debt_end) or assets_start <= 0:
        return None
    if assets_end > assets_start and debt_end < debt_start:
        growth_pct = (assets_end / assets_start - 1) * 100
        conf = scaled_confidence(growth_pct, scale=30)
        return (
            "Growing asset base funded by internal accruals reflects self-sustaining growth",
            conf,
        )
    return None


PRO_RULES = [
    ("PRO01", pro01_roe_sustained),
    ("PRO02", pro02_fcf_positive_5yr),
    ("PRO03", pro03_debt_free_latest),
    ("PRO04", pro04_revenue_cagr_5yr),
    ("PRO05", pro05_opm_latest),
    ("PRO06", pro06_pat_cagr_5yr),
    ("PRO07", pro07_icr_strong_or_debtfree),
    ("PRO08", pro08_dividend_yield_with_fcf),
    ("PRO09", pro09_eps_cagr_5yr),
    ("PRO10", pro10_roe_improving_3yr),
    ("PRO11", pro11_operating_leverage),
    ("PRO12", pro12_assets_growing_debt_declining),
]


# --------------------------------------------------------------------------
# CON RULES
# --------------------------------------------------------------------------


def con01_high_de_nonfinancial(ctx: dict) -> Optional[tuple[str, float]]:
    """Con01 high de nonfinancial."""
    if ctx["sector"] == "Financials" or not ctx["fr"]:
        return None
    de = ctx["fr"][-1]["debt_to_equity"]
    if de is None or de <= 2.0:
        return None
    conf = scaled_confidence(de - 2.0, scale=2.0)
    return (
        f"Debt-to-equity ratio of {de:.2f} is elevated for a non-financial company and warrants monitoring",
        conf,
    )


def con02_fcf_negative_3yr(ctx: dict) -> Optional[tuple[str, float]]:
    """Con02 fcf negative 3yr."""
    window = last_n(ctx["fr"], 3)
    if window is None:
        return None
    vals = [r["free_cash_flow_cr"] for r in window]
    if any(v is None for v in vals):
        return None
    if all(v < 0 for v in vals):
        magnitude = abs(sum(vals) / len(vals))
        conf = scaled_confidence(magnitude, scale=1000)  # crore-scale, gentle curve
        return (
            "Free cash flow negative for 3 consecutive years raises concern about cash generation quality",
            conf,
        )
    return None


def con03_opm_declining_3yr(ctx: dict) -> Optional[tuple[str, float]]:
    """Con03 opm declining 3yr."""
    window = last_n(ctx["fr"], 3)
    if window is None:
        return None
    vals = [r["operating_profit_margin_pct"] for r in window]
    if any(v is None for v in vals):
        return None
    if vals[0] > vals[1] > vals[2]:
        conf = scaled_confidence(vals[0] - vals[2], scale=10)
        return (
            "Operating margins declining for 3 consecutive years suggest pricing or cost pressure",
            conf,
        )
    return None


def con04_net_loss_latest(ctx: dict) -> Optional[tuple[str, float]]:
    """Con04 net loss latest."""
    if not ctx["pl"]:
        return None
    latest = ctx["pl"][-1]
    np_val = latest.get("net_profit")
    if np_val is None or np_val >= 0:
        return None
    return ("Company reported a net loss in the most recent financial year", 90.0)


def con05_revenue_declining_2yr(ctx: dict) -> Optional[tuple[str, float]]:
    """Con05 revenue declining 2yr."""
    window = last_n(ctx["pl"], 3)  # need 3 points to confirm 2 consecutive declines
    if window is None:
        return None
    sales = [r.get("sales") for r in window]
    if any(v is None for v in sales):
        return None
    if sales[0] > sales[1] > sales[2]:
        decline_pct = (1 - sales[2] / sales[0]) * 100
        conf = scaled_confidence(decline_pct, scale=15)
        return (
            "Revenue contraction over 2 consecutive years indicates demand weakness or market share loss",
            conf,
        )
    return None


def con06_icr_weak(ctx: dict) -> Optional[tuple[str, float]]:
    """Con06 icr weak."""
    if not ctx["fr"]:
        return None
    icr = ctx["fr"][-1]["interest_coverage"]
    if icr is None or icr >= 1.5:
        return None
    conf = scaled_confidence(1.5 - icr, scale=1.5)
    return (
        "Interest coverage ratio below 1.5x indicates the company is at risk of not meeting its debt obligations",
        conf,
    )


def con07_payout_over_100(ctx: dict) -> Optional[tuple[str, float]]:
    """Con07 payout over 100."""
    if not ctx["fr"]:
        return None
    payout = ctx["fr"][-1]["dividend_payout_ratio_pct"]
    if payout is None or payout <= 100:
        return None
    return (
        "Dividend payout ratio above 100% means the company is paying dividends from reserves, which is unsustainable",
        85.0,
    )


def con08_de_rising_3yr(ctx: dict) -> Optional[tuple[str, float]]:
    """Con08 de rising 3yr."""
    window = last_n(ctx["fr"], 3)
    if window is None:
        return None
    vals = [r["debt_to_equity"] for r in window]
    if any(v is None for v in vals):
        return None
    if vals[0] < vals[1] < vals[2]:
        conf = scaled_confidence(vals[2] - vals[0], scale=1.0)
        return (
            "Rising debt-to-equity ratio over 3 years suggests increasing financial leverage risk",
            conf,
        )
    return None


def con09_eps_declining_3yr(ctx: dict) -> Optional[tuple[str, float]]:
    """Con09 eps declining 3yr."""
    window = last_n(ctx["pl"], 3)
    if window is None:
        return None
    vals = [r.get("eps") for r in window]
    if any(v is None for v in vals):
        return None
    if vals[0] > vals[1] > vals[2]:
        conf = scaled_confidence(vals[0] - vals[2], scale=20)
        return (
            "Earnings per share declining for 3 consecutive years reflects deteriorating profitability",
            conf,
        )
    return None


def con10_roce_weak(ctx: dict) -> Optional[tuple[str, float]]:
    """Con10 roce weak."""
    if not ctx["fr"]:
        return None
    roce = ctx["fr"][-1]["return_on_capital_employed_pct"]
    if roce is None or is_implausible_pct(roce) or roce >= 10:
        return None
    conf = scaled_confidence(10 - roce, scale=10)
    return (
        "Return on capital employed below 10% suggests the business is not generating sufficient returns on invested capital",
        conf,
    )


def con11_net_debt_ebitda(ctx: dict) -> Optional[tuple[str, float]]:
    """See module docstring point 2 — net_debt approximated locally using
    other_asset as a cash proxy; EBITDA proxy = operating_profit.

    Financials excluded (Day 30 real-data fix, same pattern as CON01):
    the other_asset proxy breaks down for Financials, whose "other assets"
    are core-business investment holdings, not idle cash — SBILIFE/LICI
    showed ratios of -1820x/-174x, confirming the proxy is structurally
    invalid for this sector, not just an outlier reading."""
    if ctx["sector"] == "Financials" or not ctx["bs"] or not ctx["pl"]:
        return None
    bs_latest = ctx["bs"][-1]
    pl_latest = ctx["pl"][-1]
    borrowings = bs_latest.get("borrowings")
    investments = bs_latest.get("investments")
    other_asset = bs_latest.get("other_asset")
    ebitda = pl_latest.get("operating_profit")
    if None in (borrowings, investments, other_asset, ebitda) or ebitda <= 0:
        return None
    net_debt = borrowings - investments - other_asset
    ratio = net_debt / ebitda
    if ratio <= 3:
        return None
    conf = scaled_confidence(ratio - 3, scale=3)
    return (
        "Net debt exceeding 3 times EBITDA is a high leverage ratio and limits financial flexibility",
        conf,
    )


def con12_revenue_cagr_low(ctx: dict) -> Optional[tuple[str, float]]:
    """Con12 revenue cagr low."""
    if not ctx["fr"]:
        return None
    val = ctx["fr"][-1]["revenue_cagr_5yr"]
    if val is None or val >= 5:
        return None
    conf = scaled_confidence(5 - val, scale=10)
    return (
        "Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum",
        conf,
    )


CON_RULES = [
    ("CON01", con01_high_de_nonfinancial),
    ("CON02", con02_fcf_negative_3yr),
    ("CON03", con03_opm_declining_3yr),
    ("CON04", con04_net_loss_latest),
    ("CON05", con05_revenue_declining_2yr),
    ("CON06", con06_icr_weak),
    ("CON07", con07_payout_over_100),
    ("CON08", con08_de_rising_3yr),
    ("CON09", con09_eps_declining_3yr),
    ("CON10", con10_roce_weak),
    ("CON11", con11_net_debt_ebitda),
    ("CON12", con12_revenue_cagr_low),
]


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def evaluate_rules(ctx: dict, rules: list[tuple[str, callable]]) -> list[dict]:
    """Runs every rule for a company; returns ALL candidates (not yet
    confidence-filtered) so the fallback mechanism can inspect them."""
    candidates = []
    for rule_id, fn in rules:
        result = fn(ctx)
        if result is not None:
            text, confidence = result
            candidates.append(
                {"rule_id": rule_id, "text": text, "confidence_pct": confidence}
            )
    return candidates


def generate_for_company(conn: sqlite3.Connection, company_id: str) -> list[dict]:
    """Generate for company."""
    ctx = build_company_context(conn, company_id)

    pro_candidates = evaluate_rules(ctx, PRO_RULES)
    con_candidates = evaluate_rules(ctx, CON_RULES)

    output_rows = []
    for label, candidates in (("pro", pro_candidates), ("con", con_candidates)):
        passing = [c for c in candidates if c["confidence_pct"] > CONFIDENCE_FILTER]
        if passing:
            for c in passing:
                output_rows.append({"company_id": company_id, "type": label, **c})
        elif candidates:
            # Fallback: keep the single strongest candidate even if <= 60.
            best = max(candidates, key=lambda c: c["confidence_pct"])
            output_rows.append(
                {
                    "company_id": company_id,
                    "type": label,
                    "rule_id": best["rule_id"] + "_FALLBACK",
                    "text": best["text"],
                    "confidence_pct": best["confidence_pct"],
                }
            )
        else:
            # No rule produced ANY candidate — genuine data-scarcity case.
            note = (
                "Insufficient historical data available to assess business strengths in detail"
                if label == "pro"
                else "Insufficient historical data available to assess business risks in detail"
            )
            output_rows.append(
                {
                    "company_id": company_id,
                    "type": label,
                    "rule_id": "NODATA_FALLBACK",
                    "text": note,
                    "confidence_pct": 61.0,
                }
            )

    return output_rows


def write_csv(path: Path, rows: list[dict]) -> None:
    """Write csv."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["company_id", "type", "rule_id", "text", "confidence_pct"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Wrote %d rows -> %s", len(rows), path)


def main() -> None:
    """Main."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    conn = get_connection()
    try:
        assert_schema(conn)
        company_ids = sorted(r["id"] for r in conn.execute("SELECT id FROM companies"))
        logger.info("Generating pros/cons for %d companies", len(company_ids))

        all_rows = []
        fallback_count = 0
        nodata_count = 0
        for company_id in company_ids:
            rows = generate_for_company(conn, company_id)
            all_rows.extend(rows)
            fallback_count += sum(
                1
                for r in rows
                if r["rule_id"].endswith("_FALLBACK")
                and r["rule_id"] != "NODATA_FALLBACK"
            )
            nodata_count += sum(1 for r in rows if r["rule_id"] == "NODATA_FALLBACK")

        write_csv(OUTPUT_DIR / "pros_cons_generated.csv", all_rows)

        # Verification: every company must have >=1 pro and >=1 con
        by_company: dict[str, set[str]] = {}
        for r in all_rows:
            by_company.setdefault(r["company_id"], set()).add(r["type"])
        missing = [
            cid for cid in company_ids if by_company.get(cid, set()) != {"pro", "con"}
        ]

        pros = [r for r in all_rows if r["type"] == "pro"]
        cons = [r for r in all_rows if r["type"] == "con"]

        print("\n=== Day 30 Summary ===")
        print(f"Companies processed:        {len(company_ids)}")
        print(f"Total rows generated:       {len(all_rows)}")
        print(f"  Pros:                     {len(pros)}")
        print(f"  Cons:                     {len(cons)}")
        print(f"Companies using fallback (best-of, <=60%): {fallback_count} row(s)")
        print(f"Companies using NODATA fallback:            {nodata_count} row(s)")
        print(f"Companies missing pro AND/OR con (should be 0): {len(missing)}")
        if missing:
            print(f"  {missing}")

        rule_counts: dict[str, int] = {}
        for r in all_rows:
            rule_counts[r["rule_id"]] = rule_counts.get(r["rule_id"], 0) + 1
        print("\nRule trigger counts:")
        for rule_id in sorted(rule_counts):
            print(f"  {rule_id}: {rule_counts[rule_id]}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
