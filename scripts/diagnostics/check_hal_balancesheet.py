"""Investigates why HAL's balancesheet history starts in 2016 while its
P&L starts in 2013 — a 3-year gap. Checks the RAW file directly."""
import sys

sys.path.insert(0, "src")
from etl.loader import load_core_file
from etl.normaliser import normalize_ticker

df = load_core_file("data/raw/balancesheet.xlsx")
print("Raw balancesheet.xlsx total rows:", len(df))

print("\n--- Rows where company_id exactly equals 'HAL' (after strip+upper) ---")
exact = df[df["company_id"].astype(str).str.strip().str.upper() == "HAL"]
print(f"Row count: {len(exact)}")
if len(exact):
    print(exact[["id", "company_id", "year"]].to_string())

print("\n--- Rows where company_id contains 'HAL' (case-insensitive, in case of a variant spelling) ---")
mask = df["company_id"].astype(str).str.upper().str.contains("HAL", na=False)
print(sorted(df[mask]["company_id"].astype(str).str.strip().str.upper().unique()))

print("\n--- Normalized ticker check (using the real normalize_ticker function) ---")
normalized = []
for v in df["company_id"]:
    try:
        normalized.append(normalize_ticker(v))
    except ValueError:
        normalized.append(None)
count_hal = sum(1 for n in normalized if n == "HAL")
print(f"Rows that normalize to 'HAL': {count_hal}")

# Cross-check against the P&L file: does HAL have 2013-2015 rows there,
# confirming the company definitely existed/reported in those years?
print("\n--- HAL rows in profitandloss.xlsx for comparison ---")
pl = load_core_file("data/raw/profitandloss.xlsx")
pl_hal = pl[pl["company_id"].astype(str).str.strip().str.upper() == "HAL"]
print(f"P&L rows for HAL: {len(pl_hal)}")
if len(pl_hal):
    print(pl_hal[["id", "company_id", "year"]].to_string())