"""Day 38 diagnostic -- confirm which nifty100.db file the API is actually reading,
and compare its row counts against the known-correct Sprint 1 values."""
import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "data/nifty100.db")
print(f"DB_PATH env var: {os.environ.get('DB_PATH', '(not set, using default)')}")
print(f"Resolved absolute path: {os.path.abspath(DB_PATH)}")
print(f"File exists: {os.path.exists(DB_PATH)}")
if os.path.exists(DB_PATH):
    print(f"File size: {os.path.getsize(DB_PATH):,} bytes")
    print(f"Last modified: {os.path.getmtime(DB_PATH)}")

conn = sqlite3.connect(DB_PATH)
known_correct = {
    "companies": 92, "profitandloss": 1276, "balancesheet": 1312,
    "cashflow": 1187, "documents": 1585, "stock_prices": 5520,
    "financial_ratios": 1073, "market_cap": 552,
}
print("\nTable            Actual   Expected   Match")
for table, expected in known_correct.items():
    actual = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    match = "OK" if actual == expected else "MISMATCH"
    print(f"{table:16} {actual:>7}  {expected:>8}   {match}")
conn.close()

# Also check for any OTHER nifty100.db files lurking on disk that could be getting picked up
print("\nSearching for any other nifty100.db files under the project root:")
for root, dirs, files in os.walk("."):
    if ".venv" in root or ".git" in root:
        continue
    for f in files:
        if f == "nifty100.db":
            full = os.path.join(root, f)
            print(f"  {full}  ({os.path.getsize(full):,} bytes)")