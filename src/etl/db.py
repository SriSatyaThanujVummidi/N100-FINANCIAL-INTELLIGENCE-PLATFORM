"""SQLite schema creation and generic DataFrame insertion helpers.

Separate from loader.py (Day 2), which owns Excel reading + normalisation.
This module only talks to SQLite: create tables, insert DataFrames, check FKs.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("DB_PATH", PROJECT_ROOT / "data" / "nifty100.db"))
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with foreign key enforcement turned on."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_database(conn: sqlite3.Connection, schema_path: Path = SCHEMA_PATH) -> None:
    """Create all tables from schema.sql. Safe to re-run (IF NOT EXISTS)."""
    sql_script = schema_path.read_text(encoding="utf-8")
    conn.executescript(sql_script)
    conn.commit()
    logger.info("Schema applied from %s", schema_path)


def insert_dataframe(
    conn: sqlite3.Connection,
    table_name: str,
    df: pd.DataFrame,
    if_exists: str = "append",
) -> int:
    """Insert a normalised DataFrame into an existing table. Returns row count inserted.

    Raises sqlite3.IntegrityError on FK/PK violations (unwrapped from pandas'
    DatabaseError so callers can catch a consistent, real exception type).
    """
    try:
        df.to_sql(table_name, conn, if_exists=if_exists, index=False)
    except pd.errors.DatabaseError as exc:
        if isinstance(exc.__cause__, sqlite3.IntegrityError):
            raise exc.__cause__ from exc
        raise
    conn.commit()
    logger.info("Inserted %d rows into %s", len(df), table_name)
    return len(df)


def list_tables(conn: sqlite3.Connection) -> list[str]:
    """Return all user table names currently in the database."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    )
    return [row[0] for row in cursor.fetchall()]


def foreign_key_check(conn: sqlite3.Connection) -> list[tuple]:
    """Return any FK violations. Empty list = all good."""
    cursor = conn.execute("PRAGMA foreign_key_check;")
    return cursor.fetchall()


if __name__ == "__main__":
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    create_database(conn)

    tables = list_tables(conn)
    print(f"Tables created ({len(tables)}): {tables}")

    violations = foreign_key_check(conn)
    print(f"Foreign key violations: {len(violations)}")

    conn.close()
