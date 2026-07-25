import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.nlp.parser import extract_period_value, compute_pl_cagr, shift_fiscal_year


def test_extract_period_value_standard():
    assert extract_period_value("10 Years: 21%") == (10, 21.0)


def test_extract_period_value_no_colon():
    assert extract_period_value("5 Years 18.5%") == (5, 18.5)


def test_extract_period_value_singular_year():
    assert extract_period_value("1 Year: 4%") == (1, 4.0)


def test_extract_period_value_negative():
    assert extract_period_value("1 Year:         -2%") == (1, -2.0)


def test_extract_period_value_negative_decimal():
    assert extract_period_value("3 Years: -12.5%") == (3, -12.5)


def test_extract_period_value_no_match():
    assert extract_period_value("N/A") is None


def test_extract_period_value_garbage():
    assert extract_period_value("TTM") is None


def test_extract_period_value_ttm_text_still_fails():
    # TTM entries are genuinely not period-based text and must keep
    # failing to match — this is correct behaviour, not a regression.
    assert extract_period_value("TTM:            47%") is None


def test_extract_period_value_last_year_text_still_fails():
    assert extract_period_value("Last Year:    17%") is None


def test_shift_fiscal_year_march():
    assert shift_fiscal_year("2024-03", 5) == "2019-03"


def test_shift_fiscal_year_september():
    assert shift_fiscal_year("2024-09", 3) == "2021-09"


def _make_test_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE profitandloss (company_id TEXT, year TEXT, sales REAL, net_profit REAL)"
    )
    conn.executemany(
        "INSERT INTO profitandloss VALUES (?, ?, ?, ?)",
        [
            ("TESTCO", "2019-03", 100.0, 10.0),
            ("TESTCO", "2024-03", 200.0, 20.0),
            ("ZEROCO", "2019-03", 0.0, 5.0),
            ("ZEROCO", "2024-03", 50.0, 10.0),
            ("TURNCO", "2019-03", -50.0, -5.0),
            ("TURNCO", "2024-03", 100.0, 10.0),
        ],
    )
    conn.commit()
    return conn


def test_compute_pl_cagr_normal(tmp_path):
    conn = _make_test_db(tmp_path)
    result = compute_pl_cagr(conn, "TESTCO", "sales", 5)
    assert result is not None
    assert abs(result - 14.87) < 0.1  # (200/100)^(1/5)-1 ≈ 14.87%


def test_compute_pl_cagr_zero_base(tmp_path):
    conn = _make_test_db(tmp_path)
    assert compute_pl_cagr(conn, "ZEROCO", "sales", 5) is None


def test_compute_pl_cagr_turnaround(tmp_path):
    conn = _make_test_db(tmp_path)
    assert compute_pl_cagr(conn, "TURNCO", "net_profit", 5) is None


def test_compute_pl_cagr_missing_company(tmp_path):
    conn = _make_test_db(tmp_path)
    assert compute_pl_cagr(conn, "GHOST", "sales", 5) is None
