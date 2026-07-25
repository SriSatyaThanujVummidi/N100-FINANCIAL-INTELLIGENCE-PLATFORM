"""
Day 12 — Populate the financial_ratios table in nifty100.db.

Runs the full Sprint 2 ratio engine (Days 8-11 + Day 12's composite
quality score) for every company-year row in profitandloss, joining in
balancesheet/cashflow/sectors/companies data where available, and writes
the result into the financial_ratios table.

Re-runnable: deletes all existing financial_ratios rows before inserting,
so running this twice in a row produces the same result, not duplicates
(same idempotency convention as full_load.py from Sprint 1).
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from analytics.ratios import (
    compute_profitability_ratios,
    compute_leverage_efficiency_ratios,
    book_value_per_share,
)
from analytics.cashflow_kpis import compute_cashflow_kpis_single_year, capex_cr
from analytics.cagr import compute_growth_metrics
from analytics.scoring import compute_quality_scores_for_year

DB_PATH = "data/nifty100.db"

# Columns this script owns. return_on_capital_employed_pct is included
# even though it's NOT in the spec's literal Day 12 column list -- it's
# needed internally for the composite score, and Day 13 explicitly needs
# it for the ROCE cross-check, so it's persisted here rather than
# recomputed from scratch later.
REQUIRED_COLUMNS = {
    "net_profit_margin_pct": "REAL",
    "operating_profit_margin_pct": "REAL",
    "return_on_equity_pct": "REAL",
    "return_on_capital_employed_pct": "REAL",  # added beyond spec list -- see above
    "return_on_assets_pct": "REAL",  # also computed by Day 8 but was missing from this list until Day 13
    "debt_to_equity": "REAL",
    "interest_coverage": "REAL",
    "asset_turnover": "REAL",
    "free_cash_flow_cr": "REAL",
    "capex_cr": "REAL",
    "earnings_per_share": "REAL",
    "book_value_per_share": "REAL",
    "dividend_payout_ratio_pct": "REAL",
    "total_debt_cr": "REAL",
    "cash_from_operations_cr": "REAL",
    "revenue_cagr_5yr": "REAL",
    "pat_cagr_5yr": "REAL",
    "eps_cagr_5yr": "REAL",
    "composite_quality_score": "REAL",
}


def ensure_columns(conn: sqlite3.Connection) -> None:
    """Add any REQUIRED_COLUMNS not already present in financial_ratios.
    SQLite has no 'ADD COLUMN IF NOT EXISTS', so check PRAGMA table_info
    first and only add what's missing."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(financial_ratios)")}
    for column, sqltype in REQUIRED_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE financial_ratios ADD COLUMN {column} {sqltype}")


