"""Day 13 deliverable — generates output/ratio_edge_cases.log.

Walks every company's LATEST year in financial_ratios, cross-checks
computed ROE/ROCE against companies.xlsx's pre-computed roe_percentage/
roce_percentage fields, and logs every anomaly (diff > 5%) with a
category guess. Also runs the generic sanity-bound check (HAL
resolution, Option B) across every company-year, not just the latest.
"""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import sqlite3
from analytics.edge_cases import (
    roce_cross_check,
    roe_cross_check,
    flag_implausible_ratio,
)

DB_PATH = "data/nifty100.db"
LOG_PATH = "output/ratio_edge_cases.log"

logging.basicConfig(
    filename=LOG_PATH,
    filemode="w",
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # --- Part 1: ROE/ROCE cross-check, latest year only per company ---
    companies = conn.execute(
        "SELECT id, roe_percentage, roce_percentage FROM companies"
    ).fetchall()

    cross_check_anomalies = []
    for c in companies:
        latest = conn.execute(
            "SELECT year, return_on_equity_pct, return_on_capital_employed_pct "
            "FROM financial_ratios WHERE company_id = ? ORDER BY year DESC LIMIT 1",
            (c["id"],),
        ).fetchone()
        if latest is None:
            continue

        roe_result = roe_cross_check(
            c["id"], latest["year"], latest["return_on_equity_pct"], c["roe_percentage"]
        )
        roce_result = roce_cross_check(
            c["id"],
            latest["year"],
            latest["return_on_capital_employed_pct"],
            c["roce_percentage"],
        )
        if roe_result:
            cross_check_anomalies.append(roe_result)
        if roce_result:
            cross_check_anomalies.append(roce_result)

    # --- Part 2: generic sanity-bound check, every company-year ---
    all_rows = conn.execute(
        "SELECT company_id, year, return_on_equity_pct, return_on_capital_employed_pct, "
        "return_on_assets_pct, asset_turnover FROM financial_ratios"
    ).fetchall()

    implausible_count = 0
    for r in all_rows:
        for metric in (
            "return_on_equity_pct",
            "return_on_capital_employed_pct",
            "asset_turnover",
        ):
            value = r[metric] if metric in r.keys() else None
            if flag_implausible_ratio(metric, value):
                implausible_count += 1
                logger.warning(
                    "Sanity-bound violation company_id=%s year=%s metric=%s value=%s "
                    "(likely balance-sheet data anomaly, e.g. unit-conversion error)",
                    r["company_id"],
                    r["year"],
                    metric,
                    value,
                )

    conn.close()

    print(f"Cross-check anomalies (latest year): {len(cross_check_anomalies)}")
    for a in cross_check_anomalies:
        print(
            f"  {a['company_id']} {a['metric']}: computed={a['computed_value']} "
            f"source={a['source_value']} diff={a['diff_pct']} category={a['category']}"
        )
    print(f"\nSanity-bound violations (all years): {implausible_count}")
    print(f"\nFull log written to {LOG_PATH}")


if __name__ == "__main__":
    main()
