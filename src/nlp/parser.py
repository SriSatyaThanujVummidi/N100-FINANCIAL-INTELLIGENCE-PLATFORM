"""

Day 29 — Sprint 5, Module 9 (NLP & Qualitative Analysis)
Parses period/value pairs out of analysis.xlsx's free-text growth fields
using the regex pattern from spec Section 9.1: (\d+)\s*Years?:?\s*([\d.]+)%

Outputs:
    output/analysis_parsed.csv   - company_id, metric_type, period_years, value_pct
    output/parse_failures.csv    - company_id, field, raw_text, reason
    output/cross_validation.csv  - company_id, metric_type, period_years,
                                    parsed_value_pct, computed_value_pct,
                                    diff_pct, flag, note

Known real-data context (see PROGRESS.md):
  - analysis.xlsx has ~8 companies in the raw file; WIPRO is FK-rejected
    at load (Sprint 1 Day 5). Expect ~4-7 companies loaded here — under
    investigation via day29_diagnose_analysis_coverage.py.
  - financial_ratios only persists 5yr-window CAGR columns
    (revenue_cagr_5yr, pat_cagr_5yr, eps_cagr_5yr) — Sprint 3 Day 15/16
    finding. 3yr/10yr windows are recomputed here from profitandloss,
    independently of src/analytics/cagr.py, purely for cross-checking.

Day 29 real-data fix: spec's literal pattern ([\d.]+) cannot capture a
leading minus sign, so negative values (e.g. "1 Year: -2%", confirmed in
SBILIFE.stock_price_cagr) were silently mis-logged as NO_REGEX_MATCH.
Widened to (-?[\d.]+) to capture negative CAGR/growth values correctly.
"""

import csv
import logging
import re
import sqlite3
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

PATTERN = re.compile(r"(\d+)\s*Years?:?\s*(-?[\d.]+)%")

TARGET_FIELDS = [
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
]

# metric_type -> (profitandloss column, financial_ratios 5yr column)
CAGR_FIELD_MAP = {
    "compounded_sales_growth": ("sales", "revenue_cagr_5yr"),
    "compounded_profit_growth": ("net_profit", "pat_cagr_5yr"),
}

DIVERGENCE_THRESHOLD_PCT = 5.0

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    """Get connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def extract_period_value(raw_text: str) -> Optional[tuple[int, float]]:
    """Extract (period_years, value_pct) from text like '10 Years: 21%'
    or '1 Year: -2%'. Returns None if the pattern doesn't match."""
    match = PATTERN.search(raw_text)
    if match is None:
        return None
    return int(match.group(1)), float(match.group(2))


def shift_fiscal_year(year_str: str, years_back: int) -> str:
    """'2024-03' shifted back 5 -> '2019-03'. Preserves fiscal month so a
    Sep/Dec-FYE company (SIEMENS/NESTLEIND-style) is handled correctly."""
    yyyy, mm = year_str.split("-")
    return f"{int(yyyy) - years_back:04d}-{mm}"


