"""Day 40 -- GET /api/v1/market-cap/{ticker}: historical P/E, P/B, EV/EBITDA, dividend yield."""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.db import get_db, company_exists

router = APIRouter(tags=["valuation"])


@router.get("/market-cap/{ticker}")
def get_market_cap_history(
    ticker: str,
    from_year: Optional[int] = Query(None),
    to_year: Optional[int] = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get market cap history."""
    ticker = ticker.strip().upper()
    if not company_exists(conn, ticker):
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    query = "SELECT * FROM market_cap WHERE company_id = ?"
    params = [ticker]
    if from_year:
        query += " AND year >= ?"
        params.append(from_year)
    if to_year:
        query += " AND year <= ?"
        params.append(to_year)
    query += " ORDER BY year"

    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]
