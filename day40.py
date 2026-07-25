"""Day 40 diagnostic -- check how widespread the literal 'Null' string is in documents.annual_report_url."""
import sqlite3
conn = sqlite3.connect("data/nifty100.db")
rows = conn.execute(
    "SELECT COUNT(*) FROM documents WHERE annual_report_url = 'Null'"
).fetchone()
print(f"Rows with literal 'Null' string: {rows[0]}")
companies = conn.execute(
    "SELECT DISTINCT company_id FROM documents WHERE annual_report_url = 'Null'"
).fetchall()
print(f"Affected companies: {[c[0] for c in companies]}")
conn.close()