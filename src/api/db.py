"""
Day 38 -- Shared SQLite connection helper for the FastAPI layer.
"""

import os
import sqlite3
from typing import Generator

DB_PATH = os.environ.get("DB_PATH", "data/nifty100.db")

# 12 real tables (per Sprint 1 Day 4 finding) -- spec's "10 tables" phrasing is internally
# inconsistent, same documented issue as schema.sql/Day 22's db_row_counts expectations.
ALL_TABLES = [
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons",
    "sectors",
    "stock_prices",
    "market_cap",
    "financial_ratios",
    "peer_groups",
]


def get_connection() -> sqlite3.Connection:
    """Get connection."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency -- yields a connection per request, closes it after."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def get_row_counts(conn: sqlite3.Connection) -> dict:
    """Get row counts."""
    counts = {}
    for table in ALL_TABLES:
        try:
            row = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
            counts[table] = row["n"]
        except sqlite3.OperationalError:
            counts[table] = None
    return counts


def normalize_ticker(ticker: str) -> str:
    """Normalize ticker."""
    return ticker.strip().upper()


def company_exists(conn, ticker: str) -> bool:
    """Company exists."""
    row = conn.execute("SELECT 1 FROM companies WHERE id = ?", (ticker,)).fetchone()
    return row is not None


def get_latest_financial_ratios(conn, ticker: str):
    """Per-company own latest year (not a global year filter) -- same pattern used
    throughout this project since Day 15/22 to handle non-March fiscal year-ends."""
    query = """
        SELECT fr.* FROM financial_ratios fr
        WHERE fr.company_id = ?
          AND fr.year = (SELECT MAX(year) FROM financial_ratios WHERE company_id = ?)
    """
    row = conn.execute(query, (ticker, ticker)).fetchone()
    return dict(row) if row else None


RATIO_SANITY_BOUND = 500.0  # same +/-500% bound as Day 13/17/18/36/37
RATIO_SANITY_FIELDS = [
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "return_on_assets_pct",
]


def mask_if_implausible(value, bound: float = RATIO_SANITY_BOUND):
    """Returns (value_or_None, flag). Unlike internal pipelines (Day 13/17/18) which mask
    silently, the API surfaces WHY a value is missing via the flag -- a bare null here would
    look like 'we don't have this data' when the truth is 'we have it and it's implausible'
    (same distinction Day 31 already established for distress_flag: None != False)."""
    if value is not None and abs(value) > bound:
        return None, "excluded_sanity_bound_exceeded"
    return value, None


def apply_sanity_flags(ratios: dict) -> dict:
    """Applies mask_if_implausible() to ROE/ROCE/ROA within a financial_ratios row dict,
    adding a '<field>_quality_flag' sibling for each. No-op if ratios is None (e.g. SBIN,
    which has no financial_ratios coverage at all for BS-anchored metrics)."""
    if ratios is None:
        return ratios
    out = dict(ratios)
    for field in RATIO_SANITY_FIELDS:
        value, flag = mask_if_implausible(out.get(field))
        out[field] = value
        out[f"{field}_quality_flag"] = flag
    return out


def parse_float_param(value, name: str):
    """Parses a query-string float param, raising HTTP 400 (not FastAPI's default 422)
    on invalid input, per spec's explicit requirement for the screener endpoint."""
    from fastapi import HTTPException

    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid value for '{name}': {value!r} is not a number",
        )
