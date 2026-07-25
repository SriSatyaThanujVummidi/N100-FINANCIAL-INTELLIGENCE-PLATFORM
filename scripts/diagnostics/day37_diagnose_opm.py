"""Day 37 diagnostic -- verify HINDALCO/BHARTIARTL's high OPM is real, not a data/join bug."""
import pandas as pd
from src.analytics.portfolio_stats import get_connection

conn = get_connection()
for ticker in ["HINDALCO", "BHARTIARTL"]:
    df = pd.read_sql_query(
        "SELECT year, sales, operating_profit, opm_percentage FROM profitandloss WHERE company_id = ? ORDER BY year DESC LIMIT 5",
        conn, params=(ticker,),
    )
    df["computed_opm"] = df["operating_profit"] / df["sales"] * 100
    print(f"\n{ticker}:")
    print(df.to_string(index=False))
conn.close()