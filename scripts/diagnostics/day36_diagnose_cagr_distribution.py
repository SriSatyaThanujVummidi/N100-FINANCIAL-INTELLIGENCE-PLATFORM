import pandas as pd
from src.analytics.clustering import get_connection, load_revenue_cagr, load_fcf_cagr

conn = get_connection()
rev = load_revenue_cagr(conn)
fcf = load_fcf_cagr(conn)
conn.close()

print("Revenue CAGR 5yr -- sorted descending, non-null:")
print(rev.dropna().sort_values("revenue_cagr_5yr", ascending=False).to_string(index=False))

print("\nFCF CAGR 5yr -- sorted descending, non-null:")
print(fcf.dropna().sort_values("fcf_cagr_5yr", ascending=False).to_string(index=False))