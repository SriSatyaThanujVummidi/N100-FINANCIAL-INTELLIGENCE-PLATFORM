import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.etl.fiscal_calendar import get_dominant_fiscal_month, get_annual_rows


def _make_test_db(db_dir: Path) -> sqlite3.Connection:
    db_path = db_dir / "test.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE balancesheet (company_id TEXT, year TEXT, borrowings REAL)"
    )
    conn.executemany(
        "INSERT INTO balancesheet VALUES (?, ?, ?)",
        [
            ("MARCHCO", "2022-03", 500),
            ("MARCHCO", "2023-03", 400),
            ("MARCHCO", "2024-03", 300),
            ("MARCHCO", "2024-09", 250),  # off-cycle interim row
            ("SEPCO", "2022-09", 100),
            ("SEPCO", "2023-09", 90),
            ("SEPCO", "2024-09", 80),
        ],
    )
    conn.commit()
    return conn


def test_get_dominant_fiscal_month_march(tmp_path):
    conn = _make_test_db(tmp_path)
    assert get_dominant_fiscal_month(conn, "MARCHCO", "balancesheet") == "03"


def test_get_dominant_fiscal_month_september(tmp_path):
    conn = _make_test_db(tmp_path)
    assert get_dominant_fiscal_month(conn, "SEPCO", "balancesheet") == "09"


def test_get_dominant_fiscal_month_no_rows_returns_none(tmp_path):
    conn = _make_test_db(tmp_path)
    assert get_dominant_fiscal_month(conn, "GHOSTCO", "balancesheet") is None


def test_get_annual_rows_excludes_offcycle_row(tmp_path):
    conn = _make_test_db(tmp_path)
    rows = get_annual_rows(conn, "MARCHCO", "balancesheet", "year, borrowings")
    years = [r["year"] for r in rows]
    assert "2024-09" not in years
    assert years == ["2024-03", "2023-03", "2022-03"]


def test_get_annual_rows_respects_limit(tmp_path):
    conn = _make_test_db(tmp_path)
    rows = get_annual_rows(conn, "MARCHCO", "balancesheet", "year, borrowings", limit=2)
    assert len(rows) == 2
    assert rows[0]["year"] == "2024-03"
    assert rows[1]["year"] == "2023-03"


def test_get_annual_rows_pure_september_company_unaffected(tmp_path):
    conn = _make_test_db(tmp_path)
    rows = get_annual_rows(conn, "SEPCO", "balancesheet", "year, borrowings", limit=2)
    years = [r["year"] for r in rows]
    assert years == ["2024-09", "2023-09"]


def test_get_annual_rows_no_data_returns_empty(tmp_path):
    conn = _make_test_db(tmp_path)
    assert get_annual_rows(conn, "GHOSTCO", "balancesheet", "year, borrowings") == []
