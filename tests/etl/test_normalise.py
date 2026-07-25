import pytest
from etl.normaliser import normalize_ticker, normalize_year


class TestNormalizeYear:
    def test_mar_23(self):
        assert normalize_year("Mar-23") == "2023-03"

    def test_mar_space_23(self):
        assert normalize_year("Mar 23") == "2023-03"

    def test_march_full_name(self):
        assert normalize_year("March-2023") == "2023-03"

    def test_plain_4digit_year(self):
        assert normalize_year("2023") == "2023-03"

    def test_fy_prefix_2digit(self):
        assert normalize_year("FY23") == "2023-03"

    def test_fy_prefix_4digit(self):
        assert normalize_year("FY2023") == "2023-03"

    def test_dec_year_end(self):
        assert normalize_year("Dec-22") == "2022-12"

    def test_jun_year_end(self):
        assert normalize_year("Jun-23") == "2023-06"

    def test_already_normalized_passthrough(self):
        assert normalize_year("2023-03") == "2023-03"

    def test_jan(self):
        assert normalize_year("Jan-24") == "2024-01"

    def test_feb(self):
        assert normalize_year("Feb-21") == "2021-02"

    def test_apr(self):
        assert normalize_year("Apr-20") == "2020-04"

    def test_may(self):
        assert normalize_year("May-19") == "2019-05"

    def test_jul(self):
        assert normalize_year("Jul-22") == "2022-07"

    def test_aug(self):
        assert normalize_year("Aug-23") == "2023-08"

    def test_sep(self):
        assert normalize_year("Sep-23") == "2023-09"

    def test_oct(self):
        assert normalize_year("Oct-23") == "2023-10"

    def test_nov(self):
        assert normalize_year("Nov-23") == "2023-11"

    def test_strips_whitespace(self):
        assert normalize_year("  Mar-23  ") == "2023-03"

    def test_no_separator(self):
        assert normalize_year("Mar23") == "2023-03"

    def test_garbage_raises(self):
        with pytest.raises(ValueError):
            normalize_year("garbage")

    def test_none_raises(self):
        with pytest.raises(ValueError):
            normalize_year(None)

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            normalize_year("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            normalize_year("   ")

    def test_ttm_passthrough(self):
        assert normalize_year("TTM") == "TTM"

    def test_ttm_lowercase(self):
        assert normalize_year("ttm") == "TTM"

    def test_stub_period_9m(self):
        assert normalize_year("Mar 2016 9m") == "2016-03"

    def test_stub_period_15(self):
        assert normalize_year("Mar 2023 15") == "2023-03"

    def test_decimal_year(self):
        assert normalize_year("2024.5") == "2024-03"


class TestNormalizeTicker:
    def test_already_upper(self):
        assert normalize_ticker("TCS") == "TCS"

    def test_lowercase(self):
        assert normalize_ticker("tcs") == "TCS"

    def test_strips_whitespace(self):
        assert normalize_ticker("  TCS  ") == "TCS"

    def test_hyphen_preserved(self):
        assert normalize_ticker("BAJAJ-AUTO") == "BAJAJ-AUTO"

    def test_hyphen_preserved_lowercase(self):
        assert normalize_ticker("bajaj-auto") == "BAJAJ-AUTO"

    def test_ampersand_preserved(self):
        assert normalize_ticker("M&M") == "M&M"

    def test_ampersand_preserved_lowercase(self):
        assert normalize_ticker("m&m") == "M&M"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            normalize_ticker("")

    def test_none_raises(self):
        with pytest.raises(ValueError):
            normalize_ticker(None)

    def test_missing_literal_raises(self):
        with pytest.raises(ValueError):
            normalize_ticker("MISSING")

    def test_mixed_case(self):
        assert normalize_ticker("Tcs") == "TCS"

    def test_ampersand_with_spaces(self):
        assert normalize_ticker(" m&m ") == "M&M"

    def test_hyphenated_mixed_case(self):
        assert normalize_ticker("tata-motors") == "TATA-MOTORS"

    def test_trailing_space(self):
        assert normalize_ticker("INFY ") == "INFY"

    def test_tabs_and_newlines(self):
        assert normalize_ticker("\tTCS\n") == "TCS"

    def test_known_typo_correction(self):
        assert normalize_ticker("AGTL") == "ATGL"

    def test_known_typo_correction_lowercase(self):
        assert normalize_ticker("agtl") == "ATGL"
