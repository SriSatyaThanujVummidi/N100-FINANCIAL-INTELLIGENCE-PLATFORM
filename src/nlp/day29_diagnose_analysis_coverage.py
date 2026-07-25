"""

One-off diagnostic: compares raw analysis.xlsx company coverage against
what actually landed in the `analysis` SQLite table after ETL, to explain
why parser.py found only 4 companies instead of Sprint 1 Day 5's
documented "~8 companies (WIPRO excluded)" estimate.
"""

import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "analysis.xlsx"
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"


def main() -> None:
    """Main."""
    raw_df = pd.read_excel(RAW_PATH, header=1)
    raw_df.columns = [str(c).strip() for c in raw_df.columns]

    if "company_id" not in raw_df.columns:
        print("Raw columns found:", list(raw_df.columns))
        raise SystemExit("company_id column not found — check header row assumption")

    raw_df["company_id_norm"] = raw_df["company_id"].astype(str).str.strip().str.upper()
    raw_tickers = sorted(raw_df["company_id_norm"].unique())
    print(
        f"Raw analysis.xlsx: {len(raw_df)} rows, {len(raw_tickers)} distinct company_id -> {raw_tickers}"
    )

    conn = sqlite3.connect(DB_PATH)
    companies_in_db = {r[0] for r in conn.execute("SELECT id FROM companies")}
    loaded_tickers = sorted(
        {r[0] for r in conn.execute("SELECT DISTINCT company_id FROM analysis")}
    )
    loaded_rowcount = conn.execute("SELECT COUNT(*) FROM analysis").fetchone()[0]
    print(
        f"Loaded analysis table: {loaded_rowcount} rows, {len(loaded_tickers)} distinct company_id -> {loaded_tickers}"
    )

    missing = [t for t in raw_tickers if t not in loaded_tickers]
    print(f"\nIn raw file but NOT in loaded 'analysis' table: {missing}")
    for t in missing:
        in_companies = t in companies_in_db
        print(f"  {t}: exists in companies table? {in_companies}")

    conn.close()


if __name__ == "__main__":
    main()
