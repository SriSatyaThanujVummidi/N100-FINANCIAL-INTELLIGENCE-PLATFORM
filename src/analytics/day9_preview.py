"""Day 9 sanity check — preview leverage & efficiency KPIs for a handful of real companies."""

import os
import sys

# Running this file directly only puts its own folder (src/analytics) on
# sys.path, not src/ itself -- so "from analytics.ratios import ..." fails
# with ModuleNotFoundError. Add src/ explicitly, same as conftest.py does
# for pytest.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import sqlite3
from analytics.ratios import compute_leverage_efficiency_ratios

DB_PATH = "data/nifty100.db"
SAMPLE_TICKERS = ["TCS", "SBIN", "HAL", "PNB", "ADANIENSOL"]

DB_PATH = "data/nifty100.db"
SAMPLE_TICKERS = ["TCS", "SBIN", "HAL", "PNB", "ADANIENSOL"]

QUERY = """
SELECT
    p.company_id, p.year,
    p.sales, p.operating_profit, p.other_income, p.interest,
    b.borrowings, b.equity_capital, b.reserves, b.investments, b.total_assets,
    s.broad_sector
FROM profitandloss p
LEFT JOIN balancesheet b ON p.company_id = b.company_id AND p.year = b.year
LEFT JOIN sectors s ON p.company_id = s.company_id
WHERE p.company_id = ?
ORDER BY p.year DESC
LIMIT 1
"""


def main():
    """Main."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    for ticker in SAMPLE_TICKERS:
        cur.execute(QUERY, (ticker,))
        row = cur.fetchone()
        if row is None:
            print(f"{ticker}: no P&L row found")
            continue
        result = compute_leverage_efficiency_ratios(dict(row))
        print(f"\n{ticker} ({row['year']}):")
        for key, value in result.items():
            print(f"  {key}: {value}")
    conn.close()


if __name__ == "__main__":
    main()
