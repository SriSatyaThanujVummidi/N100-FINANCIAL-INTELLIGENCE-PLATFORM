"""

Day 34 — Sprint 5, Module 8 (Batch Report Generation, part 1)
Runs Day 33's build_tearsheet() across all 92 companies.

Per spec: skip companies with fewer than 3 years of data (logged to
output/skipped_tearsheets.csv), rather than crash or produce a
near-empty tearsheet.

"Years of data" is measured from profitandloss row count — the P&L
Revenue/Net Profit chart and KPI tiles are the most fundamental page-1
content; a company with <3 P&L years can't produce a meaningful
tearsheet regardless of BS/CF coverage.
"""

import csv
import logging
import tempfile
from pathlib import Path

from src.reports.tearsheet import (
    get_connection,
    get_company_data,
    build_tearsheet,
    TEARSHEETS_DIR,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
MIN_PL_YEARS = 3

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main."""
    TEARSHEETS_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()

    company_ids = sorted(r["id"] for r in conn.execute("SELECT id FROM companies"))
    logger.info("Generating tearsheets for %d companies", len(company_ids))

    generated = []
    skipped = []
    failed = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for company_id in company_ids:
            data = get_company_data(conn, company_id)
            pl_years = len(data["pl"])

            if pl_years < MIN_PL_YEARS:
                skipped.append(
                    {
                        "company_id": company_id,
                        "pl_years": pl_years,
                        "reason": f"< {MIN_PL_YEARS} years of P&L data",
                    }
                )
                logger.warning("Skipping %s: only %d P&L years", company_id, pl_years)
                continue

            output_path = TEARSHEETS_DIR / f"{company_id}_tearsheet.pdf"
            try:
                diag = build_tearsheet(conn, company_id, output_path, tmp_dir)
                generated.append(diag)
            except Exception as e:
                failed.append({"company_id": company_id, "error": str(e)})
                logger.error("FAILED %s: %s", company_id, e)

    conn.close()

    # --- Write skip log ---
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(
        OUTPUT_DIR / "skipped_tearsheets.csv", "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=["company_id", "pl_years", "reason"])
        writer.writeheader()
        writer.writerows(skipped)

    # --- Summary ---
    print("\n=== Day 34 Batch Tearsheet Summary ===")
    print(f"Total companies:      {len(company_ids)}")
    print(f"Generated:            {len(generated)}")
    print(f"Skipped (<{MIN_PL_YEARS}yr P&L): {len(skipped)}")
    print(f"Failed (unexpected):  {len(failed)}")

    if skipped:
        print("\nSkipped companies:")
        for s in skipped:
            print(f"  {s['company_id']}: {s['pl_years']} years")

    if failed:
        print("\nFAILED companies (investigate before accepting batch):")
        for f_ in failed:
            print(f"  {f_['company_id']}: {f_['error']}")

    if generated:
        sizes = [g["file_size_kb"] for g in generated]
        under_30kb = [g for g in generated if g["file_size_kb"] < 30]
        print(f"\nFile size range: {min(sizes):.1f} KB - {max(sizes):.1f} KB")
        print(f"Files under 30 KB (AC-17 concern): {len(under_30kb)}")
        if under_30kb:
            for g in under_30kb:
                print(
                    f"  {g['company_id']}: {g['file_size_kb']} KB, charts_skipped={g['charts_skipped']}"
                )

        all_skipped_charts = {}
        for g in generated:
            for chart in g["charts_skipped"]:
                all_skipped_charts[chart] = all_skipped_charts.get(chart, 0) + 1
        print("\nChart-skip frequency across generated tearsheets:")
        for chart, count in sorted(all_skipped_charts.items(), key=lambda x: -x[1]):
            print(f"  {chart}: skipped for {count} companies")


if __name__ == "__main__":
    main()
