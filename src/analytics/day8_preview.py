"""
Day 8 — quick sanity-check preview.

Joins profitandloss + balancesheet + sectors on (company_id, year) and runs
compute_profitability_ratios() over real rows from the DB, so you can see
the Day-8 functions working against real data before Day 12's full table
population.

Usage (from project root, venv active):
    python src/analytics/day8_preview.py
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.analytics.ratios import compute_profitability_ratios

DB_PATH = "data/nifty100.db"  # adjust if your .env uses a different DB_PATH

# A few companies worth spot-checking: a normal one (TCS), the known
# zero-balance-sheet company (SBIN), and the late-starting-BS company (HAL).
SAMPLE_COMPANIES = ["TCS", "SBIN", "HAL"]


def fetch_rows(db_path: str, tickers: list[str]):
    """Fetch rows."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in tickers)
    query = f"""
        SELECT
            p.company_id, p.year, p.sales, p.operating_profit, p.opm_percentage,
            p.depreciation, p.net_profit,
            b.equity_capital, b.reserves, b.borrowings, b.total_assets,
            s.broad_sector
        FROM profitandloss p
        LEFT JOIN balancesheet b
            ON p.company_id = b.company_id AND p.year = b.year
        LEFT JOIN sectors s
            ON p.company_id = s.company_id
        WHERE p.company_id IN ({placeholders})
        ORDER BY p.company_id, p.year
    """
    rows = conn.execute(query, tickers).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def main():
    """Main."""
    rows = fetch_rows(DB_PATH, SAMPLE_COMPANIES)
    if not rows:
        print(f"No rows found — check DB_PATH ({DB_PATH}) and ticker list.")
        return

    for row in rows:
        result = compute_profitability_ratios(row)
        print(
            f"{result['company_id']:10s} {result['year']:>8s} | "
            f"NPM={fmt(result['net_profit_margin_pct'])} "
            f"OPM={fmt(result['operating_profit_margin_pct'])} "
            f"ROE={fmt(result['return_on_equity_pct'])} "
            f"ROCE={fmt(result['return_on_capital_employed_pct'])} "
            f"ROA={fmt(result['return_on_assets_pct'])} "
            f"sector={row.get('broad_sector')}"
        )


def fmt(value):
    """Fmt."""
    return "None " if value is None else f"{value:6.2f}"


if __name__ == "__main__":
    main()
