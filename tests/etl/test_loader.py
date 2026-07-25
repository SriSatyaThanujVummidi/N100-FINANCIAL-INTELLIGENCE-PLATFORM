"""Day 41 -- 10 loader tests: correct row counts and column names per source file."""

import pytest
from src.etl.loader import load_all_core, load_all_supporting


@pytest.fixture(scope="module")
def core_data():
    return load_all_core()


@pytest.fixture(scope="module")
def supporting_data():
    return load_all_supporting()


def test_companies_row_count(core_data):
    assert len(core_data["companies"]) == 92


def test_companies_columns(core_data):
    assert "id" in core_data["companies"].columns
    assert "company_name" in core_data["companies"].columns


def test_profitandloss_row_count(core_data):
    assert len(core_data["profitandloss"]) == 1276


def test_profitandloss_columns(core_data):
    expected = {"company_id", "year", "sales", "operating_profit", "net_profit"}
    assert expected.issubset(set(core_data["profitandloss"].columns))


def test_balancesheet_row_count(core_data):
    assert len(core_data["balancesheet"]) == 1312


def test_cashflow_row_count(core_data):
    assert len(core_data["cashflow"]) == 1187


def test_cashflow_columns(core_data):
    expected = {
        "company_id",
        "year",
        "operating_activity",
        "investing_activity",
        "financing_activity",
    }
    assert expected.issubset(set(core_data["cashflow"].columns))


def test_documents_row_count(core_data):
    assert len(core_data["documents"]) == 1585


def test_stock_prices_row_count(supporting_data):
    assert len(supporting_data["stock_prices"]) == 5520


def test_sectors_columns(supporting_data):
    expected = {"company_id", "broad_sector", "sub_sector"}
    assert expected.issubset(set(supporting_data["sectors"].columns))
