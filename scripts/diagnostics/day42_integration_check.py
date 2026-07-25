"""Day 42 integration check -- compares Streamlit's screener data path (direct DB query, same
logic as src/screener/engine.py) against the API's /screener endpoint for the same preset,
to confirm they return the same company set. Requires the API server running on port 8000."""
import requests
import sqlite3

conn = sqlite3.connect("data/nifty100.db")

# Quality Compounder preset thresholds, per screener_config.yaml (Day 15/16)
query = """
    SELECT fr.company_id FROM financial_ratios fr
    INNER JOIN (SELECT company_id, MAX(year) AS y FROM financial_ratios GROUP BY company_id) latest
      ON fr.company_id = latest.company_id AND fr.year = latest.y
    WHERE fr.return_on_equity_pct >= 15 AND ABS(fr.return_on_equity_pct) <= 500
"""
dashboard_side = {row[0] for row in conn.execute(query).fetchall()}
conn.close()

resp = requests.get("http://localhost:8000/api/v1/screener", params={"min_roe": 15})
api_side = {c["company_id"] for c in resp.json()["results"]}

print(f"Dashboard-path ROE>=15 count: {len(dashboard_side)}")
print(f"API /screener min_roe=15 count: {len(api_side)}")
print(f"Match: {dashboard_side == api_side}")
if dashboard_side != api_side:
    print(f"Only in dashboard: {dashboard_side - api_side}")
    print(f"Only in API: {api_side - dashboard_side}")