def parse_analysis_table(conn: sqlite3.Connection) -> tuple[list[dict], list[dict]]:
    """Parse every target field of every row in `analysis`.
    Returns (parsed_rows, failure_rows)."""
    cur = conn.execute(
        "SELECT id, company_id, compounded_sales_growth, "
        "compounded_profit_growth, stock_price_cagr, roe FROM analysis"
    )
    rows = cur.fetchall()
    logger.info("Loaded %d rows from analysis table", len(rows))

    parsed: list[dict] = []
    failures: list[dict] = []

    for row in rows:
        company_id = row["company_id"]
        for field in TARGET_FIELDS:
            raw = row[field]
            if raw is None or (isinstance(raw, str) and raw.strip() == ""):
                continue  # no data for this field on this row — not a failure

            raw_str = str(raw).strip()
            result = extract_period_value(raw_str)
            if result is None:
                failures.append(
                    {
                        "company_id": company_id,
                        "field": field,
                        "raw_text": raw_str,
                        "reason": "NO_REGEX_MATCH",
                    }
                )
                logger.warning(
                    "No regex match: company=%s field=%s raw=%r",
                    company_id,
                    field,
                    raw_str,
                )
                continue

            period_years, value_pct = result
            parsed.append(
                {
                    "company_id": company_id,
                    "metric_type": field,
                    "period_years": period_years,
                    "value_pct": value_pct,
                }
            )

    # De-duplicate exact repeats — analysis.xlsx has multiple rows per
    # company (period variants) and can carry an identical text twice.
    seen = set()
    deduped = []
    for r in parsed:
        key = (r["company_id"], r["metric_type"], r["period_years"], r["value_pct"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    if len(deduped) != len(parsed):
        logger.info(
            "Removed %d exact-duplicate parsed rows", len(parsed) - len(deduped)
        )

    return deduped, failures


def compute_pl_cagr(
    conn: sqlite3.Connection, company_id: str, pl_column: str, window_years: int
) -> Optional[float]:
    """Compute CAGR for pl_column (sales/net_profit) over the most recent
    window_years, using THIS company's own latest reported year."""
    cur = conn.execute(
        "SELECT MAX(year) AS latest FROM profitandloss WHERE company_id = ?",
        (company_id,),
    )
    latest_row = cur.fetchone()
    if latest_row is None or latest_row["latest"] is None:
        return None
    end_year = latest_row["latest"]
    start_year = shift_fiscal_year(end_year, window_years)

    def get_value(year: str) -> Optional[float]:
        # pl_column comes only from CAGR_FIELD_MAP's fixed internal
        # whitelist ("sales" / "net_profit") — never external input.
        """Get value."""
        cur2 = conn.execute(
            f"SELECT {pl_column} FROM profitandloss WHERE company_id = ? AND year = ?",
            (company_id, year),
        )
        r = cur2.fetchone()
        return r[pl_column] if r is not None else None

    end_val = get_value(end_year)
    base_val = get_value(start_year)

    if base_val is None or end_val is None or base_val == 0:
        return None
    if base_val > 0 and end_val < 0:
        return None  # DECLINE_TO_LOSS
    if base_val < 0 and end_val > 0:
        return None  # TURNAROUND
    if base_val < 0 and end_val < 0:
        return None  # BOTH_NEGATIVE

    return ((end_val / base_val) ** (1 / window_years) - 1) * 100


def get_5yr_column(
    conn: sqlite3.Connection, company_id: str, column: str
) -> Optional[float]:
    """Get 5yr column."""
    cur = conn.execute(
        f"SELECT {column} FROM financial_ratios WHERE company_id = ? ORDER BY year DESC LIMIT 1",
        (company_id,),
    )
    r = cur.fetchone()
    return r[column] if r is not None else None


def get_avg_roe(
    conn: sqlite3.Connection, company_id: str, window_years: int
) -> Optional[float]:
    """Average return_on_equity_pct over the most recent window_years
    reported rows (skips None years; doesn't require exactly N rows)."""
    cur = conn.execute(
        "SELECT return_on_equity_pct FROM financial_ratios "
        "WHERE company_id = ? AND return_on_equity_pct IS NOT NULL "
        "ORDER BY year DESC LIMIT ?",
        (company_id, window_years),
    )
    values = [r["return_on_equity_pct"] for r in cur.fetchall()]
    return sum(values) / len(values) if values else None


def cross_validate(conn: sqlite3.Connection, parsed_rows: list[dict]) -> list[dict]:
    """Cross validate."""
    results = []
    for row in parsed_rows:
        metric_type = row["metric_type"]
        company_id = row["company_id"]
        period = row["period_years"]
        parsed_value = row["value_pct"]

        computed_value: Optional[float] = None
        note = ""

        if metric_type in CAGR_FIELD_MAP:
            pl_column, col_5yr = CAGR_FIELD_MAP[metric_type]
            if period == 5:
                computed_value = get_5yr_column(conn, company_id, col_5yr)
                note = f"from financial_ratios.{col_5yr}"
            else:
                computed_value = compute_pl_cagr(conn, company_id, pl_column, period)
                note = f"on-the-fly {period}yr CAGR from profitandloss.{pl_column}"
        elif metric_type == "roe":
            computed_value = get_avg_roe(conn, company_id, period)
            note = f"avg return_on_equity_pct, trailing {period}yr"
        elif metric_type == "stock_price_cagr":
            note = "no computed equivalent built in this project yet"

        if computed_value is None:
            flag, diff_pct = "SKIPPED_NO_COMPUTED_VALUE", None
        elif computed_value == 0:
            flag, diff_pct = "SKIPPED_ZERO_BASE", None
        else:
            diff_pct = abs(parsed_value - computed_value) / abs(computed_value) * 100
            flag = "DIVERGENCE_FLAGGED" if diff_pct > DIVERGENCE_THRESHOLD_PCT else "OK"

        results.append(
            {
                "company_id": company_id,
                "metric_type": metric_type,
                "period_years": period,
                "parsed_value_pct": parsed_value,
                "computed_value_pct": computed_value,
                "diff_pct": round(diff_pct, 2) if diff_pct is not None else None,
                "flag": flag,
                "note": note,
            }
        )
    return results


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    """Write csv."""
    path.parent.mkdir(parents=True, exist_ok=True)
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
        parsed_rows, failure_rows = parse_analysis_table(conn)

        write_csv(
            OUTPUT_DIR / "analysis_parsed.csv",
            parsed_rows,
            ["company_id", "metric_type", "period_years", "value_pct"],
        )
        write_csv(
            OUTPUT_DIR / "parse_failures.csv",
            failure_rows,
            ["company_id", "field", "raw_text", "reason"],
        )

        cross_val_rows = cross_validate(conn, parsed_rows)
        write_csv(
            OUTPUT_DIR / "cross_validation.csv",
            cross_val_rows,
            [
                "company_id",
                "metric_type",
                "period_years",
                "parsed_value_pct",
                "computed_value_pct",
                "diff_pct",
                "flag",
                "note",
            ],
        )

        companies_covered = sorted({r["company_id"] for r in parsed_rows})
        flagged = [r for r in cross_val_rows if r["flag"] == "DIVERGENCE_FLAGGED"]

        print("\n=== Day 29 Summary ===")
        print(f"Parsed metric rows:      {len(parsed_rows)}")
        print(f"Parse failures:          {len(failure_rows)}")
        print(
            f"Companies covered:       {len(companies_covered)} -> {companies_covered}"
        )
        print(f"Cross-validation rows:   {len(cross_val_rows)}")
        print(f"Divergence > {DIVERGENCE_THRESHOLD_PCT}% flagged: {len(flagged)}")
        for r in flagged:
            print(
                f"  {r['company_id']} / {r['metric_type']} / {r['period_years']}yr: "
                f"parsed={r['parsed_value_pct']}% computed={r['computed_value_pct']}% diff={r['diff_pct']}%"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
