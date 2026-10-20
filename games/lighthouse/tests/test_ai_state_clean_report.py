"""Tests for state.clean_report()."""

from state import clean_report
import lore


def test_clean_report_with_valid_data():
    """A normal report with valid keys and types passes through unchanged."""
    valid_letter_id = list(lore.LETTERS.keys())[0]
    raw = {
        "night": 5,
        "summary": "A calm night.",
        "ships": [
            {"name": "The Wanderer", "kind": "ferry", "outcome": "passed"},
            {"name": "Old Bob", "kind": "cargo", "outcome": "delayed"},
        ],
        "lamp_hours": 12.5,
        "oil_used": 8.0,
        "damage": 2,
        "incidents": 1,
        "rep": 3,
        "salvage": 10,
        "passed": 1,
        "delayed": 1,
        "damaged": 0,
        "worst": 2,
        "quiet": True,
        "lines": ["Ship passed.", "Oil used: 8."],
        "letters": [
            {"id": valid_letter_id, "from_name": "Sailor", "subject": "Hello"},
        ],
        "beats": [
            {"kind": "odd", "text": "A strange light."},
        ],
    }
    result = clean_report(raw)
    assert result is not None
    assert result["night"] == 5
    assert result["summary"] == "A calm night."
    assert len(result["ships"]) == 2
    assert result["ships"][0]["name"] == "The Wanderer"
    assert result["lamp_hours"] == 12.5
    assert result["oil_used"] == 8.0
    assert result["worst"] == 2
    assert result["quiet"] is True
    assert len(result["lines"]) == 2
    assert len(result["letters"]) == 1
    assert result["letters"][0]["id"] == valid_letter_id
    assert len(result["beats"]) == 1


def test_clean_report_clamps_and_filters_invalid_data():
    """Out-of-range numbers are clamped, invalid types are dropped, and defaults are used."""
    raw = {
        "night": -5,
        "summary": "A" * 400,
        "ships": [{"name": "X", "kind": "Y", "outcome": "invalid_outcome"}],
        "lamp_hours": -10,
        "oil_used": 200000,
        "damage": -5000,
        "worst": 10,
        "quiet": False,
        "lines": [123, "valid line", None],
        "letters": [{"id": "invalid_id", "from_name": "X", "subject": "Y"}],
        "beats": [{"kind": "bad_kind", "text": "Z"}],
    }
    result = clean_report(raw)
    assert result["night"] == 1  # clamped to min 1
    assert len(result["summary"]) == 300  # truncated
    assert result["ships"][0]["outcome"] == "passed"  # default
    assert result["lamp_hours"] == 0.0  # clamped to min 0
    assert result["oil_used"] == 100000.0  # clamped to max 100000
    assert result["damage"] == -1000  # clamped to min -1000
    assert result["worst"] == 4  # clamped to max 4
    assert result["quiet"] is False
    assert len(result["lines"]) == 1  # only "valid line" kept
    assert len(result["letters"]) == 0  # invalid_id filtered out
    assert result["beats"][0]["kind"] == "kind"  # default


def test_clean_report_handles_empty_and_none_input():
    """Missing or empty input returns None instead of crashing."""
    assert clean_report(None) is None
    assert clean_report({}) is None
