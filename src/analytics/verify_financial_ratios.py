"""Day 12 verification — row count check + manual spot-check helper.

Per spec Day 12 exit criteria:
  - SELECT COUNT(*) FROM financial_ratios must be >= 1,100
  - Manually recompute ROE and 5yr Revenue CAGR for 3 companies and
    compare to the database value (must match within 0.1%)

This script does the row-count check automatically, and for the manual
spot-check it prints both the DB value AND the raw inputs needed to redo
the calculation by hand in Excel -- so you can verify quickly without
writing your own SQL each time.
"""

import sqlite3

DB_PATH = "data/nifty100.db"
SAMPLE_TICKERS = [
    "TCS",
    "INFY",
    "RELIANCE",
]  # swap in whichever 3 you want to spot-check


def main():
    """Main."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    count = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
    print(f"financial_ratios row count: {count} (spec requires >= 1,100)\n")

    for ticker in SAMPLE_TICKERS:
        latest = conn.execute(
            "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year DESC LIMIT 1",
            (ticker,),
        ).fetchone()
        if latest is None:
            print(f"{ticker}: no financial_ratios row found\n")
            continue

        year = latest["year"]
        print(f"--- {ticker} ({year}) ---")
        print(f"  DB return_on_equity_pct: {latest['return_on_equity_pct']}")
        print(f"  DB revenue_cagr_5yr:     {latest['revenue_cagr_5yr']}")

        pl = conn.execute(
            "SELECT net_profit, sales FROM profitandloss WHERE company_id=? AND year=?",
            (ticker, year),
        ).fetchone()
        bs = conn.execute(
            "SELECT equity_capital, reserves FROM balancesheet WHERE company_id=? AND year=?",
            (ticker, year),
        ).fetchone()
        if (
            pl
            and bs
            and bs["equity_capital"] is not None
            and bs["reserves"] is not None
        ):
            equity = bs["equity_capital"] + bs["reserves"]
            if equity:
                hand_roe = pl["net_profit"] / equity * 100
                print(
                    f"  Hand-check ROE: net_profit={pl['net_profit']} / "
                    f"(equity_capital={bs['equity_capital']} + reserves={bs['reserves']}) "
                    f"x 100 = {hand_roe:.4f}"
                )

        five_years_ago = f"{int(year[:4]) - 5}{year[4:]}"
        pl_start = conn.execute(
            "SELECT sales FROM profitandloss WHERE company_id=? AND year=?",
            (ticker, five_years_ago),
        ).fetchone()
        if pl and pl_start and pl_start["sales"]:
            start_sales = pl_start["sales"]
            end_sales = pl["sales"]
            hand_cagr = ((end_sales / start_sales) ** (1 / 5) - 1) * 100
            print(
                f"  Hand-check Revenue CAGR: ((sales[{year}]={end_sales} / "
                f"sales[{five_years_ago}]={start_sales}) ^ (1/5) - 1) x 100 = {hand_cagr:.4f}"
            )
        print()

    conn.close()


if __name__ == "__main__":
    main()
