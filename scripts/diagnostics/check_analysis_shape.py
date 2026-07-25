"""Checks the real shape of analysis.xlsx: is company_id truly 1:1,
or does each company have multiple distinct rows (which our current
1:1 dedup would be wrongly collapsing)?"""
import sys

sys.path.insert(0, "src")
from etl.loader import load_all_core

df = load_all_core()["analysis"]
print("Total rows:", len(df))
print("Unique company_id values:", df["company_id"].nunique())
print()
print("Row counts per company_id:")
print(df["company_id"].value_counts())
print()
print("Full contents:")
print(df.to_string())