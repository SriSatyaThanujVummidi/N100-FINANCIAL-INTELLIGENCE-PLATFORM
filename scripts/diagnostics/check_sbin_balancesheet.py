"""Investigates why SBIN has 0 rows in the loaded balancesheet table,
despite having full P&L/CF history. Checks the RAW file directly."""
import sys

sys.path.insert(0, "src")
from etl.loader import load_core_file
from etl.normaliser import normalize_ticker

df = load_core_file("data/raw/balancesheet.xlsx")
print("Raw balancesheet.xlsx total rows:", len(df))
print("Columns:", list(df.columns))

print("\n--- Rows where company_id contains 'SBI' (case-insensitive) ---")
mask = df["company_id"].astype(str).str.upper().str.contains("SBI", na=False)
candidates = df[mask]
if len(candidates):
    print(candidates.to_string())
else:
    print("No rows found containing 'SBI' anywhere in company_id.")

print("\n--- Exact match check ---")
exact = df[df["company_id"].astype(str).str.strip().str.upper() == "SBIN"]
print(f"Rows with company_id exactly 'SBIN' (after strip+upper): {len(exact)}")

print("\n--- Normalized ticker check (using the real normalize_ticker function) ---")
normalized = []
for v in df["company_id"]:
    try:
        normalized.append(normalize_ticker(v))
    except ValueError:
        normalized.append(None)
count_sbin = sum(1 for n in normalized if n == "SBIN")
print(f"Rows that normalize to 'SBIN': {count_sbin}")

# Show all unique tickers that look bank-related, in case SBIN is spelled
# completely differently (e.g. 'STATEBANK', 'SBI')
print("\n--- All unique company_id values containing 'BANK' or 'STATE' (sanity check) ---")
mask2 = df["company_id"].astype(str).str.upper().str.contains("BANK|STATE", na=False)
print(sorted(df[mask2]["company_id"].astype(str).str.strip().str.upper().unique()))