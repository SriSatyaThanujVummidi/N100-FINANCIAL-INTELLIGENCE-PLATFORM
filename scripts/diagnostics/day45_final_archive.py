"""Day 45 -- final archive pass, adds the deliverables not covered by Day 44's script."""
import shutil
from pathlib import Path

DEST = Path("output/final_deliverables")
DEST.mkdir(parents=True, exist_ok=True)

additional = [
    ("output/acceptance_gate_results.csv", "D-XX_acceptance_gate_results.csv"),
    ("docs/acceptance_checklist.pdf", "D-23_acceptance_checklist.pdf"),
    ("reports/elbow_plot.png", "elbow_plot.png"),
    ("reports/correlation_heatmap.png", "correlation_heatmap.png"),
    ("output/outlier_report.csv", "outlier_report.csv"),
    ("output/portfolio_stats.csv", "portfolio_stats.csv"),
    ("output/exploratory_queries.sql", "D-04_exploratory_queries.sql"),
]

copied, missing = [], []
for src, dest_name in additional:
    p = Path(src)
    if p.exists():
        shutil.copy2(p, DEST / dest_name)
        copied.append(dest_name)
    else:
        missing.append(src)

for folder, label in [("reports/radar_charts", "D-10_radar_charts"), ("reports/portfolio", "D-18_portfolio_summary")]:
    p = Path(folder)
    if p.exists() and any(p.iterdir()):
        dest_folder = DEST / label
        if dest_folder.exists():
            shutil.rmtree(dest_folder)
        shutil.copytree(p, dest_folder)
        copied.append(f"{label}/ ({len(list(dest_folder.iterdir()))} files)")
    else:
        missing.append(folder)

print(f"Copied {len(copied)}:")
for c in copied:
    print(f"  {c}")
print(f"\nMissing ({len(missing)}):")
for m in missing:
    print(f"  {m}")

print(f"\nFinal contents of output/final_deliverables/:")
for item in sorted(DEST.iterdir()):
    print(f"  {item.name}")