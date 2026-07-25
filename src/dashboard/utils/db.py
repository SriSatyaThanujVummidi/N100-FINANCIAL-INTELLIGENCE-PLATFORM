"""Shared, cached SQLite data loader for the Streamlit dashboard.

Every public function is wrapped in @st.cache_data(ttl=600) per Day 22's
spec requirement. Queries use SELECT * wherever the exact downstream
column set isn't fixed yet (financial_ratios' column list has grown twice
already — Day 12 -> 19 cols, Day 17 added composite_score_sector_relative —
so we don't hardcode column names here and risk a silent KeyError later).
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# db.py lives at src/dashboard/utils/db.py -> parents[3] is the project root
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_PROJECT_ROOT / ".env")

_DB_PATH_RAW = os.getenv("DB_PATH", "data/nifty100.db")
_DB_PATH = Path(_DB_PATH_RAW)
if not _DB_PATH.is_absolute():
    _DB_PATH = _PROJECT_ROOT / _DB_PATH


def _get_connection() -> sqlite3.Connection:
    if not _DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {_DB_PATH}. Check DB_PATH in .env "
            "and confirm make load / full_load.py has been run."
        )
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    """All 92 companies joined with their sector mapping."""
    query = """
        SELECT c.*, s.broad_sector, s.sub_sector, s.index_weight_pct, s.market_cap_category
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        ORDER BY c.id
    """
    with _get_connection() as conn:
        return pd.read_sql_query(query, conn)


@st.cache_data(ttl=600)
def get_ratios(
    ticker: Optional[str] = None, year: Optional[str] = None
) -> pd.DataFrame:
    """financial_ratios rows, optionally filtered by ticker and/or year.
    Returns all reported years for a ticker if year is None."""
    query = "SELECT * FROM financial_ratios WHERE 1=1"
    params: list = []
    if ticker:
        query += " AND company_id = ?"
        params.append(ticker.strip().upper())
    if year:
        query += " AND year = ?"
        params.append(year)
    query += " ORDER BY company_id, year"
    with _get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


@st.cache_data(ttl=600)
def get_latest_ratios() -> pd.DataFrame:
    """One row per company at THEIR OWN latest reported year — reuses Day 15's
    per-company MAX(year) join so SIEMENS's Sep fiscal year-end doesn't get
    silently dropped by a shared year filter."""
    query = """
        SELECT r.*
        FROM financial_ratios r
        INNER JOIN (
            SELECT company_id, MAX(year) AS max_year
            FROM financial_ratios
            GROUP BY company_id
        ) latest
        ON r.company_id = latest.company_id AND r.year = latest.max_year
    """
    with _get_connection() as conn:
        return pd.read_sql_query(query, conn)


@st.cache_data(ttl=600)
def get_ratios_as_of_calendar_year(calendar_year: int) -> pd.DataFrame:
    """One row per company: the latest financial_ratios row whose fiscal
    year-end falls on or before December of the given calendar year.

    Added for Day 23's Home screen year selector (spec: '2019 to 2024').
    A naive year='{Y}-03' filter would silently drop every non-March-FYE
    company (SIEMENS=Sep, NESTLEIND/AMBUJACEM/EICHERMOT/BOSCHLTD/ABB=Dec,
    per Day 15's finding) from every year's Home screen aggregate — this
    generalises Day 15's per-company MAX(year) fix to a capped version.
    """
    with _get_connection() as conn:
        all_ratios = pd.read_sql_query("SELECT * FROM financial_ratios", conn)
    if all_ratios.empty:
        return all_ratios
    cutoff = f"{calendar_year}-12"
    eligible = all_ratios[all_ratios["year"] <= cutoff]
    if eligible.empty:
        return eligible
    idx = eligible.groupby("company_id")["year"].idxmax()
    return eligible.loc[idx].reset_index(drop=True)


@st.cache_data(ttl=600)
def get_pl(ticker: str) -> pd.DataFrame:
    """Get pl."""
    query = "SELECT * FROM profitandloss WHERE company_id = ? ORDER BY year"
    with _get_connection() as conn:
        return pd.read_sql_query(query, conn, params=[ticker.strip().upper()])


@st.cache_data(ttl=600)
def get_bs(ticker: str) -> pd.DataFrame:
    """Get bs."""
    query = "SELECT * FROM balancesheet WHERE company_id = ? ORDER BY year"
    with _get_connection() as conn:
        return pd.read_sql_query(query, conn, params=[ticker.strip().upper()])


@st.cache_data(ttl=600)
def get_cf(ticker: str) -> pd.DataFrame:
    """Get cf."""
    query = "SELECT * FROM cashflow WHERE company_id = ? ORDER BY year"
    with _get_connection() as conn:
        return pd.read_sql_query(query, conn, params=[ticker.strip().upper()])


@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    """Get sectors."""
    with _get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM sectors ORDER BY broad_sector, company_id", conn
        )


@st.cache_data(ttl=600)
def get_peers(group_name: str) -> pd.DataFrame:
    """Members of one peer group (Day 18 real shape: one row per
    company-per-group, not spec's assumed comma-separated format)."""
    query = "SELECT * FROM peer_groups WHERE peer_group_name = ?"
    with _get_connection() as conn:
        return pd.read_sql_query(query, conn, params=[group_name])


@st.cache_data(ttl=600)
def get_peer_percentiles(group_name: Optional[str] = None) -> pd.DataFrame:
    """Day 18's peer_percentiles table (560 rows: 56 companies x 10 metrics)."""
    query = "SELECT * FROM peer_percentiles WHERE 1=1"
    params: list = []
    if group_name:
        query += " AND peer_group_name = ?"
        params.append(group_name)
    with _get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


@st.cache_data(ttl=600)
def get_valuation(ticker: Optional[str] = None) -> pd.DataFrame:
    """market_cap table — raw P/E, P/B, EV/EBITDA, dividend yield.
    NOTE: Day 26 hasn't run yet, so overvaluation flags (Caution/Discount/
    Fair) don't exist until then. This returns the raw table only."""
    query = "SELECT * FROM market_cap WHERE 1=1"
    params: list = []
    if ticker:
        query += " AND company_id = ?"
        params.append(ticker.strip().upper())
    query += " ORDER BY company_id, year"
    with _get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


@st.cache_data(ttl=600)
def get_prosandcons(ticker: str) -> pd.DataFrame:
    """Get prosandcons."""
    query = "SELECT * FROM prosandcons WHERE company_id = ?"
    with _get_connection() as conn:
        return pd.read_sql_query(query, conn, params=[ticker.strip().upper()])


@st.cache_data(ttl=600)
def get_documents(ticker: str) -> pd.DataFrame:
    """Day 4 renamed spec's capital-'Year' column to report_year in the real
    schema — see PROGRESS.md Day 4 note. Query uses the real column name."""
    query = "SELECT * FROM documents WHERE company_id = ? ORDER BY report_year"
    with _get_connection() as conn:
        return pd.read_sql_query(query, conn, params=[ticker.strip().upper()])


@st.cache_data(ttl=600)
def get_capital_allocation() -> pd.DataFrame:
    """Day 11's output/capital_allocation.csv — this was written as a CSV,
    never loaded back into SQLite, so it's read from disk (still cached
    the same way as the DB calls for a consistent API)."""
    csv_path = _PROJECT_ROOT / "output" / "capital_allocation.csv"
    if not csv_path.exists():
        return pd.DataFrame()
    return pd.read_csv(csv_path)


@st.cache_data(ttl=600)
def get_latest_pl_all() -> pd.DataFrame:
    """One P&L row per company at THEIR OWN latest reported year — same
    per-company MAX(year) pattern as get_latest_ratios(), needed for Day 25's
    Sector Analysis bubble chart (X=Revenue) across all 92 companies at once
    rather than looping get_pl(ticker) 92 times."""
    query = """
        SELECT p.*
        FROM profitandloss p
        INNER JOIN (
            SELECT company_id, MAX(year) AS max_year
            FROM profitandloss
            GROUP BY company_id
        ) latest
        ON p.company_id = latest.company_id AND p.year = latest.max_year
    """
    with _get_connection() as conn:
        return pd.read_sql_query(query, conn)


@st.cache_data(ttl=600)
def get_latest_market_cap_all() -> pd.DataFrame:
    """One market_cap row per company at their latest available year —
    needed for Day 25's Sector Analysis bubble size (Market Cap)."""
    query = """
        SELECT m.*
        FROM market_cap m
        INNER JOIN (
            SELECT company_id, MAX(year) AS max_year
            FROM market_cap
            GROUP BY company_id
        ) latest
        ON m.company_id = latest.company_id AND m.year = latest.max_year
    """
    with _get_connection() as conn:
        return pd.read_sql_query(query, conn)
