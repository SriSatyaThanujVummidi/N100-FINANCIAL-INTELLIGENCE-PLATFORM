"""Day 11 deliverable — generates output/capital_allocation.csv for all
companies x all years, per spec Day 11 / Deliverable D-06."""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import sqlite3
from analytics.cashflow_kpis import cfo_pat_ratio, capital_allocation_pattern

DB_PATH = "data/nifty100.db"
OUTPUT_PATH = "output/capital_allocation.csv"

QUERY = """
SELECT
    c.company_id, c.year,
    c.operating_activity, c.investing_activity, c.financing_activity,
    p.net_profit
FROM cashflow c
LEFT JOIN profitandloss p ON c.company_id = p.company_id AND c.year = p.year
ORDER BY c.company_id, c.year
"""


def main():
    """Main."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(QUERY)
    rows = cur.fetchall()
    conn.close()

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["company_id", "year", "cfo_sign", "cfi_sign", "cff_sign", "pattern_label"]
        )

        for company_id, year, cfo, cfi, cff, net_profit in rows:
            ratio = cfo_pat_ratio(cfo, net_profit)
            cfo_sign, cfi_sign, cff_sign, pattern_label = capital_allocation_pattern(
                cfo, cfi, cff, ratio
            )
            writer.writerow(
                [company_id, year, cfo_sign, cfi_sign, cff_sign, pattern_label]
            )

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
