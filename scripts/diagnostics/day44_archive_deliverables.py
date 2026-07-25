"""Day 44 -- archive all deliverables to output/final_deliverables/ for Day 45 sign-off."""
import shutil
from pathlib import Path

DEST = Path("output/final_deliverables")
DEST.mkdir(parents=True, exist_ok=True)

deliverables = [
    ("data/nifty100.db", "D-01_nifty100.db"),
    ("output/load_audit.csv", "D-02_load_audit.csv"),
    ("output/validation_failures.csv", "D-03_validation_failures.csv"),
    ("output/capital_allocation.csv", "D-06_capital_allocation.csv"),
    ("output/screener_output.xlsx", "D-07_screener_output.xlsx"),
    ("config/screener_config.yaml", "D-08_screener_config.yaml"),
    ("output/peer_comparison.xlsx", "D-09_peer_comparison.xlsx"),
    ("output/valuation_summary.xlsx", "D-12_valuation_summary.xlsx"),
    ("output/cashflow_intelligence.xlsx", "D-13_cashflow_intelligence.xlsx"),
    ("output/pros_cons_generated.csv", "D-14_pros_cons_generated.csv"),
    ("output/analysis_parsed.csv", "D-15_analysis_parsed.csv"),
    ("output/cluster_labels.csv", "D-19_cluster_labels.csv"),
    ("reports/pytest_report.html", "D-21_pytest_report.html"),
    ("docs/analyst_guide.pdf", "D-22_analyst_guide.pdf"),
    ("docs/openapi.json", "openapi.json"),
    ("output/perf_notes.md", "perf_notes.md"),
]

copied, missing = [], []
for src, dest_name in deliverables:
    src_path = Path(src)
    if src_path.exists():
        shutil.copy2(src_path, DEST / dest_name)
        copied.append(dest_name)
    else:
        missing.append(src)

for folder, label in [("reports/tearsheets", "D-16_tearsheets"), ("reports/sector", "D-17_sector_reports")]:
    src_folder = Path(folder)
    if src_folder.exists():
        dest_folder = DEST / label
        if dest_folder.exists():
            shutil.rmtree(dest_folder)
        shutil.copytree(src_folder, dest_folder)
        copied.append(f"{label}/ ({len(list(dest_folder.iterdir()))} files)")
    else:
        missing.append(folder)

print(f"Copied {len(copied)} deliverables:")
for c in copied:
    print(f"  {c}")
print(f"\nMissing/not found ({len(missing)}):")
for m in missing:
    print(f"  {m}")