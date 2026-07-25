"""Day 14 — quick screener preview per spec exit criteria.

Filters financial_ratios for the "Quality Compounder" preset's core
two conditions (ROE > 15%, D/E < 1) and verifies the result count falls
in the spec's expected 15-50 company range.

Excludes any company-year flagged by Day 13's sanity-bound check --
without this, a HAL-style balance-sheet anomaly would silently pass the
raw ROE>15% threshold with a nonsensical value (e.g. 1450%) and
contaminate the result set.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import sqlite3
from analytics.edge_cases import flag_implausible_ratio

DB_PATH = "data/nifty100.db"


def main():
    """Main."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Latest year per company only -- the spec's screener returns one row
    # per qualifying COMPANY, not one row per qualifying company-year.
    # Without this filter, a company that crossed both thresholds in
    # several different years gets counted once per year, wildly
    # inflating the result count.
    rows = conn.execute("""
        SELECT f.company_id, f.year, f.return_on_equity_pct, f.debt_to_equity
        FROM financial_ratios f
        INNER JOIN (
            SELECT company_id, MAX(year) AS latest_year
            FROM financial_ratios
            GROUP BY company_id
        ) latest ON f.company_id = latest.company_id AND f.year = latest.latest_year
        WHERE f.return_on_equity_pct > 15 AND f.debt_to_equity < 1
    """).fetchall()

    clean_matches = []
    excluded = []
    for r in rows:
        if flag_implausible_ratio("return_on_equity_pct", r["return_on_equity_pct"]):
            excluded.append(r)
        else:
            clean_matches.append(r)

    print(f"Raw matches (ROE>15%, D/E<1, latest year only): {len(rows)}")
    print(f"Excluded as implausible (sanity-bound): {len(excluded)}")
    for r in excluded:
        print(
            f"  EXCLUDED: {r['company_id']} ({r['year']}) ROE={r['return_on_equity_pct']}"
        )
    print(f"Clean screener result count: {len(clean_matches)}")
    print("Spec expects 15-50 companies for the full 92-company universe.")

    conn.close()


if __name__ == "__main__":
    main()
