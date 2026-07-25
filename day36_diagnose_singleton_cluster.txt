"""Day 36 diagnostic -- identify the 1-company cluster and verify its FCF CAGR is real."""
import pandas as pd
from src.analytics.clustering import get_connection

df = pd.read_csv("output/cluster_labels.csv")
counts = df["cluster_id"].value_counts()
singleton_cluster = counts[counts == 1].index[0]
company_id = df.loc[df["cluster_id"] == singleton_cluster, "company_id"].iloc[0]
print(f"Singleton cluster: {singleton_cluster}  ->  company: {company_id}")

conn = get_connection()
cf = pd.read_sql_query(
    "SELECT year, operating_activity, investing_activity FROM cashflow WHERE company_id = ? ORDER BY year",
    conn, params=(company_id,),
)
cf["fcf"] = cf["operating_activity"] + cf["investing_activity"]
print("\nFull FCF history:")
print(cf.to_string(index=False))

if len(cf) >= 6:
    start, end = cf["fcf"].iloc[-6], cf["fcf"].iloc[-1]
    print(f"\n5yr CAGR base (index -6): {start}   end (latest): {end}")
    if start and start > 0 and end and end > 0:
        cagr = ((end / start) ** (1 / 5) - 1) * 100
        print(f"Computed CAGR: {cagr:.2f}%  (matches cluster mean if this is the singleton)")

sectors = pd.read_sql_query(
    "SELECT broad_sector, sub_sector FROM sectors WHERE company_id = ?", conn, params=(company_id,)
)
print(f"\nSector: {sectors.to_dict('records')}")
conn.close()