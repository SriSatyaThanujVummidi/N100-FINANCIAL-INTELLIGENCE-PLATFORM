"""
Day 38 -- Health check endpoint (AC-11: GET /api/v1/health returns HTTP 200
with db_row_counts for all tables).
"""

import time
import sqlite3

from fastapi import APIRouter, Depends

from src.api.db import get_db, get_row_counts
from src.api.state import APP_START_TIME, API_VERSION

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(conn: sqlite3.Connection = Depends(get_db)):
    """Health check."""
    return {
        "status": "ok",
        "db_row_counts": get_row_counts(conn),
        "uptime_seconds": round(time.time() - APP_START_TIME, 1),
        "version": API_VERSION,
    }
