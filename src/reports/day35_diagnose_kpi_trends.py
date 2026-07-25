"""

Day 35: the portfolio summary's ">=4/6 N/A" watchlist came back EMPTY,
which is suspicious given known data gaps (SBIN's missing balance sheet,
JIOFIN's 2yr history, HAL/BEL/INDIGO/ICICIPRULI/HDFCLIFE's sanity-masked
ROE/ROCE). Dumps the raw KPI/trend output for these companies directly,
rather than trusting the summary's own count.
"""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"

import sys

sys.path.insert(0, str(PROJECT_ROOT))
from src.reports.portfolio_summary import get_company_kpi_trends, get_last_two_years


def main() -> None:
    """Main."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    watch_list = ["SBIN", "JIOFIN", "HAL", "BEL", "INDIGO", "ICICIPRULI", "HDFCLIFE"]

    for cid in watch_list:
        latest, prior = get_last_two_years(conn, cid)
        print(f"\n{cid}:")
        print(f"  latest year row exists: {latest is not None}")
        print(f"  prior year row exists:  {prior is not None}")
        if latest:
            print(f"  latest year: {latest.get('year')}")
        if prior:
            print(f"  prior year:  {prior.get('year')}")

        kpis = get_company_kpi_trends(conn, cid)
        na_count = sum(1 for k in kpis if k["arrow"] == "na")
        print(f"  N/A arrow count: {na_count}/6")
        for k in kpis:
            print(f"    {k['label']:20s} value={k['value_str']:15s} arrow={k['arrow']}")

    conn.close()


if __name__ == "__main__":
    main()
