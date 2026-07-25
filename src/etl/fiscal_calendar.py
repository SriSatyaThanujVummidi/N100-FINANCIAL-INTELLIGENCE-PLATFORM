"""
src/etl/fiscal_calendar.py

Day 33 root-cause fix: ~79 companies carry a spurious interim row
(mostly "2024-09", a half-year snapshot) inside balancesheet ONLY —
profitandloss and cashflow are unaffected (confirmed via
day33_diagnose_offcycle_years.py). Any code doing "ORDER BY year DESC
LIMIT N" against balancesheet silently mixes an interim row into what's
meant to be an annual-only sequence.

This module provides one shared, tested way to get a company's own
dominant fiscal-year-end month and to filter any table's rows down to
that company's real annual cadence — so every consumer (Day 31's
deleveraging flag, Day 33's BS chart, and any future module) uses the
same corrected logic instead of each re-implementing it slightly
differently.

Known genuine multi-fiscal-month histories this must NOT break (Day 15
finding): SIEMENS (Sep FYE throughout), NESTLEIND/AMBUJACEM/EICHERMOT/
BOSCHLTD/ABB (Dec FYE, some with early-history June/Dec before settling
on March) — dominant-month selection (most common month in a company's
own history) handles these correctly by design, since it asks each
company what ITS normal cadence is rather than assuming March globally.
"""

import sqlite3
from collections import Counter
from typing import Optional


def get_dominant_fiscal_month(
    conn: sqlite3.Connection, company_id: str, table: str
) -> Optional[str]:
    """Returns the 2-digit month string (e.g. '03') that appears most
    often in this company's own year history for the given table.
    Returns None if the company has zero rows (e.g. SBIN in
    balancesheet — Sprint 1 Day 6, genuine source gap)."""
    years = [
        r[0]
        for r in conn.execute(
            f"SELECT year FROM {table} WHERE company_id = ?", (company_id,)
        )
    ]
    if not years:
        return None
    months = [y.split("-")[1] for y in years if "-" in y]
    if not months:
        return None
    return Counter(months).most_common(1)[0][0]


def get_annual_rows(
    conn: sqlite3.Connection,
    company_id: str,
    table: str,
    columns: str,
    limit: Optional[int] = None,
) -> list[sqlite3.Row]:
    """Returns rows for this company from `table`, restricted to their
    OWN dominant fiscal month (filters out off-cycle interim rows like
    the 2024-09 balancesheet snapshot), ordered by year descending.
    columns: a SQL column list, e.g. "year, borrowings" or "*".
    """
    dominant_month = get_dominant_fiscal_month(conn, company_id, table)
    if dominant_month is None:
        return []

    query = (
        f"SELECT {columns} FROM {table} WHERE company_id = ? "
        f"AND year LIKE ? ORDER BY year DESC"
    )
    params = (company_id, f"%-{dominant_month}")
    if limit is not None:
        query += " LIMIT ?"
        params = params + (limit,)

    return conn.execute(query, params).fetchall()
