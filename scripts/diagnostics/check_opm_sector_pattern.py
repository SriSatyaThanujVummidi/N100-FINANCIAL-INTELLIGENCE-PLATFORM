"""Confirms whether the OPM source-vs-computed divergence (Query 7) is
concentrated in specific sectors, rather than being random/scattered."""
import sqlite3

conn = sqlite3.connect("data/nifty100.db")

query = """
SELECT s.broad_sector, COUNT(DISTINCT p.company_id) AS affected_companies,
       COUNT(*) AS affected_rows
FROM profitandloss p
JOIN sectors s ON p.company_id = s.company_id
WHERE p.sales != 0
  AND p.opm_percentage IS NOT NULL
  AND p.operating_profit IS NOT NULL
  AND ABS(p.opm_percentage - (p.operating_profit * 100.0 / p.sales)) >= 1.0
GROUP BY s.broad_sector
ORDER BY affected_rows DESC;
"""
print("--- Sector breakdown of OPM-divergence rows ---")
for row in conn.execute(query):
    print(row)

query2 = """
SELECT DISTINCT p.company_id, s.broad_sector
FROM profitandloss p
JOIN sectors s ON p.company_id = s.company_id
WHERE p.sales != 0
  AND p.opm_percentage IS NOT NULL
  AND p.operating_profit IS NOT NULL
  AND ABS(p.opm_percentage - (p.operating_profit * 100.0 / p.sales)) >= 1.0
ORDER BY s.broad_sector, p.company_id;
"""
print("\n--- All distinct affected companies ---")
for row in conn.execute(query2):
    print(row)

conn.close()