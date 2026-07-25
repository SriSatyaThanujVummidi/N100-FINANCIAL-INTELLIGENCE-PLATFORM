import sys
sys.path.insert(0, "src")
from etl.loader import load_all_core
import pandas as pd

core = load_all_core()
cf = core["cashflow"]

print("=== Raw company_id variants that normalize to TCS ===")
tcs_like = cf[cf["company_id"].astype(str).str.strip().str.upper() == "TCS"]
print(tcs_like[["id", "company_id", "year"]].to_string(index=False))

print(f"\nTotal rows: {len(tcs_like)}  |  Unique raw company_id values: {tcs_like['company_id'].unique().tolist()}")
print(f"Unique raw year values: {sorted(tcs_like['year'].astype(str).unique().tolist())}")