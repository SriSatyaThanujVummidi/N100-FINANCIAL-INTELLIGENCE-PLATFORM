"""
Diagnostic: print raw balancesheet rows for HAL to investigate the
implausible ROE/ROCE/ROA values seen from FY2016 onward in day8_preview.py.
"""

import sqlite3

DB_PATH = "data/nifty100.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("--- Raw balancesheet rows for HAL ---")
rows = conn.execute(
    "SELECT * FROM balancesheet WHERE company_id = 'HAL' ORDER BY year"
).fetchall()
for r in rows:
    d = dict(r)
    equity = (d.get("equity_capital") or 0) + (d.get("reserves") or 0)
    print(
        f"year={d.get('year'):>8} equity_capital={d.get('equity_capital')!s:>10} "
        f"reserves={d.get('reserves')!s:>12} equity+reserves={equity:>12} "
        f"borrowings={d.get('borrowings')!s:>10} total_assets={d.get('total_assets')!s:>12}"
    )

print("\n--- Row count check: any duplicate (company_id, year) for HAL? ---")
dupes = conn.execute(
    "SELECT year, COUNT(*) FROM balancesheet WHERE company_id='HAL' GROUP BY year HAVING COUNT(*) > 1"
).fetchall()
print(dupes if dupes else "No duplicates found.")

conn.close()