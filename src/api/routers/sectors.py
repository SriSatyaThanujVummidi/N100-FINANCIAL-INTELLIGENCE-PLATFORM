"""
Day 40 -- Sectors endpoints (Sprint 6, Module 11)

NOTE: the real sectors table has 10 distinct broad_sector values, not the spec's stated 11
(Sprint 4 Day 22/25's already-documented finding) -- returns whatever the real table contains.
"""

import statistics
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from src.api.db import get_db, mask_if_implausible

router = APIRouter(tags=["sectors"])


def _latest_ratios_with_sector(conn: sqlite3.Connection):
    query = """
        SELECT fr.company_id, fr.return_on_equity_pct, fr.debt_to_equity, s.broad_sector, mc.pe_ratio
        FROM financial_ratios fr
        INNER JOIN (
            SELECT company_id, MAX(year) AS max_year FROM financial_ratios GROUP BY company_id
        ) latest ON fr.company_id = latest.company_id AND fr.year = latest.max_year
        LEFT JOIN sectors s ON fr.company_id = s.company_id
        LEFT JOIN (
            SELECT mc1.company_id, mc1.pe_ratio FROM market_cap mc1
            INNER JOIN (
                SELECT company_id, MAX(year) AS max_year FROM market_cap GROUP BY company_id
            ) mlatest ON mc1.company_id = mlatest.company_id AND mc1.year = mlatest.max_year
        ) mc ON fr.company_id = mc.company_id
    """
    return [dict(r) for r in conn.execute(query).fetchall()]


@router.get("/sectors")
def list_sectors(conn: sqlite3.Connection = Depends(get_db)):
    """List sectors."""
    rows = _latest_ratios_with_sector(conn)
    by_sector = {}
    for r in rows:
        sector = r["broad_sector"]
        if sector is None:
            continue
        by_sector.setdefault(sector, []).append(r)

    results = []
    for sector, members in sorted(by_sector.items()):
        roes = [mask_if_implausible(m["return_on_equity_pct"])[0] for m in members]
        roes = [v for v in roes if v is not None]
        des = [m["debt_to_equity"] for m in members if m["debt_to_equity"] is not None]
        pes = [m["pe_ratio"] for m in members if m["pe_ratio"] is not None]
        results.append(
            {
                "broad_sector": sector,
                "company_count": len(members),
                "median_roe": round(statistics.median(roes), 2) if roes else None,
                "median_pe": round(statistics.median(pes), 2) if pes else None,
                "median_de": round(statistics.median(des), 2) if des else None,
            }
        )
    return results


@router.get("/sectors/{sector}/companies")
def get_sector_companies(sector: str, conn: sqlite3.Connection = Depends(get_db)):
    """Get sector companies."""
    valid_sectors = {
        row[0]
        for row in conn.execute("SELECT DISTINCT broad_sector FROM sectors").fetchall()
    }
    if sector not in valid_sectors:
        raise HTTPException(
            status_code=404,
            detail=f"Sector '{sector}' not found. Valid sectors: {sorted(valid_sectors)}",
        )

    query = """
        SELECT fr.company_id, c.company_name, fr.return_on_equity_pct, fr.return_on_capital_employed_pct,
               fr.debt_to_equity, fr.operating_profit_margin_pct, fr.free_cash_flow_cr,
               fr.net_profit_margin_pct, fr.composite_quality_score
        FROM financial_ratios fr
        INNER JOIN (
            SELECT company_id, MAX(year) AS max_year FROM financial_ratios GROUP BY company_id
        ) latest ON fr.company_id = latest.company_id AND fr.year = latest.max_year
        JOIN companies c ON fr.company_id = c.id
        JOIN sectors s ON fr.company_id = s.company_id
        WHERE s.broad_sector = ?
    """
    rows = conn.execute(query, (sector,)).fetchall()
    results = []
    for r in rows:
        row = dict(r)
        roe, roe_flag = mask_if_implausible(row["return_on_equity_pct"])
        roce, roce_flag = mask_if_implausible(row["return_on_capital_employed_pct"])
        row["return_on_equity_pct"] = roe
        row["return_on_equity_pct_quality_flag"] = roe_flag
        row["return_on_capital_employed_pct"] = roce
        row["return_on_capital_employed_pct_quality_flag"] = roce_flag
        results.append(row)
    return results
