"""
src/etl/day33_diagnose_offcycle_years.py

Day 33 follow-up: TCS's balancesheet table contains a 2024-09 row (interim
H1 report) alongside its normal March-FYE annual sequence — confirmed via
day33_diagnose_tcs_bs.py to hold genuinely different (not duplicate)
values. Checking whether this is a TCS-specific anomaly or a systemic
pattern across the other 91 companies, and across profitandloss/cashflow
too, before deciding on a project-wide fix ahead of Day 34's batch run.

Approach: for each company, determine its dominant fiscal-month (the
month suffix that appears most often in its own year history — e.g. '03'
for TCS/most companies, '09' for SIEMENS, '12' for NESTLEIND, per Day 15's
finding). Any row whose month suffix does NOT match that company's own
dominant month is flagged as a likely off-cycle/interim row.
"""

import sqlite3
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"


def find_offcycle_rows(conn: sqlite3.Connection, table: str) -> list[tuple]:
    """Find offcycle rows."""
    company_ids = sorted(r[0] for r in conn.execute("SELECT id FROM companies"))
    offcycle = []

    for cid in company_ids:
        years = [
            r[0]
            for r in conn.execute(
                f"SELECT year FROM {table} WHERE company_id = ?", (cid,)
            )
        ]
        if not years:
            continue

        months = [y.split("-")[1] for y in years if "-" in y]
        if not months:
            continue

        dominant_month, dominant_count = Counter(months).most_common(1)[0]

        for y in years:
            month = y.split("-")[1] if "-" in y else None
            if month != dominant_month:
                offcycle.append(
                    (cid, table, y, dominant_month, dominant_count, len(years))
                )

    return offcycle


def main() -> None:
    """Main."""
    conn = sqlite3.connect(DB_PATH)

    all_offcycle = []
    for table in ["balancesheet", "profitandloss", "cashflow"]:
        rows = find_offcycle_rows(conn, table)
        all_offcycle.extend(rows)
        print(f"\n--- Off-cycle rows in {table}: {len(rows)} ---")
        for cid, tbl, year, dom_month, dom_count, total in rows:
            print(
                f"  {cid:15s} year={year:10s} (company's dominant month='{dom_month}', "
                f"{dom_count}/{total} rows match it)"
            )

    affected_companies = sorted({r[0] for r in all_offcycle})
    print("\n=== Summary ===")
    print(f"Total off-cycle rows across all 3 tables: {len(all_offcycle)}")
    print(f"Companies affected: {len(affected_companies)} -> {affected_companies}")

    conn.close()


if __name__ == "__main__":
    main()
