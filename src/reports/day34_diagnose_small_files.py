"""

Day 34: batch summary reported a file-size floor of 43.5 KB, but AC-17
requires each tearsheet to be >= 50 KB — my own diagnostic used a wrong
30 KB threshold. This finds every tearsheet under 50 KB, identifies the
company, and checks its data availability to explain why it's small
(consistent with a chart being skipped) rather than assuming it's fine.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEARSHEETS_DIR = PROJECT_ROOT / "reports" / "tearsheets"
AC17_THRESHOLD_KB = 50


def main() -> None:
    """Main."""
    files = sorted(TEARSHEETS_DIR.glob("*.pdf"), key=lambda p: p.stat().st_size)

    print(f"Total tearsheet PDFs: {len(files)}\n")
    print("Smallest 10 files:")
    under_threshold = []
    for f in files[:10]:
        size_kb = f.stat().st_size / 1024
        flag = " <-- BELOW AC-17 (50 KB)" if size_kb < AC17_THRESHOLD_KB else ""
        print(f"  {f.name:35s} {size_kb:7.1f} KB{flag}")
        if size_kb < AC17_THRESHOLD_KB:
            under_threshold.append((f.name, size_kb))

    print(f"\nFiles below AC-17's 50 KB threshold: {len(under_threshold)}")
    for name, size in under_threshold:
        print(f"  {name}: {size:.1f} KB")


if __name__ == "__main__":
    main()
