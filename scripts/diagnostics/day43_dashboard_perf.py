"""Day 43 -- Company Profile screen load time, 5 tickers, target <3s each.
Simulates the queries 02_profile.py runs: company + sector + full P&L/BS/CF history + latest ratios."""
import time
import sqlite3

TICKERS = ["TCS", "RELIANCE", "SBIN", "HDFCBANK", "HAL"]  # mix of normal + known edge cases

def load_company_profile(conn, ticker):
    conn.execute("SELECT * FROM companies WHERE id = ?", (ticker,)).fetchone()
    conn.execute("SELECT * FROM sectors WHERE company_id = ?", (ticker,)).fetchone()
    conn.execute("SELECT * FROM profitandloss WHERE company_id = ? ORDER BY year", (ticker,)).fetchall()
    conn.execute("SELECT * FROM balancesheet WHERE company_id = ? ORDER BY year", (ticker,)).fetchall()
    conn.execute("SELECT * FROM cashflow WHERE company_id = ? ORDER BY year", (ticker,)).fetchall()
    conn.execute("SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year", (ticker,)).fetchall()
    conn.execute(
        "SELECT * FROM prosandcons WHERE company_id = ?", (ticker,)
    ).fetchall()

conn = sqlite3.connect("data/nifty100.db")
print("Company Profile screen load time (target: <3s each):\n")
all_pass = True
for ticker in TICKERS:
    start = time.perf_counter()
    load_company_profile(conn, ticker)
    duration = time.perf_counter() - start
    status = "PASS" if duration < 3 else "FAIL"
    if duration >= 3:
        all_pass = False
    print(f"  {ticker:12} {duration*1000:.1f}ms  {status}")
conn.close()
print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")