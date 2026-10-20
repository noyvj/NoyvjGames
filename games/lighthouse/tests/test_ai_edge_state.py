"""Edge-case tests for state.py public functions."""

from state import num, text, clean_seed_text, pick_one, clean_order, clean_report


def test_num_clamps_to_bounds():
    """num clamps values outside [lo, hi] to the bounds."""
    assert num(-10, 0, 10, 5) == 0
    assert num(20, 0, 10, 5) == 10


def test_num_returns_default_for_invalid_types():
    """num returns default for booleans, strings, None, etc."""
    assert num(True, 0, 10, 5) == 5
    assert num("5", 0, 10, 5) == 5
    assert num(None, 0, 10, 5) == 5


def test_num_handles_floats_correctly():
    """num rounds floats to int unless integer=False."""
    assert num(3.6, 0, 10, 0) == 4
    assert num(3.6, 0, 10, 0, integer=False) == 3.6


def test_text_truncates_to_limit():
    """text truncates strings longer than limit."""
    long_str = "a" * 250
    assert len(text(long_str, 200, "")) == 200


def test_text_returns_default_for_non_strings():
    """text returns default for non-string inputs."""
    assert text(123, 200, "default") == "default"
    assert text(None, 200, "default") == "default"


def test_clean_seed_text_validates_format():
    """clean_seed_text accepts valid LIGHTHOUSE-XXXXXX format and rejects invalid."""
    assert clean_seed_text("LIGHTHOUSE-ABCDE") == "LIGHTHOUSE-ABCDE"  # exactly 16 chars total
    assert clean_seed_text("") == ""
    assert clean_seed_text("LIGHTHOUSE-ABCD") == ""  # too short (15)
    assert clean_seed_text("LIGHTHOUSE-ABCDEF") == ""  # too long (17)
    assert clean_seed_text("BADPREFIX-ABCDE") == ""
    assert clean_seed_text("LIGHTHOUSE-1BCDE") == ""  # invalid char '1'


def test_pick_one_returns_matching_or_default():
    """pick_one returns the value if it's in choices, else default."""
    assert pick_one("a", ("a", "b"), "x") == "a"
    assert pick_one("c", ("a", "b"), "x") == "x"
    assert pick_one(123, ("a", "b"), "x") == "x"


def test_clean_order_validates_sum_and_values():
    """clean_order returns default order if sum != BOAT_CRATES or values are negative."""
    from data import BOAT_CRATES, DEFAULT_ORDER

    # Sum is wrong (60 instead of 12)
    valid = {k: BOAT_CRATES for k in ("oil", "food", "timber", "tar", "glass")}
    assert clean_order(valid) == DEFAULT_ORDER

    # Negative values get clamped to 0 by num, making sum < BOAT_CRATES
    raw = {"oil": -5, "food": 2, "timber": 3, "tar": 3, "glass": 3}
    assert clean_order(raw) == DEFAULT_ORDER


def test_clean_report_clamps_and_limits():
    """clean_report clamps numeric fields and limits list lengths."""
    raw = {
        "night": -100,
        "summary": "x" * 500,
        "ships": [{"name": "A", "kind": "B", "outcome": "passed"}] * 20,
        "lamp_hours": -1000,
        "oil_used": -1000,
        "damage": -1000,
        "lines": ["line"] * 20,
    }
    report = clean_report(raw)
    assert report["night"] == 1
    assert len(report["summary"]) == 300
    assert len(report["ships"]) == 8
    assert report["lamp_hours"] == 0.0
    assert len(report["lines"]) == 10
