"""
src/etl/day33_diagnose_tcs_bs.py

One-off diagnostic: TCS's Balance Sheet Composition chart (Day 33
tearsheet) showed an unexpected "2024-09" year alongside the expected
March fiscal year-end sequence. TCS reports on a March FYE throughout
this project (no prior finding says otherwise) — checking whether this
is a genuine interim/duplicate row that slipped past Sprint 1's
dedup engine, or a legitimate data point.
"""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"


def main() -> None:
    """Main."""
    conn = sqlite3.connect(DB_PATH)

    print("--- TCS balancesheet: ALL rows ---")
    rows = conn.execute(
        "SELECT year, equity_capital, reserves, borrowings, total_assets, total_liabilities "
        "FROM balancesheet WHERE company_id = 'TCS' ORDER BY year"
    ).fetchall()
    for r in rows:
        print(r)

    print(f"\nTotal TCS balancesheet rows: {len(rows)}")

    print("\n--- Comparing 2024-03 vs 2024-09 directly ---")
    for year in ["2024-03", "2024-09"]:
        row = conn.execute(
            "SELECT * FROM balancesheet WHERE company_id = 'TCS' AND year = ?", (year,)
        ).fetchone()
        print(f"{year}: {row}")

    conn.close()


if __name__ == "__main__":
    main()
