"""Day 4 smoke tests: table creation + foreign key enforcement."""

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from src.etl.db import create_database, insert_dataframe, list_tables, foreign_key_check

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "src" / "etl" / "schema.sql"


@pytest.fixture
def conn(tmp_path):
    db_file = tmp_path / "test_nifty100.db"
    connection = sqlite3.connect(db_file)
    connection.execute("PRAGMA foreign_keys = ON;")
    create_database(connection, SCHEMA_PATH)
    yield connection
    connection.close()


def test_all_12_tables_created(conn):
    tables = list_tables(conn)
    assert len(tables) == 12


def test_company_insert_and_fk_pass(conn):
    companies_df = pd.DataFrame(
        [
            {
                "id": "TCS",
                "company_name": "Tata Consultancy Services Ltd",
                "face_value": 1,
            }
        ]
    )
    insert_dataframe(conn, "companies", companies_df)

    pl_df = pd.DataFrame(
        [
            {
                "company_id": "TCS",
                "year": "2023-03",
                "sales": 225458,
                "expenses": 176924,
                "operating_profit": 48534,
                "opm_percentage": 21.5,
            }
        ]
    )
    insert_dataframe(conn, "profitandloss", pl_df)

    assert foreign_key_check(conn) == []


def test_orphan_company_id_rejected(conn):
    bad_pl_df = pd.DataFrame(
        [
            {
                "company_id": "GHOST",  # does not exist in companies
                "year": "2023-03",
                "sales": 100,
                "expenses": 50,
                "operating_profit": 50,
                "opm_percentage": 50.0,
            }
        ]
    )
    with pytest.raises(sqlite3.IntegrityError):
        insert_dataframe(conn, "profitandloss", bad_pl_df)
