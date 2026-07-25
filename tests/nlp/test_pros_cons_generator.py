import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.nlp.pros_cons_generator import (
    is_implausible_pct,
    scaled_confidence,
    pro01_roe_sustained,
    pro03_debt_free_latest,
    con01_high_de_nonfinancial,
    con04_net_loss_latest,
    generate_for_company,
)


def test_is_implausible_pct_flags_extreme():
    assert is_implausible_pct(600.0) is True
    assert is_implausible_pct(-600.0) is True


def test_is_implausible_pct_allows_normal():
    assert is_implausible_pct(25.0) is False
    assert is_implausible_pct(None) is False


def test_scaled_confidence_at_threshold():
    assert scaled_confidence(0, scale=10) == 60.0


def test_scaled_confidence_at_full_scale():
    assert scaled_confidence(10, scale=10) == 100.0


def test_scaled_confidence_beyond_scale_caps_at_100():
    assert scaled_confidence(50, scale=10) == 100.0


def test_pro01_roe_sustained_triggers():
    ctx = {
        "fr": [
            {"return_on_equity_pct": 22.0},
            {"return_on_equity_pct": 25.0},
            {"return_on_equity_pct": 30.0},
        ]
    }
    result = pro01_roe_sustained(ctx)
    assert result is not None
    assert result[1] > 60


def test_pro01_roe_sustained_masks_implausible():
    ctx = {
        "fr": [
            {"return_on_equity_pct": 22.0},
            {"return_on_equity_pct": 25.0},
            {"return_on_equity_pct": 900.0},
        ]
    }
    assert pro01_roe_sustained(ctx) is None


def test_pro01_roe_sustained_insufficient_history():
    ctx = {"fr": [{"return_on_equity_pct": 25.0}]}
    assert pro01_roe_sustained(ctx) is None


def test_pro03_debt_free_triggers():
    ctx = {"fr": [{"debt_to_equity": 0}]}
    result = pro03_debt_free_latest(ctx)
    assert result is not None
    assert result[1] == 85.0


def test_con01_de_high_nonfinancial_triggers():
    ctx = {"sector": "Materials", "fr": [{"debt_to_equity": 4.0}]}
    result = con01_high_de_nonfinancial(ctx)
    assert result is not None
    assert "4.00" in result[0]


def test_con01_de_high_financials_excluded():
    ctx = {"sector": "Financials", "fr": [{"debt_to_equity": 6.0}]}
    assert con01_high_de_nonfinancial(ctx) is None


def test_con04_net_loss_triggers():
    ctx = {"pl": [{"net_profit": -100.0}]}
    result = con04_net_loss_latest(ctx)
    assert result is not None
    assert result[1] == 90.0


def test_con04_net_profit_positive_no_trigger():
    ctx = {"pl": [{"net_profit": 100.0}]}
    assert con04_net_loss_latest(ctx) is None


def _make_sparse_db(tmp_path):
    """A company with almost no usable data — should hit NODATA_FALLBACK
    for both pro and con, not crash."""
    db_path = tmp_path / "sparse.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE companies (id TEXT)")
    conn.execute(
        "CREATE TABLE financial_ratios (company_id TEXT, year TEXT, net_profit_margin_pct REAL, operating_profit_margin_pct REAL, return_on_equity_pct REAL, return_on_capital_employed_pct REAL, debt_to_equity REAL, interest_coverage REAL, free_cash_flow_cr REAL, dividend_payout_ratio_pct REAL, revenue_cagr_5yr REAL, pat_cagr_5yr REAL, eps_cagr_5yr REAL, total_debt_cr REAL, cash_from_operations_cr REAL)"
    )
    conn.execute(
        "CREATE TABLE profitandloss (company_id TEXT, year TEXT, sales REAL, net_profit REAL, eps REAL, operating_profit REAL)"
    )
    conn.execute(
        "CREATE TABLE balancesheet (company_id TEXT, year TEXT, total_assets REAL, borrowings REAL, investments REAL, other_asset REAL)"
    )
    conn.execute(
        "CREATE TABLE market_cap (company_id TEXT, year TEXT, dividend_yield_pct REAL)"
    )
    conn.execute("CREATE TABLE sectors (company_id TEXT, broad_sector TEXT)")
    conn.execute("INSERT INTO companies VALUES ('SPARSECO')")
    conn.commit()
    return conn


def test_generate_for_company_nodata_fallback_no_crash(tmp_path):
    conn = _make_sparse_db(tmp_path)
    rows = generate_for_company(conn, "SPARSECO")
    types = {r["type"] for r in rows}
    assert types == {"pro", "con"}
    assert all(r["rule_id"] == "NODATA_FALLBACK" for r in rows)


def test_con11_excludes_financials():
    ctx = {
        "sector": "Financials",
        "bs": [{"borrowings": 100, "investments": 5000000, "other_asset": 5000000}],
        "pl": [{"operating_profit": 100}],
    }
    from src.nlp.pros_cons_generator import con11_net_debt_ebitda

    assert con11_net_debt_ebitda(ctx) is None


def test_con11_triggers_for_nonfinancial_high_leverage():
    ctx = {
        "sector": "Energy",
        "bs": [{"borrowings": 50000, "investments": 1000, "other_asset": 1000}],
        "pl": [{"operating_profit": 5000}],
    }
    from src.nlp.pros_cons_generator import con11_net_debt_ebitda

    result = con11_net_debt_ebitda(ctx)
    assert result is not None
