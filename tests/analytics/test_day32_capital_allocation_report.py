import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.analytics.day32_capital_allocation_report import (
    latest_year_distribution,
    detect_pattern_changes,
)


def test_latest_year_distribution_picks_latest_per_company():
    rows = [
        {"company_id": "A", "year": "2022-03", "pattern_label": "Reinvestor"},
        {"company_id": "A", "year": "2024-03", "pattern_label": "Distress Signal"},
        {"company_id": "B", "year": "2024-03", "pattern_label": "Reinvestor"},
    ]
    dist = latest_year_distribution(rows)
    dist_map = {d["pattern_label"]: d["company_count"] for d in dist}
    assert dist_map["Distress Signal"] == 1
    assert dist_map["Reinvestor"] == 1


def test_detect_pattern_changes_finds_transition():
    rows = [
        {"company_id": "A", "year": "2022-03", "pattern_label": "Reinvestor"},
        {"company_id": "A", "year": "2023-03", "pattern_label": "Reinvestor"},
        {"company_id": "A", "year": "2024-03", "pattern_label": "Distress Signal"},
    ]
    changes = detect_pattern_changes(rows)
    assert len(changes) == 1
    assert changes[0]["from_pattern"] == "Reinvestor"
    assert changes[0]["to_pattern"] == "Distress Signal"
    assert changes[0]["from_year"] == "2023-03"
    assert changes[0]["to_year"] == "2024-03"


def test_detect_pattern_changes_no_change_returns_empty():
    rows = [
        {"company_id": "A", "year": "2022-03", "pattern_label": "Reinvestor"},
        {"company_id": "A", "year": "2023-03", "pattern_label": "Reinvestor"},
    ]
    assert detect_pattern_changes(rows) == []


def test_detect_pattern_changes_multiple_companies_independent():
    rows = [
        {"company_id": "A", "year": "2022-03", "pattern_label": "Reinvestor"},
        {"company_id": "A", "year": "2023-03", "pattern_label": "Distress Signal"},
        {"company_id": "B", "year": "2022-03", "pattern_label": "Shareholder Returns"},
        {"company_id": "B", "year": "2023-03", "pattern_label": "Shareholder Returns"},
    ]
    changes = detect_pattern_changes(rows)
    assert len(changes) == 1
    assert changes[0]["company_id"] == "A"
