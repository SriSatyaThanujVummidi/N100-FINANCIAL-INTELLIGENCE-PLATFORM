import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.reports.tearsheet import (
    is_implausible_pct,
    get_kpi_tiles,
    chart_revenue_np,
    chart_roe_roce,
    chart_bs_composition,
    chart_cf_waterfall,
)


def test_is_implausible_pct():
    assert is_implausible_pct(600.0) is True
    assert is_implausible_pct(25.0) is False


def test_get_kpi_tiles_no_data():
    tiles = get_kpi_tiles({"fr": []})
    assert len(tiles) == 6
    assert all(v == "—" for _, v in tiles)


def test_get_kpi_tiles_masks_implausible_roe():
    data = {
        "fr": [
            {
                "return_on_equity_pct": 900.0,
                "return_on_capital_employed_pct": 15.0,
                "debt_to_equity": 0.5,
                "operating_profit_margin_pct": 20.0,
                "revenue_cagr_5yr": 10.0,
                "free_cash_flow_cr": 500.0,
            }
        ]
    }
    tiles = dict(get_kpi_tiles(data))
    assert tiles["ROE"] == "N/A"
    assert tiles["ROCE"] == "15.0%"


def test_get_kpi_tiles_normal_values():
    data = {
        "fr": [
            {
                "return_on_equity_pct": 25.0,
                "return_on_capital_employed_pct": 20.0,
                "debt_to_equity": 0.3,
                "operating_profit_margin_pct": 22.0,
                "revenue_cagr_5yr": 12.0,
                "free_cash_flow_cr": 1000.0,
            }
        ]
    }
    tiles = dict(get_kpi_tiles(data))
    assert tiles["ROE"] == "25.0%"
    assert tiles["D/E"] == "0.30x"


def test_chart_revenue_np_insufficient_data_returns_none(tmp_path):
    data = {
        "company_id": "TESTCO",
        "pl": [{"year": "2024-03", "sales": 100, "net_profit": 10}],
    }
    assert chart_revenue_np(data, tmp_path) is None


def test_chart_revenue_np_renders_with_enough_data(tmp_path):
    data = {
        "company_id": "TESTCO",
        "pl": [
            {"year": "2020-03", "sales": 100, "net_profit": 10},
            {"year": "2021-03", "sales": 120, "net_profit": 12},
            {"year": "2022-03", "sales": 140, "net_profit": 15},
        ],
    }
    path = chart_revenue_np(data, tmp_path)
    assert path is not None
    assert path.exists()
    assert path.stat().st_size > 0


def test_chart_roe_roce_all_masked_returns_none(tmp_path):
    data = {
        "company_id": "TESTCO",
        "fr": [
            {
                "year": "2023-03",
                "return_on_equity_pct": 900.0,
                "return_on_capital_employed_pct": 800.0,
            },
            {
                "year": "2024-03",
                "return_on_equity_pct": 950.0,
                "return_on_capital_employed_pct": 850.0,
            },
        ],
    }
    assert chart_roe_roce(data, tmp_path) is None


def test_chart_bs_composition_insufficient_returns_none(tmp_path):
    data = {
        "company_id": "TESTCO",
        "bs": [{"year": "2024-03", "equity_capital": 10, "reserves": 100}],
    }
    assert chart_bs_composition(data, tmp_path) is None


def test_chart_cf_waterfall_no_cashflow_returns_none(tmp_path):
    data = {"company_id": "TESTCO", "cf": []}
    assert chart_cf_waterfall(data, tmp_path) is None


def test_chart_cf_waterfall_renders(tmp_path):
    data = {
        "company_id": "TESTCO",
        "cf": [
            {
                "year": "2024-03",
                "operating_activity": 100,
                "investing_activity": -40,
                "financing_activity": -30,
                "net_cash_flow": 30,
            },
        ],
    }
    path = chart_cf_waterfall(data, tmp_path)
    assert path is not None
    assert path.exists()
