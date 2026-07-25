import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.analytics.cashflow_intelligence import (
    cfo_quality_label,
    capex_label,
    shift_fiscal_year,
    compute_cfo_quality,
    compute_capex_intensity,
    compute_fcf_5yr_cagr,
    compute_distress_and_deleveraging,
)


def test_cfo_quality_label_high():
    assert cfo_quality_label(1.5) == "High Quality"


def test_cfo_quality_label_moderate():
    assert cfo_quality_label(0.7) == "Moderate"


def test_cfo_quality_label_boundary_low():
    assert cfo_quality_label(0.5) == "Moderate"


def test_cfo_quality_label_accrual_risk():
    assert cfo_quality_label(0.3) == "Accrual Risk"


def test_cfo_quality_label_none():
    assert cfo_quality_label(None) is None


def test_capex_label_asset_light():
    assert capex_label(2.0) == "Asset Light"


def test_capex_label_moderate_boundary():
    assert capex_label(3.0) == "Moderate"
    assert capex_label(8.0) == "Moderate"


def test_capex_label_capital_intensive():
    assert capex_label(9.0) == "Capital Intensive"


def test_shift_fiscal_year():
    assert shift_fiscal_year("2024-03", 5) == "2019-03"


def _make_test_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE cashflow (company_id TEXT, year TEXT, operating_activity REAL, investing_activity REAL, financing_activity REAL)"
    )
    conn.execute(
        "CREATE TABLE profitandloss (company_id TEXT, year TEXT, sales REAL, net_profit REAL, operating_profit REAL)"
    )
    conn.execute(
        "CREATE TABLE balancesheet (company_id TEXT, year TEXT, borrowings REAL)"
    )
    conn.executemany(
        "INSERT INTO cashflow VALUES (?, ?, ?, ?, ?)",
        [
            ("GOODCO", "2019-03", 100.0, -20.0, -30.0),
            ("GOODCO", "2024-03", 200.0, -40.0, -50.0),
            ("DISTRESSCO", "2024-03", -50.0, -10.0, 80.0),
            ("DELEVCO", "2024-03", 100.0, -20.0, -30.0),
        ],
    )
    conn.executemany(
        "INSERT INTO profitandloss VALUES (?, ?, ?, ?, ?)",
        [
            ("GOODCO", "2019-03", 500.0, 50.0, 80.0),
            ("GOODCO", "2024-03", 900.0, 90.0, 150.0),
        ],
    )
    conn.executemany(
        "INSERT INTO balancesheet VALUES (?, ?, ?)",
        [
            ("DELEVCO", "2023-03", 500.0),
            ("DELEVCO", "2024-03", 300.0),
        ],
    )
    conn.commit()
    return conn


def test_compute_cfo_quality_normal(tmp_path):
    conn = _make_test_db(tmp_path)
    score, label = compute_cfo_quality(conn, "GOODCO")
    assert score is not None
    assert label in {"High Quality", "Moderate", "Accrual Risk"}


def test_compute_cfo_quality_no_data(tmp_path):
    conn = _make_test_db(tmp_path)
    score, label = compute_cfo_quality(conn, "GHOSTCO")
    assert score is None and label is None


def test_compute_capex_intensity_normal(tmp_path):
    conn = _make_test_db(tmp_path)
    pct, label = compute_capex_intensity(conn, "GOODCO")
    assert pct is not None
    assert abs(pct - (40.0 / 900.0 * 100)) < 0.01


def test_compute_fcf_5yr_cagr_normal(tmp_path):
    conn = _make_test_db(tmp_path)
    result = compute_fcf_5yr_cagr(conn, "GOODCO")
    # base FCF = 100-20=80, end FCF = 200-40=160 -> CAGR = 2^(1/5)-1 ~ 14.87%
    assert result is not None
    assert abs(result - 14.87) < 0.1


def test_compute_distress_flag_triggers(tmp_path):
    conn = _make_test_db(tmp_path)
    distress, deleveraging, cfo, cff, net_profit = compute_distress_and_deleveraging(
        conn, "DISTRESSCO"
    )
    assert distress is True


def test_compute_deleveraging_flag_triggers(tmp_path):
    conn = _make_test_db(tmp_path)
    distress, deleveraging, cfo, cff, net_profit = compute_distress_and_deleveraging(
        conn, "DELEVCO"
    )
    assert deleveraging is True


def test_compute_distress_missing_company_returns_none(tmp_path):
    conn = _make_test_db(tmp_path)
    distress, deleveraging, cfo, cff, net_profit = compute_distress_and_deleveraging(
        conn, "GHOSTCO"
    )
    assert distress is None and deleveraging is None


def test_compute_distress_missing_company_returns_five_values(tmp_path):
    conn = _make_test_db(tmp_path)
    result = compute_distress_and_deleveraging(conn, "GHOSTCO")
    assert len(result) == 5
    assert result == (None, None, None, None, None)


def test_compute_distress_excludes_financials(tmp_path):
    conn = _make_test_db(tmp_path)
    distress, deleveraging, cfo, cff, net_profit = compute_distress_and_deleveraging(
        conn, "DISTRESSCO", sector="Financials"
    )
    assert distress is None  # would be True without the carve-out


def test_compute_distress_still_triggers_for_nonfinancials(tmp_path):
    conn = _make_test_db(tmp_path)
    distress, deleveraging, cfo, cff, net_profit = compute_distress_and_deleveraging(
        conn, "DISTRESSCO", sector="Industrials"
    )
    assert distress is True
