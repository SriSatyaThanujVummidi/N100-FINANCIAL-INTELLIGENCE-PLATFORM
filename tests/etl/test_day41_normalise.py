"""Day 41 -- 20 normalize_year tests covering documented real-world format variants."""

import pytest
from src.etl.normaliser import normalize_year, normalize_ticker


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Mar-23", "2023-03"),
        ("Mar 23", "2023-03"),
        ("March-2023", "2023-03"),
        ("2023", "2023-03"),
        ("FY23", "2023-03"),
        ("Dec-22", "2022-12"),
        ("Jun-23", "2023-06"),
        ("2023-03", "2023-03"),
        ("Mar-09", "2009-03"),
        ("Mar-24", "2024-03"),
    ],
)
def test_normalize_year_valid(raw, expected):
    assert normalize_year(raw) == expected


def test_normalize_year_garbage():
    with pytest.raises(ValueError):
        normalize_year("garbage")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("TCS", "TCS"),
        ("tcs", "TCS"),
        (" TCS ", "TCS"),
        ("BAJAJ-AUTO", "BAJAJ-AUTO"),
        ("M&M", "M&M"),
    ],
)
def test_normalize_ticker(raw, expected):
    assert normalize_ticker(raw) == expected
