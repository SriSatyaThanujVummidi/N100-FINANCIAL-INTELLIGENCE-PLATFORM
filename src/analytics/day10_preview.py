"""Day 10 sanity check — preview CAGR metrics for a handful of real companies."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import sqlite3
from analytics.cagr import compute_growth_metrics

DB_PATH = "data/nifty100.db"
SAMPLE_TICKERS = ["TCS", "SBIN", "HAL", "PNB", "JIOFIN"]

QUERY = """
SELECT year, sales, net_profit, eps
FROM profitandloss
WHERE company_id = ?
ORDER BY year
"""


def main():
    """Main."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for ticker in SAMPLE_TICKERS:
        cur.execute(QUERY, (ticker,))
        rows = cur.fetchall()
        if not rows:
            print(f"{ticker}: no P&L rows found")
            continue

        latest_year = rows[-1][0]
        sales_series = {r[0]: r[1] for r in rows}
        net_profit_series = {r[0]: r[2] for r in rows}
        eps_series = {r[0]: r[3] for r in rows}

        result = compute_growth_metrics(
            ticker, latest_year, sales_series, net_profit_series, eps_series
        )

        print(f"\n{ticker} (latest year: {latest_year}, {len(rows)} years of history):")
        for key, value in result.items():
            print(f"  {key}: {value}")
    conn.close()


if __name__ == "__main__":
    main()
