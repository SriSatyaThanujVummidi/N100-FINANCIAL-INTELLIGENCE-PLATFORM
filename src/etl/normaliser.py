"""Normalisation helpers for year labels and company tickers."""

from __future__ import annotations

import re

# Known ticker typos found in specific source files, mapped here rather than
# editing data/raw/ (which must stay untouched). Add new entries as they're
# discovered.
TICKER_CORRECTIONS = {
    "AGTL": "ATGL",  # cashflow.xlsx — transposed letters; correct ticker is ATGL (Adani Total Gas Ltd)
}

MONTH_MAP = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "sept": "09",
    "september": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
}


def _expand_year(yy: str) -> str:
    """Expand a 2-digit year to 4 digits (assumes 2000s)."""
    if len(yy) == 4:
        return yy
    return f"20{yy}"


def normalize_year(raw_value) -> str:
    """Normalise a raw FY label to 'YYYY-MM'. Raises ValueError if unparseable."""
    if raw_value is None:
        raise ValueError(f"Cannot parse year: {raw_value!r}")

    text = str(raw_value).strip()
    if not text:
        raise ValueError(f"Cannot parse year: {raw_value!r}")

    # TTM = "trailing twelve months" — a rolling window, not a fiscal year-end.
    # Pass it through unchanged so callers can decide how to treat it
    # (the validator excludes TTM rows from annual time-series tables).
    if text.upper() == "TTM":
        return "TTM"

    # Already normalised: 2023-03
    m = re.match(r"^(\d{4})-(\d{2})$", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}"

    # FY prefix: FY23, FY2023
    m = re.match(r"^FY\s*(\d{2,4})$", text, re.IGNORECASE)
    if m:
        return f"{_expand_year(m.group(1))}-03"

    # Month name/abbrev + separator + year, optionally followed by a
    # stub-period duration suffix, e.g. "Mar 2016 9m" or "Mar 2023 15".
    # Companies sometimes report a short/long stub period when they change
    # their fiscal year-end date. We keep the FY-end month/year and drop the
    # duration suffix (it doesn't affect the (company_id, year) join key,
    # though it does mean that particular year isn't a clean 12-month period).
    m = re.match(r"^([A-Za-z]+)[\s\-]?(\d{2,4})(?:\s+\d+m?)?$", text)
    if m:
        month_key = m.group(1).lower()
        if month_key in MONTH_MAP:
            return f"{_expand_year(m.group(2))}-{MONTH_MAP[month_key]}"

    # Decimal-year artifact, e.g. "2024.5" — take the integer part.
    m = re.match(r"^(\d{4})\.\d+$", text)
    if m:
        return f"{m.group(1)}-03"

    # Plain 4-digit year -> assume March FY close
    m = re.match(r"^(\d{4})$", text)
    if m:
        return f"{m.group(1)}-03"

    raise ValueError(f"Cannot parse year: {raw_value!r}")


def normalize_ticker(raw_value) -> str:
    """Strip whitespace, upper-case, and correct known typos. Raises ValueError if missing/empty."""
    if raw_value is None:
        raise ValueError("Ticker is missing")

    text = str(raw_value).strip()
    if not text or text.upper() == "MISSING":
        raise ValueError("Ticker is missing")

    ticker = text.upper()
    return TICKER_CORRECTIONS.get(ticker, ticker)
