"""


One-off diagnostic: checks whether Day 31's 13 distress-flagged companies
are concentrated in Financials (where negative CFO + positive CFF is a
structurally normal lending-business pattern, not real distress) before
deciding whether to add a sector carve-out.
"""

import csv
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
ALERTS_CSV = PROJECT_ROOT / "output" / "distress_alerts.csv"


def main() -> None:
    """Main."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    sectors = {
        r["company_id"]: r["broad_sector"]
        for r in conn.execute("SELECT company_id, broad_sector FROM sectors")
    }

    with open(ALERTS_CSV, newline="", encoding="utf-8") as f:
        alerts = list(csv.DictReader(f))

    print(f"Total distress-flagged: {len(alerts)}\n")
    financials = []
    non_financials = []
    for a in alerts:
        sector = sectors.get(a["company_id"], "UNKNOWN")
        line = f"  {a['company_id']:15s} sector={sector:12s} CFO={float(a['cfo']):>12,.0f} CFF={float(a['cff']):>12,.0f} NetProfit={float(a['net_profit']):>10,.0f}"
        if sector == "Financials":
            financials.append(line)
        else:
            non_financials.append(line)

    print(f"Financials ({len(financials)}):")
    for line in financials:
        print(line)
    for line in non_financials:
        print(line)

    conn.close()


if __name__ == "__main__":
    main()
