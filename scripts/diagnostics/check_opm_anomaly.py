"""Checks the RAW profitandloss.xlsx row for ICICIBANK 2019-03 to confirm
whether the wildly out-of-range opm_percentage is a genuine source-data
characteristic or a column-shift bug in our loader."""
import sys

sys.path.insert(0, "src")
from etl.loader import load_core_file

df = load_core_file("data/raw/profitandloss.xlsx")
print("All columns:", list(df.columns))

print("\n--- Raw ICICIBANK rows (all columns, all years) ---")
icici = df[df["company_id"].astype(str).str.strip().str.upper() == "ICICIBANK"]
print(icici.to_string())

print("\n--- For comparison, a normal industrial company (TCS) ---")
tcs = df[df["company_id"].astype(str).str.strip().str.upper() == "TCS"]
print(tcs[["company_id", "year", "sales", "operating_profit", "opm_percentage"]].head(3).to_string())