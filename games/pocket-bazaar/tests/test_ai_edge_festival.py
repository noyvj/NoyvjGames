import pytest
import festival


def test_for_day_handles_zero_and_negative_numbers():
    """for_day uses modulo, so zero and negative inputs wrap around predictably."""
    assert festival.for_day(0) == "bargain"
    assert festival.for_day(-5) == "slow"


def test_for_day_handles_very_large_day_numbers():
    """Large day numbers are reduced by modulo without error."""
    large = 10**9
    expected = festival.for_day((large - 1) % 6 + 1)
    assert festival.for_day(large) == expected


def test_info_rejects_unknown_festival_ids():
    """info looks up the FESTIVALS table and raises KeyError for unknown ids."""
    with pytest.raises(KeyError):
        festival.info("nonexistent")


def test_apply_spec_raises_on_missing_slack_pct():
    """apply_spec requires spec to contain 'slack_pct' and raises KeyError if absent."""
    with pytest.raises(KeyError):
        festival.apply_spec({}, "slow")


def test_day_rules_filters_correctly_for_twin():
    """day_rules only includes keys present in the loop and present in the festival dict."""
    rules = festival.day_rules("twin")
    assert rules == {"twin": True}


def test_apply_spec_does_not_mutate_input_spec():
    """apply_spec returns a new dict and leaves the original spec unchanged."""
    spec = {"slack_pct": 100, "archetypes": [("regular", 1)]}
    out = festival.apply_spec(spec, "twin")
    assert out is not spec
    assert out["slack_pct"] == 100
    assert spec["slack_pct"] == 100
