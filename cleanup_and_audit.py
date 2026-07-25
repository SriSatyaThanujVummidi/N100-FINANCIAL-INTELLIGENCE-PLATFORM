"""
cleanup_and_audit.py — Nifty 100 Financial Intelligence Platform
Audits the real project tree against spec Section 19's expected directory
layout, flags junk/duplicate/malformed files, and archives loose diagnostic
scripts out of the project root into scripts/diagnostics/ (kept, not deleted
— PROGRESS.md references many of them by name as evidence, so they stay
available, just out of the way).

DRY RUN BY DEFAULT — prints the full plan and writes it to
output/cleanup_plan.csv. Nothing is moved or deleted until you re-run with
--apply.

USAGE (PowerShell, from project root):
    python cleanup_and_audit.py              # dry run — report only
    python cleanup_and_audit.py --apply       # actually move/delete

Categories:
    DELETE       — confirmed junk: malformed filenames from botched commands,
                   exact duplicates, stray one-off test artifacts
    ARCHIVE      — legitimate diagnostic/day-scripts that don't belong loose
                   at project root per spec Section 19 — moved to
                   scripts/diagnostics/, not deleted
    FOLDER_DELETE— preview/test-only folders fully superseded by a later
                   full-batch run of the same content
    RENAME       — meaningful file with a malformed name, corrected in place
    REVIEW       — flagged for a human look, no automatic action taken
"""

import argparse
import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(sys.argv[-1]) if len(sys.argv) > 1 and not sys.argv[-1].startswith("-") else Path.cwd()


# --- Explicit, hand-verified actions based on the actual uploaded tree ---
# (path is relative to ROOT)
EXPLICIT_ACTIONS = [
    # --- Confirmed junk: malformed filenames from botched shell commands ---
    ("python day36_diagnose_cagr_distribution.py", "DELETE",
     "Malformed filename — looks like 'python day36_diagnose_cagr_distribution.py' "
     "was accidentally saved as a filename instead of being run as a command. "
     "The real script (day36_diagnose_cagr_distribution.py) already exists separately."),

    ("run exploratory queries.py", "DELETE",
     "Duplicate of run_exploratory_queries.py with a space in the filename — "
     "almost certainly an accidental re-save. Keep the underscore version."),

    ("tcs_test.pdf", "DELETE",
     "Stray root-level test artifact from Day 33 tearsheet development — "
     "superseded by reports/tearsheets_test/TCS_tearsheet.pdf and the real "
     "batch output reports/tearsheets/TCS_tearsheet.pdf."),

    # --- Malformed but meaningful — rename, don't delete ---
    ("# Sprint 5 Retrospective — Intelligence,.md", "RENAME:sprint5_retro.md",
     "Filename looks like a doc title got saved directly as a filename "
     "(truncated, with a leading '#' and trailing comma). Content is very "
     "likely the missing Sprint 5 retro referenced nowhere else in the tree — "
     "renaming preserves it instead of losing it."),

    ("notebooks/Exploratory queries.sql", "RENAME:notebooks/exploratory_queries.sql",
     "D-04's tracker path is notebooks/exploratory_queries.sql (lowercase, "
     "underscore) — this file has a capitalized name with a space. Rename to "
     "match the tracker rather than deleting; output/exploratory_queries.sql "
     "remains the actively-maintained copy per Day 45's note."),

    # --- Folders fully superseded by a later full-batch run ---
    ("reports/radar_charts_preview", "FOLDER_DELETE",
     "Day 19's 4-ticker visual preview (TCS/HDFCLIFE/HAL/PIDILITIND) before "
     "committing to the full 92-chart batch. Superseded by reports/radar_charts/ "
     "(92/92 confirmed present). Safe to remove."),

    ("reports/tearsheets_test", "FOLDER_DELETE",
     "Day 33's 5-company test batch (TCS/HDFCBANK/RELIANCE/SUNPHARMA/TATASTEEL) "
     "before the full run. Superseded by reports/tearsheets/ (91/92 confirmed "
     "present). Safe to remove."),

    # --- Flagged for review, not auto-actioned ---
    ("day36_diagnose_singleton_cluster.txt", "REVIEW",
     "Same base name as day36_diagnose_singleton_cluster.py — likely that "
     "script's captured console output. Harmless to keep, but confirm it's "
     "not an accidental duplicate before archiving with the script."),

    ("day40.py", "REVIEW",
     "Generic name, unclear purpose from filename alone — check contents "
     "before archiving; may be a superseded early draft of a Day 40 endpoint "
     "test rather than a kept diagnostic."),
]

