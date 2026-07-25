"""Day 17 — compute the sector-relative composite score against the real
92-company universe. Specifically checking SIEMENS, whose Sprint 2 global
score was frozen at ~60 across its entire 14-year history (Day 15/16
finding, single-company fiscal-year cohort)."""

import sqlite3

from src.screener.engine import load_screener_universe
from src.screener.composite_score import compute_sector_relative_composite_score

DB_PATH = "data/nifty100.db"


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    universe = load_screener_universe(conn)

    result = compute_sector_relative_composite_score(universe, conn)

    print(f"Universe: {len(result)} companies")
    non_null = result["composite_score_sector_relative"].notna().sum()
    print(f"Non-null composite_score_sector_relative: {non_null}/{len(result)}\n")

    print("--- SIEMENS: old (Sprint 2 global) vs new (Day 17 sector-relative) ---")
    siemens = result[result["company_id"] == "SIEMENS"]
    print(siemens[["company_id", "broad_sector", "composite_quality_score",
                    "composite_score_sector_relative"]].to_string(index=False))

    print()
    print("--- Industrials sector peer group (SIEMENS's real comparison pool) ---")
    industrials = result[result["broad_sector"] == "Industrials"].sort_values(
        "composite_score_sector_relative", ascending=False
    )
    print(f"Industrials sector size: {len(industrials)}")
    print(industrials[["company_id", "composite_quality_score",
                        "composite_score_sector_relative"]].to_string(index=False))

    print()
    print("--- top 10 overall by new sector-relative score ---")
    top10 = result.sort_values("composite_score_sector_relative", ascending=False).head(10)
    print(top10[["company_id", "broad_sector", "composite_score_sector_relative"]].to_string(index=False))

    print()
    print("--- companies with None composite_score_sector_relative (missing sub-data) ---")
    missing = result[result["composite_score_sector_relative"].isna()]
    print(missing[["company_id", "broad_sector"]].to_string(index=False))

    conn.close()


if __name__ == "__main__":
    main()