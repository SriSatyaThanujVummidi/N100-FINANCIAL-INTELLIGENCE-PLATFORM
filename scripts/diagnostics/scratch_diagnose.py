import sys
sys.path.insert(0, "src")
from etl.loader import load_all_core
from etl.normaliser import normalize_ticker
import pandas as pd

core = load_all_core()

print("=== Raw duplicate check (before normalization) ===")
for table in ["profitandloss", "balancesheet", "cashflow"]:
    df = core[table]
    dupes = df.groupby(["company_id", "year"]).size()
    dupes = dupes[dupes > 1]
    if len(dupes):
        companies = sorted(dupes.index.get_level_values("company_id").unique().tolist())
        print(f"{table}: {len(dupes)} dup (company_id, year) pairs -> {companies}")
    else:
        print(f"{table}: no raw duplicates")

print("\n=== ATGL vs AGTL check ===")
companies_df = core["companies"]
ids_upper = companies_df["id"].astype(str).str.strip().str.upper()
print("ATGL present in companies.xlsx:", "ATGL" in ids_upper.values)
for table in ["profitandloss", "balancesheet", "cashflow"]:
    vals = core[table]["company_id"].astype(str).str.strip().str.upper()
    print(f"{table}: ATGL rows={(vals == 'ATGL').sum()}, AGTL rows={(vals == 'AGTL').sum()}")

print("\n=== Companies in P&L/BS/CF but missing from companies.xlsx ===")
valid_ids = set(ids_upper.dropna())
for table in ["profitandloss", "balancesheet", "cashflow"]:
    ids = set(core[table]["company_id"].dropna().astype(str).str.strip().str.upper())
    missing = sorted(ids - valid_ids)
    print(f"{table}: {len(missing)} missing -> {missing}")