# --- Pattern-based rule: any loose .py at ROOT matching these prefixes is a
# diagnostic/one-off script per spec Section 19 (root should only hold
# requirements.txt, README.md, .env(.template), pyproject.toml, and the
# three tool scripts below) — archive, don't delete, since PROGRESS.md cites
# many of these by name as evidence of real bugs found and fixed. ---
DIAGNOSTIC_PREFIXES = ("check_", "day", "scratch_", "run_")
KEEP_AT_ROOT = {
    "requirements.txt", "README.md", "pyproject.toml", ".env", ".env.template",
    "setup_structure.py", "verify_deliverables.py", "list_project_structure.py",
    "cleanup_and_audit.py", "conftest.py",  # conftest.py must stay at root for pytest discovery
}


def find_pattern_archive_candidates(root: Path):
    """Any loose .py at project root matching diagnostic-script naming, not
    already covered by EXPLICIT_ACTIONS and not in the keep-list."""
    explicit_paths = {a[0] for a in EXPLICIT_ACTIONS}
    candidates = []
    for f in root.iterdir():
        if not f.is_file() or f.suffix != ".py":
            continue
        if f.name in KEEP_AT_ROOT or f.name in explicit_paths:
            continue
        if f.name.startswith(DIAGNOSTIC_PREFIXES):
            candidates.append(f.name)
    return candidates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually perform the moves/deletes")
    parser.add_argument("root", nargs="?", default=str(ROOT))
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"ERROR: root path does not exist: {root}")
        sys.exit(1)

    plan = []  # (path, action, reason)

    for rel_path, action, reason in EXPLICIT_ACTIONS:
        p = root / rel_path
        if p.exists():
            plan.append((rel_path, action, reason))
        else:
            plan.append((rel_path, "SKIP (not found)", "Already absent — no action needed"))

    for name in find_pattern_archive_candidates(root):
        plan.append((name, "ARCHIVE", "Diagnostic/day-script at project root — spec Section 19 "
                                       "doesn't list loose diagnostic scripts at root; moved to "
                                       "scripts/diagnostics/ for a clean deliverable tree, kept "
                                       "(not deleted) since PROGRESS.md cites it as real evidence."))

    # --- Print report ---
    print(f"Cleanup plan for: {root}")
    print(f"Mode: {'APPLY (files will be moved/deleted)' if args.apply else 'DRY RUN (no changes made)'}\n")
    print(f"{'Action':<14}{'Path':<55}Reason")
    print("-" * 130)
    for path, action, reason in plan:
        short_reason = reason if len(reason) < 60 else reason[:57] + "..."
        print(f"{action:<14}{path:<55}{short_reason}")

    out_dir = root / "output"
    out_dir.mkdir(exist_ok=True)
    csv_path = out_dir / "cleanup_plan.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["path", "action", "reason"])
        writer.writerows(plan)
    print(f"\nFull plan saved to: {csv_path}")

    if not args.apply:
        print("\nDRY RUN — nothing changed. Re-run with --apply to execute this plan.")
        return

    # --- Execute ---
    archive_dir = root / "scripts" / "diagnostics"
    archive_dir.mkdir(parents=True, exist_ok=True)

    for path, action, reason in plan:
        p = root / path
        if action.startswith("SKIP"):
            continue
        if action == "DELETE":
            p.unlink()
            print(f"Deleted: {path}")
        elif action == "FOLDER_DELETE":
            shutil.rmtree(p)
            print(f"Deleted folder: {path}")
        elif action.startswith("RENAME:"):
            new_path = root / action.split(":", 1)[1]
            new_path.parent.mkdir(parents=True, exist_ok=True)
            p.rename(new_path)
            print(f"Renamed: {path} -> {action.split(':', 1)[1]}")
        elif action == "ARCHIVE":
            dest = archive_dir / p.name
            shutil.move(str(p), str(dest))
            print(f"Archived: {path} -> scripts/diagnostics/{p.name}")
        elif action == "REVIEW":
            print(f"Left for manual review (no action): {path}")

    print(f"\nDone. Diagnostic scripts archived under: {archive_dir}")


if __name__ == "__main__":
    main()