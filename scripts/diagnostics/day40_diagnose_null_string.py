"""Day 40 diagnostic -- is the literal 'Null' string concentrated in early years (plausible:
older annual reports genuinely not digitized) or scattered (more likely a load/source defect)?"""
import sqlite3
conn = sqlite3.connect("data/nifty100.db")

print("Literal 'Null' rows by year:")
rows = conn.execute(
    "SELECT report_year, COUNT(*) as n FROM documents WHERE annual_report_url = 'Null' GROUP BY report_year ORDER BY report_year"
).fetchall()
for year, n in rows:
    print(f"  {year}: {n}")

print("\nFor comparison -- TOTAL rows per year (all companies, valid + 'Null'):")
rows = conn.execute(
    "SELECT report_year, COUNT(*) as n FROM documents GROUP BY report_year ORDER BY report_year"
).fetchall()
for year, n in rows:
    print(f"  {year}: {n}")

# Check: does this affect real sqlite NULL too, or only the literal string?
none_count = conn.execute("SELECT COUNT(*) FROM documents WHERE annual_report_url IS NULL").fetchone()[0]
print(f"\nRows with a genuine SQL NULL (not the string): {none_count}")

conn.close()