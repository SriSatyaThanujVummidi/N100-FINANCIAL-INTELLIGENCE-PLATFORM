"""Day 43 -- Add indexes on company_id/year for query optimization on large tables."""
import sqlite3

conn = sqlite3.connect("data/nifty100.db")
tables_with_composite_key = [
    "profitandloss", "balancesheet", "cashflow", "financial_ratios", "market_cap",
]
tables_with_company_id_only = ["stock_prices", "documents", "prosandcons", "sectors"]

for table in tables_with_composite_key:
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_company_year ON {table}(company_id, year)")
    print(f"Index created: idx_{table}_company_year")

for table in tables_with_company_id_only:
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_company_id ON {table}(company_id)")
    print(f"Index created: idx_{table}_company_id")

conn.commit()

# Verify
print("\nAll indexes on the database:")
rows = conn.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'").fetchall()
for name, tbl in rows:
    print(f"  {name} on {tbl}")
conn.close()