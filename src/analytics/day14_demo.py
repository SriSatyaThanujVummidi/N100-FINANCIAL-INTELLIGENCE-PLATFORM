"""Day 14 — demo script: show 5 sample companies' financial_ratios rows
to the team lead. Covers a normal large-cap (TCS), a missing-BS company
(SBIN), a known anomaly (HAL), a large conglomerate (RELIANCE), and
another normal IT company (INFY) -- one view spanning the
normal/missing-data/anomaly cases discussed across Sprint 2.
"""

import sqlite3

DB_PATH = "data/nifty100.db"
SAMPLE_TICKERS = ["TCS", "SBIN", "HAL", "RELIANCE", "INFY"]


def main():
    """Main."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    placeholders = ",".join("?" for _ in SAMPLE_TICKERS)
    query = f"""
        SELECT * FROM financial_ratios
        WHERE company_id IN ({placeholders})
        ORDER BY company_id, year DESC
    """
    rows = conn.execute(query, SAMPLE_TICKERS).fetchall()

    seen = set()
    for r in rows:
        if r["company_id"] in seen:
            continue  # only show each company's latest year for this demo
        seen.add(r["company_id"])
        print(f"\n--- {r['company_id']} ({r['year']}) ---")
        for key in r.keys():
            print(f"  {key}: {r[key]}")

    conn.close()


if __name__ == "__main__":
    main()
