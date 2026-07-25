"""
Day 40 -- Screener endpoint (Sprint 6, Module 11)

GET /api/v1/screener?min_roe=&max_de=&min_fcf=&sector=&min_rev_cagr_5yr=&min_pat_cagr_5yr=&max_pe=

FIX (Day 45, found via AC-13 acceptance-gate investigation): the D/E filter applied a flat
threshold to every company, with no exemption for Financials -- unlike src/screener/engine.py
(Sprint 3 Day 16), which has always exempted Financials from the D/E max filter since high
leverage is structurally normal for lenders. This caused ICICIBANK (D/E=6.45x) and CANBK
(D/E=14.87x) to be silently excluded from the API's Quality Compounder-equivalent results
while correctly appearing in screener_output.xlsx. Fixed by adding the same carve-out used
everywhere else in this project.
"""
import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.api.db import get_db, parse_float_param, mask_if_implausible

router = APIRouter(tags=["screener"])

FINANCIALS_SECTOR = "Financials"


@router.get("/screener")
def run_screener(
    min_roe: Optional[str] = Query(None),
    max_de: Optional[str] = Query(None),
    min_fcf: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    min_rev_cagr_5yr: Optional[str] = Query(None),
    min_pat_cagr_5yr: Optional[str] = Query(None),
    max_pe: Optional[str] = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
):
    min_roe_v = parse_float_param(min_roe, "min_roe")
    max_de_v = parse_float_param(max_de, "max_de")
    min_fcf_v = parse_float_param(min_fcf, "min_fcf")
    min_rev_cagr_v = parse_float_param(min_rev_cagr_5yr, "min_rev_cagr_5yr")
    min_pat_cagr_v = parse_float_param(min_pat_cagr_5yr, "min_pat_cagr_5yr")
    max_pe_v = parse_float_param(max_pe, "max_pe")

    query = """
        SELECT fr.company_id, c.company_name, s.broad_sector,
               fr.return_on_equity_pct, fr.debt_to_equity, fr.free_cash_flow_cr,
               fr.revenue_cagr_5yr, fr.pat_cagr_5yr, fr.composite_quality_score,
               mc.pe_ratio
        FROM financial_ratios fr
        INNER JOIN (
            SELECT company_id, MAX(year) AS max_year FROM financial_ratios GROUP BY company_id
        ) latest ON fr.company_id = latest.company_id AND fr.year = latest.max_year
        JOIN companies c ON fr.company_id = c.id
        LEFT JOIN sectors s ON fr.company_id = s.company_id
        LEFT JOIN (
            SELECT mc1.company_id, mc1.pe_ratio FROM market_cap mc1
            INNER JOIN (
                SELECT company_id, MAX(year) AS max_year FROM market_cap GROUP BY company_id
            ) mlatest ON mc1.company_id = mlatest.company_id AND mc1.year = mlatest.max_year
        ) mc ON fr.company_id = mc.company_id
    """
    rows = conn.execute(query).fetchall()

    results = []
    for r in rows:
        row = dict(r)
        roe, roe_flag = mask_if_implausible(row["return_on_equity_pct"])
        row["return_on_equity_pct"] = roe
        row["return_on_equity_pct_quality_flag"] = roe_flag

        is_financials = row["broad_sector"] == FINANCIALS_SECTOR

        if sector and row["broad_sector"] != sector:
            continue
        if min_roe_v is not None and (roe is None or roe < min_roe_v):
            continue
        # D/E-Financials carve-out: same exemption as src/screener/engine.py (Sprint 3 Day 16) --
        # high leverage is structurally normal for banks/NBFCs/insurers, so the max_de filter
        # does not apply to them, same as every other D/E rule in this project.
        if max_de_v is not None and not is_financials and (row["debt_to_equity"] is None or row["debt_to_equity"] > max_de_v):
            continue
        if min_fcf_v is not None and (row["free_cash_flow_cr"] is None or row["free_cash_flow_cr"] < min_fcf_v):
            continue
        if min_rev_cagr_v is not None and (row["revenue_cagr_5yr"] is None or row["revenue_cagr_5yr"] < min_rev_cagr_v):
            continue
        if min_pat_cagr_v is not None and (row["pat_cagr_5yr"] is None or row["pat_cagr_5yr"] < min_pat_cagr_v):
            continue
        if max_pe_v is not None and (row["pe_ratio"] is None or row["pe_ratio"] > max_pe_v):
            continue
        results.append(row)

    results.sort(key=lambda r: (r["composite_quality_score"] is None, -(r["composite_quality_score"] or 0)))
    return {"count": len(results), "results": results}