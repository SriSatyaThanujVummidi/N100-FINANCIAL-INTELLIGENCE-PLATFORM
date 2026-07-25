"""
Day 39 -- Company Data endpoints (Sprint 6, Module 11)

GET /companies, /companies/{ticker}, /pl, /bs, /cashflow, /ratios, /tearsheet.

Post-Day-39 fix: /companies and /companies/{ticker} were exposing raw, unmasked ROE/ROCE/ROA
values (HAL=3816%, INDIGO=892%/4953%, etc.) -- inconsistent with every other module downstream
of financial_ratios (composite score, screener, peer percentiles, clustering, portfolio stats --
Day 13/17/18/36/37), all of which mask these with a +/-500% sanity bound. Now masked here too,
via db.py's mask_if_implausible()/apply_sanity_flags() -- with an explicit '<field>_quality_flag'
sibling on each masked value, since a bare null on a public API endpoint would misleadingly look
like missing data rather than 'present but implausible'.
"""

import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from src.api.db import (
    get_db,
    normalize_ticker,
    company_exists,
    get_latest_financial_ratios,
    mask_if_implausible,
    apply_sanity_flags,
)

router = APIRouter(tags=["companies"])

TEARSHEET_DIR = Path("reports/tearsheets")


@router.get("/companies")
def list_companies(
    sector: Optional[str] = Query(None, description="Filter by broad_sector"),
    market_cap_category: Optional[str] = Query(
        None, description="Filter by market_cap_category"
    ),
    search: Optional[str] = Query(
        None, description="Partial match on ticker or company name"
    ),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List companies."""
    query = """
        SELECT c.id, c.company_name, s.broad_sector, s.sub_sector, s.market_cap_category,
               fr.return_on_equity_pct AS roe_pct, fr.return_on_capital_employed_pct AS roce_pct
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        LEFT JOIN (
            SELECT fr1.company_id, fr1.return_on_equity_pct, fr1.return_on_capital_employed_pct
            FROM financial_ratios fr1
            INNER JOIN (
                SELECT company_id, MAX(year) AS max_year FROM financial_ratios GROUP BY company_id
            ) latest ON fr1.company_id = latest.company_id AND fr1.year = latest.max_year
        ) fr ON c.id = fr.company_id
        WHERE 1=1
    """
    params = []
    if sector:
        query += " AND s.broad_sector = ?"
        params.append(sector)
    if market_cap_category:
        query += " AND s.market_cap_category = ?"
        params.append(market_cap_category)
    if search:
        query += " AND (c.id LIKE ? OR c.company_name LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])

    rows = conn.execute(query, params).fetchall()
    results = []
    for r in rows:
        row = dict(r)
        roe, roe_flag = mask_if_implausible(row["roe_pct"])
        roce, roce_flag = mask_if_implausible(row["roce_pct"])
        row["roe_pct"] = roe
        row["roe_pct_quality_flag"] = roe_flag
        row["roce_pct"] = roce
        row["roce_pct_quality_flag"] = roce_flag
        results.append(row)
    return results


@router.get("/companies/{ticker}")
def get_company_profile(ticker: str, conn: sqlite3.Connection = Depends(get_db)):
    """Get company profile."""
    ticker = normalize_ticker(ticker)
    company = conn.execute("SELECT * FROM companies WHERE id = ?", (ticker,)).fetchone()
    if company is None:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    sector = conn.execute(
        "SELECT * FROM sectors WHERE company_id = ?", (ticker,)
    ).fetchone()
    ratios = get_latest_financial_ratios(conn, ticker)
    ratios = apply_sanity_flags(
        ratios
    )  # masks return_on_equity_pct/return_on_capital_employed_pct/return_on_assets_pct

    profile = dict(company)
    profile["sector"] = dict(sector) if sector else None
    profile["latest_ratios"] = (
        ratios  # None if genuinely unavailable (e.g. SBIN -- documented gap)
    )
    return profile


def _year_range_query(
    table: str, ticker: str, from_year: Optional[str], to_year: Optional[str]
):
    query = f"SELECT * FROM {table} WHERE company_id = ?"
    params = [ticker]
    if from_year:
        query += " AND year >= ?"
        params.append(from_year)
    if to_year:
        query += " AND year <= ?"
        params.append(to_year)
    query += " ORDER BY year"
    return query, params


@router.get("/companies/{ticker}/pl")
def get_pl_history(
    ticker: str,
    from_year: Optional[str] = Query(None, description="YYYY-MM"),
    to_year: Optional[str] = Query(None, description="YYYY-MM"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get pl history."""
    ticker = normalize_ticker(ticker)
    if not company_exists(conn, ticker):
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")
    query, params = _year_range_query("profitandloss", ticker, from_year, to_year)
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@router.get("/companies/{ticker}/bs")
def get_bs_history(
    ticker: str,
    from_year: Optional[str] = Query(None, description="YYYY-MM"),
    to_year: Optional[str] = Query(None, description="YYYY-MM"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get bs history."""
    ticker = normalize_ticker(ticker)
    if not company_exists(conn, ticker):
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")
    # Empty array (not 404) is the correct response for tickers like SBIN with a genuine,
    # documented zero-row balance sheet gap (Sprint 1 Day 6) -- ticker exists, data doesn't.
    query, params = _year_range_query("balancesheet", ticker, from_year, to_year)
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@router.get("/companies/{ticker}/cashflow")
def get_cashflow_history(
    ticker: str,
    from_year: Optional[str] = Query(None, description="YYYY-MM"),
    to_year: Optional[str] = Query(None, description="YYYY-MM"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get cashflow history."""
    ticker = normalize_ticker(ticker)
    if not company_exists(conn, ticker):
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")
    query, params = _year_range_query("cashflow", ticker, from_year, to_year)
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@router.get("/companies/{ticker}/ratios")
def get_ratios(
    ticker: str,
    year: Optional[str] = Query(None, description="YYYY-MM -- omit for all years"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get ratios."""
    ticker = normalize_ticker(ticker)
    if not company_exists(conn, ticker):
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")
    if year:
        rows = conn.execute(
            "SELECT * FROM financial_ratios WHERE company_id = ? AND year = ?",
            (ticker, year),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year",
            (ticker,),
        ).fetchall()
    # NOTE: full year-by-year history intentionally NOT sanity-flagged here -- this endpoint
    # returns the Ratio Engine's raw computed output per spec ("all computed KPIs per year"),
    # and a company's ROE can legitimately swing in/out of plausibility across different years.
    # Masking is applied at /companies and /companies/{ticker} (latest-year summary views)
    # where a single implausible headline number is most likely to mislead a consumer.
    return [dict(r) for r in rows]


@router.get("/companies/{ticker}/tearsheet")
def get_tearsheet(ticker: str, conn: sqlite3.Connection = Depends(get_db)):
    """Get tearsheet."""
    ticker = normalize_ticker(ticker)
    if not company_exists(conn, ticker):
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    pdf_path = TEARSHEET_DIR / f"{ticker}_tearsheet.pdf"
    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Tearsheet not available for '{ticker}' (possibly skipped due to insufficient history)",
        )
    return FileResponse(
        path=pdf_path, media_type="application/pdf", filename=pdf_path.name
    )
