"""Checks whether companies.xlsx has a genuine duplicate ticker (same id
appearing twice) AFTER ticker normalization — separate from any stale-DB
issue. Run this and paste the output."""
import sys
import collections

sys.path.insert(0, "src")
from etl.loader import load_all_core
from etl.normaliser import normalize_ticker

df = load_all_core()["companies"]
print("Raw row count in companies.xlsx:", len(df))

normalized_ids = []
for v in df["id"]:
    try:
        normalized_ids.append(normalize_ticker(v))
    except ValueError:
        normalized_ids.append(None)

counts = collections.Counter(normalized_ids)
dupes = {k: v for k, v in counts.items() if v > 1 and k is not None}

print("Unique normalized ids:", len(set(normalized_ids) - {None}))
print("Rows that failed ticker normalization (None):", normalized_ids.count(None))
print("Duplicate ids after normalization:", dupes if dupes else "none")

if dupes:
    print("\nFull rows for each duplicated id:")
    df_copy = df.copy()
    df_copy["normalized_id"] = normalized_ids
    for dup_id in dupes:
        print(f"\n--- {dup_id} ---")
        print(df_copy[df_copy["normalized_id"] == dup_id].to_string())