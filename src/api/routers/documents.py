"""
Day 40 -- GET /api/v1/companies/{ticker}/documents

Real schema: report_year/annual_report_url (Day 25 finding, not spec's Year/Annual_Report).
is_url_valid is null by default (not live-checked) -- pass ?live_check=true to opt in.

FIX (post Day 40 diagnostic): 285 rows across 77/92 companies store the literal string "Null"
(not a real SQL NULL) in annual_report_url -- concentrated in 2009-2011 (86% of companies
missing a report in 2009, decaying smoothly to near-zero by 2020), consistent with older
annual reports genuinely not being digitized at scrape time, not a loader defect. A separate
51 rows use a genuine SQL NULL for the same situation -- two representations of the same
"no report" case. Normalized to a real null here at the API boundary; ETL-layer fix (teaching
normaliser.py to coerce "Null" -> NULL at load time) flagged for a future data-quality pass,
not applied here since it would mean reopening already-signed-off Day 2/5 code.
"""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.db import get_db, company_exists

router = APIRouter(tags=["documents"])

NULL_URL_PLACEHOLDERS = {None, "", "Null", "null", "NULL"}


@router.get("/companies/{ticker}/documents")
def get_documents(
    ticker: str,
    from_year: Optional[int] = Query(None),
    to_year: Optional[int] = Query(None),
    live_check: bool = Query(
        False, description="If true, performs a live HTTP HEAD check per URL (slow)"
    ),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get documents."""
    ticker = ticker.strip().upper()
    if not company_exists(conn, ticker):
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    query = "SELECT report_year, annual_report_url FROM documents WHERE company_id = ?"
    params = [ticker]
    if from_year:
        query += " AND report_year >= ?"
        params.append(from_year)
    if to_year:
        query += " AND report_year <= ?"
        params.append(to_year)
    query += " ORDER BY report_year"

    rows = conn.execute(query, params).fetchall()
    results = []
    for r in rows:
        row = dict(r)
        url = row["annual_report_url"]
        if url in NULL_URL_PLACEHOLDERS:
            row["annual_report_url"] = None
            row["is_url_valid"] = None
            results.append(row)
            continue

        is_valid = None
        if live_check:
            import requests

            try:
                resp = requests.head(url, timeout=3)
                is_valid = resp.status_code == 200
            except requests.RequestException:
                is_valid = False
        row["is_url_valid"] = is_valid
        results.append(row)
    return results
