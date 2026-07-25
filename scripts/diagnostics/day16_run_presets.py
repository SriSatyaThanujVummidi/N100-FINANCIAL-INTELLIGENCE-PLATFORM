"""Day 16 — run the 5 threshold-based preset screeners against the full
92-company universe. Turnaround Watch (multi-year logic) is handled
separately in day16_turnaround.py.
"""

import sqlite3

from src.screener.engine import load_config, load_screener_universe, run_custom_screen

DB_PATH = "data/nifty100.db"

THRESHOLD_PRESETS = [
    "quality_compounder",
    "value_pick",
    "growth_accelerator",
    "dividend_champion",
    "debt_free_blue_chip",
]


def main() -> None:
    config = load_config()
    conn = sqlite3.connect(DB_PATH)
    universe = load_screener_universe(conn)
    print(f"Universe loaded: {len(universe)} companies\n")

    for preset_name in THRESHOLD_PRESETS:
        preset = config["presets"][preset_name]
        result = run_custom_screen(
            universe,
            preset["filters"],
            preset["rank_by"],
            config,
            exclude_sectors=preset.get("exclude_sectors"),
        )

        lo, hi = preset["expected_count"]
        count = len(result)
        status = "OK" if lo <= count <= hi else "OUT OF EXPECTED RANGE"

        print("=" * 78)
        print(f"{preset_name.upper()}  ->  {count} companies  [expected {lo}-{hi}]  {status}")
        print("=" * 78)
        # Day 16 fix: rank_by in the config is a metric KEY (e.g. 'dividend_yield'),
        # translate through config['metrics'] before indexing the result DataFrame,
        # same fix as engine.py's run_custom_screen().
        resolved_rank_by = config["metrics"].get(preset["rank_by"], preset["rank_by"])
        cols = ["company_id", "broad_sector", resolved_rank_by]
        print(result[cols].head(10).to_string(index=False))
        print()

    conn.close()


if __name__ == "__main__":
    main()