def compute_all_rows(conn: sqlite3.Connection) -> list[dict]:
    """Run the full ratio engine for every (company_id, year) row found
    in profitandloss, joining in balancesheet/cashflow/sectors/companies
    data where available."""
    conn.row_factory = sqlite3.Row

    face_value_by_company = {
        r["id"]: r["face_value"]
        for r in conn.execute("SELECT id, face_value FROM companies")
    }
    sector_by_company = {
        r["company_id"]: r["broad_sector"]
        for r in conn.execute("SELECT company_id, broad_sector FROM sectors")
    }

    pl_rows = conn.execute("""
        SELECT company_id, year, sales, net_profit, operating_profit,
               opm_percentage, depreciation, eps, dividend_payout,
               other_income, interest
        FROM profitandloss ORDER BY company_id, year
    """).fetchall()

    bs_by_key = {(r["company_id"], r["year"]): r for r in conn.execute("""
            SELECT company_id, year, equity_capital, reserves, borrowings,
                   total_assets, investments
            FROM balancesheet
        """)}
    cf_by_key = {(r["company_id"], r["year"]): r for r in conn.execute("""
            SELECT company_id, year, operating_activity, investing_activity,
                   financing_activity
            FROM cashflow
        """)}

    pl_by_company: dict[str, list] = {}
    for r in pl_rows:
        pl_by_company.setdefault(r["company_id"], []).append(r)

    computed_rows: list[dict] = []

    for company_id, rows in pl_by_company.items():
        rows_sorted = sorted(rows, key=lambda r: r["year"])
        sales_series = {r["year"]: r["sales"] for r in rows_sorted}
        net_profit_series = {r["year"]: r["net_profit"] for r in rows_sorted}
        eps_series = {r["year"]: r["eps"] for r in rows_sorted}

        face_value = face_value_by_company.get(company_id)
        broad_sector = sector_by_company.get(company_id)

        for pl in rows_sorted:
            year = pl["year"]
            bs = bs_by_key.get((company_id, year))
            cf = cf_by_key.get((company_id, year))

            profitability_row = {
                "company_id": company_id,
                "year": year,
                "sales": pl["sales"],
                "net_profit": pl["net_profit"],
                "operating_profit": pl["operating_profit"],
                "opm_percentage": pl["opm_percentage"],
                "depreciation": pl["depreciation"],
                "equity_capital": bs["equity_capital"] if bs else None,
                "reserves": bs["reserves"] if bs else None,
                "borrowings": bs["borrowings"] if bs else None,
                "total_assets": bs["total_assets"] if bs else None,
                "broad_sector": broad_sector,
            }
            profitability = compute_profitability_ratios(profitability_row)

            leverage_row = {
                **profitability_row,
                "other_income": pl["other_income"],
                "interest": pl["interest"],
                "investments": bs["investments"] if bs else None,
            }
            leverage = compute_leverage_efficiency_ratios(leverage_row)

            cashflow_row = {
                "company_id": company_id,
                "year": year,
                "operating_activity": cf["operating_activity"] if cf else None,
                "investing_activity": cf["investing_activity"] if cf else None,
                "financing_activity": cf["financing_activity"] if cf else None,
                "sales": pl["sales"],
                "operating_profit": pl["operating_profit"],
                "net_profit": pl["net_profit"],
            }
            cashflow = compute_cashflow_kpis_single_year(cashflow_row)

            growth = compute_growth_metrics(
                company_id, year, sales_series, net_profit_series, eps_series
            )

            bvps = book_value_per_share(
                bs["equity_capital"] if bs else None,
                bs["reserves"] if bs else None,
                face_value,
            )
            capex = capex_cr(cf["investing_activity"] if cf else None)

            computed_rows.append(
                {
                    "company_id": company_id,
                    "year": year,
                    "net_profit_margin_pct": profitability["net_profit_margin_pct"],
                    "operating_profit_margin_pct": profitability[
                        "operating_profit_margin_pct"
                    ],
                    "return_on_equity_pct": profitability["return_on_equity_pct"],
                    "return_on_capital_employed_pct": profitability[
                        "return_on_capital_employed_pct"
                    ],
                    "return_on_assets_pct": profitability["return_on_assets_pct"],
                    "debt_to_equity": leverage["debt_to_equity"],
                    "interest_coverage": leverage["interest_coverage"],
                    "asset_turnover": leverage["asset_turnover"],
                    "free_cash_flow_cr": cashflow["free_cash_flow_cr"],
                    "capex_cr": capex,
                    "earnings_per_share": pl["eps"],
                    "book_value_per_share": bvps,
                    "dividend_payout_ratio_pct": pl["dividend_payout"],
                    "total_debt_cr": bs["borrowings"] if bs else None,
                    "cash_from_operations_cr": cf["operating_activity"] if cf else None,
                    "revenue_cagr_5yr": growth["revenue_cagr_5yr"],
                    "pat_cagr_5yr": growth["pat_cagr_5yr"],
                    "eps_cagr_5yr": growth["eps_cagr_5yr"],
                }
            )

    # Composite quality score needs cross-sectional (same-year) percentiles
    # across companies, so it's computed in a second pass, grouped by year.
    rows_by_year: dict[str, list] = {}
    for row in computed_rows:
        rows_by_year.setdefault(row["year"], []).append(row)

    for year, year_rows in rows_by_year.items():
        scores = compute_quality_scores_for_year(year_rows)
        score_by_company = {
            s["company_id"]: s["composite_quality_score"] for s in scores
        }
        for row in year_rows:
            row["composite_quality_score"] = score_by_company.get(row["company_id"])

    return computed_rows


def write_rows(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Write rows."""
    conn.execute("DELETE FROM financial_ratios")
    columns = list(REQUIRED_COLUMNS.keys())
    column_list = ", ".join(["company_id", "year"] + columns)
    placeholders = ", ".join("?" for _ in (["company_id", "year"] + columns))
    insert_sql = f"INSERT INTO financial_ratios ({column_list}) VALUES ({placeholders})"

    for row in rows:
        values = [row["company_id"], row["year"]] + [row.get(c) for c in columns]
        conn.execute(insert_sql, values)

    conn.commit()
    return conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]


def main():
    """Main."""
    conn = sqlite3.connect(DB_PATH)
    ensure_columns(conn)
    rows = compute_all_rows(conn)
    count = write_rows(conn, rows)
    print(f"Inserted {count} rows into financial_ratios.")
    conn.close()


if __name__ == "__main__":
    main()
