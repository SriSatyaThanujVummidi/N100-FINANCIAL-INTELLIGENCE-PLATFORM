"""Day 16 — run Turnaround Watch against the real 92-company universe."""

import sqlite3

from src.screener.engine import load_screener_universe
from src.screener.turnaround import run_turnaround_watch

DB_PATH = "data/nifty100.db"


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    universe = load_screener_universe(conn)

    result = run_turnaround_watch(universe, conn)

    lo, hi = 5, 15
    count = len(result)
    status = "OK" if lo <= count <= hi else "OUT OF EXPECTED RANGE"

    print(f"TURNAROUND_WATCH  ->  {count} companies  [expected {lo}-{hi}]  {status}")
    print(result[["company_id", "broad_sector", "revenue_cagr_3yr", "free_cash_flow_cr"]].to_string(index=False))

    conn.close()


if __name__ == "__main__":
    main()