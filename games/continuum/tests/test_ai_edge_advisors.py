"""Edge-case tests for advisors.py: empty/zero input, min/max bounds, and rejection/clamping."""


import advisors


def test_clean_handles_empty_and_zero_input():
    """Tests clean() with None, empty dict, empty list, and zeroed fields."""
    assert advisors.clean(None) == advisors.fresh()
    assert advisors.clean({}) == advisors.fresh()
    assert advisors.clean([]) == advisors.fresh()
    assert advisors.clean({"season": 0, "trust": {}, "record": {}}) == advisors.fresh()


def test_clean_clamps_trust_and_record_counts_to_bounds():
    """Tests clean() clamping season, trust, and record counts to their min/max limits."""
    raw = {
        "season": 10**9,
        "trust": {a: -5 for a in advisors.ORDER},
        "record": {a: {"followed": 10**7, "ignored": -10} for a in advisors.ORDER},
    }
    out = advisors.clean(raw)
    assert out["season"] == 10**7
    for a in advisors.ORDER:
        assert out["trust"][a] == 0
        assert out["record"][a]["followed"] == 10**6
        assert out["record"][a]["ignored"] == 0


def test_clean_rejects_invalid_types_for_int_fields():
    """Tests clean() rejecting floats, bools, strings, and None for integer fields."""
    raw = {
        "season": 3.5,
        "trust": {"marit": True, "teodor": "fast"},
        "record": {"ines": "not a dict", "okoro": {"followed": None}},
    }
    out = advisors.clean(raw)
    assert out["season"] == 0
    assert out["trust"]["marit"] == 5
    assert out["trust"]["teodor"] == 5
    assert out["record"]["ines"]["followed"] == 0
    assert out["record"]["okoro"]["followed"] == 0


def test_get_returns_fresh_when_key_missing_or_ui_not_dict():
    """Tests get() falling back to fresh() when ui is not a dict or key is missing."""
    ui = {}
    assert advisors.get(ui) == advisors.fresh()
    ui["advisors"] = "garbage"
    assert advisors.get(ui) == advisors.fresh()
    ui["advisors"] = 123
    assert advisors.get(ui) == advisors.fresh()


def test_put_clamps_values_and_validates_structure():
    """Tests put() clamping out-of-bounds trust and record counts on write."""
    ui = {}
    record = {
        "season": 0,
        "advice": [{"id": "marit", "action": {"type": "assign", "role": "farmers"}, "text": "x"}],
        "trust": {a: -5 for a in advisors.ORDER},
        "record": {a: {"followed": 10**7} for a in advisors.ORDER},
        "history": [{"id": "marit", "text": "y", "season": 1}],
    }
    advisors.put(ui, record)
    assert ui["advisors"]["trust"]["marit"] == 0
    assert ui["advisors"]["record"]["marit"]["followed"] == 10**6


def test_trust_text_handles_bounds_and_zero():
    """Tests trust_text() rendering correctly at zero and maximum bounds."""
    assert advisors.trust_text(0) == "Trust ○○○○○○○○○○ 0 of 10"
    assert advisors.trust_text(10) == "Trust ●●●●●●●●●● 10 of 10"
    assert advisors.trust_text(5) == "Trust ●●●●●○○○○○ 5 of 10"


def test_stale_detects_season_mismatch():
    """Tests stale() returning True on season mismatch and False on match."""
    class MockState:
        season = 5

    ui = {"advisors": {"season": 4}}
    assert advisors.stale(ui, MockState()) is True
    ui["advisors"]["season"] = 5
    assert advisors.stale(ui, MockState()) is False
