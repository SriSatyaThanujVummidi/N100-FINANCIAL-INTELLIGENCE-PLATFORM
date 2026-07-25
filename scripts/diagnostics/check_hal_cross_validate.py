"""
Diagnostic: cross-validate HAL's balance-sheet-implied ROE against the
independent, pre-computed roe_percentage/roce_percentage/book_value fields
in companies.xlsx, to determine whether HAL's balancesheet.xlsx block is
at the wrong scale (e.g. Lakhs vs Crore) relative to the rest of the dataset.
"""

import pandas as pd

companies_df = pd.read_excel("data/raw/companies.xlsx", header=1)
companies_df["id_clean"] = companies_df["id"].astype(str).str.strip().str.upper()
hal_company = companies_df[companies_df["id_clean"] == "HAL"]

print("--- companies.xlsx row for HAL (independent source) ---")
cols = [c for c in ["id", "face_value", "book_value", "roce_percentage", "roe_percentage"] if c in hal_company.columns]
print(hal_company[cols].to_string(index=False))

pl_df = pd.read_excel("data/raw/profitandloss.xlsx", header=1)
pl_df["company_id_clean"] = pl_df["company_id"].astype(str).str.strip().str.upper()
hal_pl = pl_df[pl_df["company_id_clean"] == "HAL"][["year", "sales", "net_profit"]]

print("\n--- profitandloss.xlsx rows for HAL ---")
print(hal_pl.to_string(index=False))

print("\n--- Implied equity from source roe_percentage (most recent net_profit / roe_pct) ---")
if not hal_company.empty and "roe_percentage" in hal_company.columns:
    roe_pct = hal_company["roe_percentage"].iloc[0]
    latest_net_profit = hal_pl.sort_values("year").iloc[-1]["net_profit"]
    if roe_pct and roe_pct != 0:
        implied_equity = latest_net_profit / (roe_pct / 100)
        print(f"roe_percentage={roe_pct}, latest net_profit={latest_net_profit}")
        print(f"Implied equity+reserves ≈ {implied_equity:.1f} Cr")
        print("Compare this to balancesheet.xlsx's FY24 equity+reserves = 199 Cr")