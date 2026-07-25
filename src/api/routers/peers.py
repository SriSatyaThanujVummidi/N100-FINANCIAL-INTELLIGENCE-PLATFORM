"""
Day 40 -- Peer Comparison endpoints (Sprint 6, Module 11)

peer_percentiles column names resolved via introspection, same precedent as Day 31/36/37.
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from src.api.db import get_db

router = APIRouter(tags=["peers"])

RADAR_METRICS = [
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "net_profit_margin_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "pat_cagr_5yr",
    "revenue_cagr_5yr",
    "eps_cagr_5yr",
]


def _peer_percentiles_columns(conn: sqlite3.Connection) -> set:
    return {
        row[1] for row in conn.execute("PRAGMA table_info(peer_percentiles)").fetchall()
    }


@router.get("/peers/{group_name}")
def get_peer_group(group_name: str, conn: sqlite3.Connection = Depends(get_db)):
    """Get peer group."""
    valid_groups = {
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT peer_group_name FROM peer_groups"
        ).fetchall()
    }
    if group_name not in valid_groups:
        raise HTTPException(
            status_code=404,
            detail=f"Peer group '{group_name}' not found. Valid groups: {sorted(valid_groups)}",
        )

    cols = _peer_percentiles_columns(conn)
    metric_col = "metric" if "metric" in cols else "metric_name"
    percentile_col = "percentile_rank" if "percentile_rank" in cols else "percentile"

    query = f"""
        SELECT pp.company_id, c.company_name, pp.{metric_col} AS metric, pp.{percentile_col} AS percentile_rank
        FROM peer_percentiles pp
        JOIN peer_groups pg ON pp.company_id = pg.company_id AND pg.peer_group_name = ?
        JOIN companies c ON pp.company_id = c.id
    """
    rows = conn.execute(query, (group_name,)).fetchall()

    by_company = {}
    for r in rows:
        row = dict(r)
        cid = row["company_id"]
        by_company.setdefault(
            cid,
            {"company_id": cid, "company_name": row["company_name"], "percentiles": {}},
        )
        by_company[cid]["percentiles"][row["metric"]] = row["percentile_rank"]

    benchmark_row = conn.execute(
        "SELECT company_id FROM peer_groups WHERE peer_group_name = ? AND is_benchmark = 1",
        (group_name,),
    ).fetchone()

    return {
        "peer_group_name": group_name,
        "benchmark_company": benchmark_row["company_id"] if benchmark_row else None,
        "companies": list(by_company.values()),
    }


@router.get("/companies/{ticker}/peers/compare")
def compare_to_peers(ticker: str, conn: sqlite3.Connection = Depends(get_db)):
    """Compare to peers."""
    ticker = ticker.strip().upper()
    company = conn.execute(
        "SELECT id FROM companies WHERE id = ?", (ticker,)
    ).fetchone()
    if company is None:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    company_ratios = conn.execute(
        """SELECT * FROM financial_ratios WHERE company_id = ?
           AND year = (SELECT MAX(year) FROM financial_ratios WHERE company_id = ?)""",
        (ticker, ticker),
    ).fetchone()
    company_values = (
        {m: company_ratios[m] for m in RADAR_METRICS}
        if company_ratios
        else {m: None for m in RADAR_METRICS}
    )

    group_row = conn.execute(
        "SELECT peer_group_name FROM peer_groups WHERE company_id = ?", (ticker,)
    ).fetchone()
    if group_row is None:
        # Documented, expected case (36/92 companies, Day 18) -- not an error.
        return {
            "company_id": ticker,
            "peer_group_name": None,
            "message": "No peer group assigned",
            "company_values": company_values,
            "peer_group_average": None,
            "benchmark_company": None,
            "benchmark_values": None,
        }

    group_name = group_row["peer_group_name"]
    peer_ids = [
        r[0]
        for r in conn.execute(
            "SELECT company_id FROM peer_groups WHERE peer_group_name = ?",
            (group_name,),
        ).fetchall()
    ]

    placeholders = ",".join("?" * len(peer_ids))
    peer_rows = conn.execute(
        f"""SELECT fr.* FROM financial_ratios fr
            INNER JOIN (
                SELECT company_id, MAX(year) AS max_year FROM financial_ratios
                WHERE company_id IN ({placeholders}) GROUP BY company_id
            ) latest ON fr.company_id = latest.company_id AND fr.year = latest.max_year
            WHERE fr.company_id IN ({placeholders})""",
        peer_ids + peer_ids,
    ).fetchall()

    group_average = {}
    for m in RADAR_METRICS:
        values = [
            r[m] for r in peer_rows if r[m] is not None and r["company_id"] != ticker
        ]
        group_average[m] = round(sum(values) / len(values), 2) if values else None

    benchmark_row = conn.execute(
        "SELECT company_id FROM peer_groups WHERE peer_group_name = ? AND is_benchmark = 1",
        (group_name,),
    ).fetchone()
    benchmark_id = benchmark_row["company_id"] if benchmark_row else None
    benchmark_values = None
    if benchmark_id:
        b_ratios = conn.execute(
            """SELECT * FROM financial_ratios WHERE company_id = ?
               AND year = (SELECT MAX(year) FROM financial_ratios WHERE company_id = ?)""",
            (benchmark_id, benchmark_id),
        ).fetchone()
        benchmark_values = {m: b_ratios[m] for m in RADAR_METRICS} if b_ratios else None

    return {
        "company_id": ticker,
        "peer_group_name": group_name,
        "company_values": company_values,
        "peer_group_average": group_average,
        "benchmark_company": benchmark_id,
        "benchmark_values": benchmark_values,
    }
