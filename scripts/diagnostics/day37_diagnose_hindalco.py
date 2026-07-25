"""Day 37 diagnostic -- cross-check HINDALCO's OPM anomaly against an independent source field,
same method as Day 8's HAL equity cross-check (companies.xlsx.roce_percentage is computed
independently of profitandloss.xlsx, so it isn't vulnerable to the same field-labeling issue)."""
import pandas as pd
from src.analytics.portfolio_stats import get_connection

conn = get_connection()
df = pd.read_sql_query(
    "SELECT id, roce_percentage, roe_percentage FROM companies WHERE id IN ('HINDALCO','BHARTIARTL','HAL')",
    conn,
)
print(df.to_string(index=False))

# also check whether the sales-minus-opm_percentage-equals-operating_profit pattern is
# unique to HINDALCO or affects other Materials-sector companies too
pl = pd.read_sql_query(
    """SELECT company_id, year, sales, operating_profit, opm_percentage,
              (sales - opm_percentage) AS sales_minus_opmfield
       FROM profitandloss
       WHERE company_id IN (SELECT company_id FROM sectors WHERE broad_sector = 'Materials')
       AND year = '2024-03'""",
    conn,
)
pl["matches_operating_profit"] = (pl["sales_minus_opmfield"] - pl["operating_profit"]).abs() < 1
print("\nMaterials sector, 2024-03 -- does (sales - opm_percentage) match operating_profit?")
print(pl.to_string(index=False))
conn.close()