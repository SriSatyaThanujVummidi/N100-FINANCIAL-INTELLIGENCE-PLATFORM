"""Day 37 diagnostic -- find the real OPM distribution to pick a defensible sector-agnostic
bound, same discipline as Day 36's FCF CAGR fix (find the natural gap, don't guess)."""
import pandas as pd
from src.analytics.portfolio_stats import get_connection, resolve_kpi_columns, load_latest_kpis

conn = get_connection()
kpi_map = resolve_kpi_columns(conn)
df = load_latest_kpis(conn, kpi_map)
conn.close()

print("\nOperating Profit Margin % -- sorted descending, by sector:")
cols = ["company_id", "broad_sector", "Operating Profit Margin %"]
print(df[cols].dropna().sort_values("Operating Profit Margin %", ascending=False).to_string(index=False))