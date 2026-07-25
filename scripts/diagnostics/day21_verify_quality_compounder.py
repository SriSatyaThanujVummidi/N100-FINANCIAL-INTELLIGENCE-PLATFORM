"""Day 21 manual verification — Quality Compounder preset's top 5 must
all satisfy ROE>15% and D/E<1 (or Financials carve-out), per the Sprint 3
tracker's Day 21 exit criteria."""

import sqlite3

from src.screener.composite_score import compute_sector_relative_composite_score
from src.screener.engine import load_config, load_screener_universe, run_custom_screen

DB_PATH = "data/nifty100.db"


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    config = load_config()

    universe = load_screener_universe(conn)
    universe = compute_sector_relative_composite_score(universe, conn)

    preset = config["presets"]["quality_compounder"]
    result = run_custom_screen(
        universe, preset["filters"], preset["rank_by"], config,
        exclude_sectors=preset.get("exclude_sectors"),
    )

    print(f"Quality Compounder: {len(result)} companies\n")
    print("--- top 5, manual verification against ROE>15% and D/E<1 (or Financials) ---")
    top5 = result.head(5)
    for _, row in top5.iterrows():
        roe_ok = row["return_on_equity_pct"] > 15
        de_ok = row["debt_to_equity"] < 1.0 or row["broad_sector"] == "Financials"
        status = "PASS" if (roe_ok and de_ok) else "FAIL"
        print(
            f"{row['company_id']:12s} ROE={row['return_on_equity_pct']:6.1f}%  "
            f"D/E={row['debt_to_equity']:.2f}  sector={row['broad_sector']:22s} [{status}]"
        )

    conn.close()


if __name__ == "__main__":
    main()