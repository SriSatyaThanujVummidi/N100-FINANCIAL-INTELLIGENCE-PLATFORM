"""
Diagnostic: read data/raw/balancesheet.xlsx directly (no loader, no
normalisation) and print HAL's raw rows exactly as they appear in the
source file. This tells us whether the implausible HAL balance sheet
values originate in the source data itself, or get introduced somewhere
in the ETL pipeline.
"""

import pandas as pd

RAW_PATH = "data/raw/balancesheet.xlsx"

# Core files use header=1 per spec (row 0 is metadata, row 1 is real headers)
df = pd.read_excel(RAW_PATH, header=1)

print("Columns found:", list(df.columns))
print()

# Normalise just enough to filter — strip/upper, same as normalize_ticker()
df["company_id_clean"] = df["company_id"].astype(str).str.strip().str.upper()

hal_rows = df[df["company_id_clean"] == "HAL"]

print(f"--- Raw rows for HAL in {RAW_PATH} (n={len(hal_rows)}) ---")
cols_to_show = [c for c in [
    "company_id", "year", "equity_capital", "reserves",
    "borrowings", "total_assets", "total_liabilities"
] if c in hal_rows.columns]
print(hal_rows[cols_to_show].to_string(index=False))