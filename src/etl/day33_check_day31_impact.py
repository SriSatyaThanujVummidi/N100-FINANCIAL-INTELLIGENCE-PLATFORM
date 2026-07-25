"""
src/analytics/day33_check_day31_impact.py

Day 33 finding: ~79 companies have a spurious 2024-09 interim row in
balancesheet only. Day 31's deleveraging_flag used
"ORDER BY year DESC LIMIT 2" on balancesheet — if a 2024-09 row exists,
that logic would compare 2024-09 vs 2024-03 (a 6-month gap) instead of
2024-03 vs 2023-03 (the intended annual-to-annual comparison). This
checks how many of Day 31's ALREADY-SIGNED-OFF deleveraging_flag results
would change if computed against the correct annual-only rows.
"""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"


def get_dominant_month(conn, company_id: str, table: str) -> str:
    """Get dominant month."""
    years = [
        r[0]
        for r in conn.execute(
            f"SELECT year FROM {table} WHERE company_id = ?", (company_id,)
        )
    ]
    months = [y.split("-")[1] for y in years]
    from collections import Counter

    return Counter(months).most_common(1)[0][0]


def deleveraging_naive(conn, company_id: str) -> tuple:
    """Day 31's ORIGINAL logic — unchanged, for comparison."""
    rows = conn.execute(
        "SELECT year, borrowings FROM balancesheet WHERE company_id = ? "
        "ORDER BY year DESC LIMIT 2",
        (company_id,),
    ).fetchall()
    cff_row = conn.execute(
        "SELECT financing_activity FROM cashflow WHERE company_id = ? "
        "ORDER BY year DESC LIMIT 1",
        (company_id,),
    ).fetchone()
    if len(rows) != 2 or cff_row is None or cff_row[0] is None:
        return None, None, None
    (y1, b1), (y2, b2) = rows
    cff = cff_row[0]
    if b1 is None or b2 is None:
        return None, y1, y2
    return bool(cff < 0 and b1 < b2), y1, y2


def deleveraging_fixed(conn, company_id: str, dominant_month: str) -> tuple:
    """Corrected — restricted to the company's own dominant fiscal month."""
    rows = conn.execute(
        "SELECT year, borrowings FROM balancesheet WHERE company_id = ? "
        "AND year LIKE ? ORDER BY year DESC LIMIT 2",
        (company_id, f"%-{dominant_month}"),
    ).fetchall()
    cff_row = conn.execute(
        "SELECT financing_activity FROM cashflow WHERE company_id = ? "
        "ORDER BY year DESC LIMIT 1",
        (company_id,),
    ).fetchone()
    if len(rows) != 2 or cff_row is None or cff_row[0] is None:
        return None, None, None
    (y1, b1), (y2, b2) = rows
    cff = cff_row[0]
    if b1 is None or b2 is None:
        return None, y1, y2
    return bool(cff < 0 and b1 < b2), y1, y2


def main() -> None:
    """Main."""
    conn = sqlite3.connect(DB_PATH)
    company_ids = sorted(r[0] for r in conn.execute("SELECT id FROM companies"))

    changed = []
    for cid in company_ids:
        dom_month = get_dominant_month(conn, cid, "balancesheet")
        naive_flag, naive_y1, naive_y2 = deleveraging_naive(conn, cid)
        fixed_flag, fixed_y1, fixed_y2 = deleveraging_fixed(conn, cid, dom_month)

        if naive_flag != fixed_flag:
            changed.append(
                (cid, naive_flag, naive_y1, naive_y2, fixed_flag, fixed_y1, fixed_y2)
            )

    print(f"Total companies: {len(company_ids)}")
    print(f"Companies where deleveraging_flag CHANGES after the fix: {len(changed)}\n")
    for cid, nf, ny1, ny2, ff, fy1, fy2 in changed:
        print(
            f"  {cid:15s} naive={nf} (compared {ny2} vs {ny1})  ->  fixed={ff} (compared {fy2} vs {fy1})"
        )

    conn.close()


if __name__ == "__main__":
    main()
