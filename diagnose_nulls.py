"""Day 5 diagnostic — checks every column the schema marks NOT NULL for
missing values in the REAL source files, before we re-run the full load.
Run this once; paste the output back."""
import sys
from pathlib import Path

sys.path.insert(0, "src")
from etl.loader import load_all_core, load_all_supporting

# (table_key_in_loader, column_name) pairs that schema.sql marks NOT NULL,
# excluding company_id/year which normaliser already handles separately.
NOT_NULL_CHECKS = {
    "companies": ["company_name", "face_value"],
    "profitandloss": ["sales", "expenses", "operating_profit", "opm_percentage"],
    "balancesheet": ["equity_capital", "total_liabilities", "total_assets"],
    "documents": ["Year"],  # becomes report_year
    "sectors": ["broad_sector", "sub_sector"],
}

core = load_all_core()
supporting = load_all_supporting()
all_files = {**core, **supporting}

print(f"{'table':16s} {'column':24s} {'rows_missing':>12s}  example_ids")
print("-" * 80)
any_found = False
for table, cols in NOT_NULL_CHECKS.items():
    df = all_files[table]
    id_col = "id" if table == "companies" else "company_id"
    for col in cols:
        if col not in df.columns:
            print(f"{table:16s} {col:24s} {'COLUMN MISSING':>12s}")
            continue
        missing = df[df[col].isna()]
        if len(missing):
            any_found = True
            examples = list(missing[id_col].head(5))
            print(f"{table:16s} {col:24s} {len(missing):12d}  {examples}")

if not any_found:
    print("\nNo NOT NULL gaps found in any checked column. TVSMOTOR/face_value was the only one.")
else:
    print("\n^ These are the gaps we need to decide how to handle before re-running full_load.py.")