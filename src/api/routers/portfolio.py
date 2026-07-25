"""
Day 40 -- GET /api/v1/portfolio/stats

Reuses Day 37's portfolio_stats.py functions directly rather than reimplementing the same
masking/exclusion logic a second time.
"""

import sqlite3

from fastapi import APIRouter, Depends

from src.api.db import get_db
from src.analytics.portfolio_stats import (
    resolve_kpi_columns,
    load_latest_kpis,
    apply_ratio_sanity_bounds,
    apply_known_anomaly_exclusions,
    generate_portfolio_stats,
)

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio/stats")
def get_portfolio_stats(conn: sqlite3.Connection = Depends(get_db)):
    """Get portfolio stats."""
    kpi_map = resolve_kpi_columns(conn)
    df = load_latest_kpis(conn, kpi_map)
    df = apply_ratio_sanity_bounds(df)
    df = apply_known_anomaly_exclusions(df)
    stats = generate_portfolio_stats(df, list(kpi_map.keys()))
    return stats.to_dict(orient="records")
