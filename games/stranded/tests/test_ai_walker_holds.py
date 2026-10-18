"""Tests for walker.holds() function."""


import walker


def test_holds_returns_true_for_none_condition():
    """holds returns True when condition is None."""
    state, _ = walker.initial()
    assert walker.holds(None, state) is True


def test_holds_all_flag_present():
    """holds returns True when all required flags are present in state."""
    state, _ = walker.initial()
    # Construct a state with a flag present
    state_with_flag = (state[0], state[1], ("bitgave",))
    assert walker.holds({"all": ["bitgave"], "none": [], "min": {}, "max": {}}, state_with_flag) is True


def test_holds_min_stat_met():
    """holds returns True when minimum stat requirement is met."""
    state, _ = walker.initial()
    # Construct a state with trust >= 5
    state_high_trust = (state[0], (5, 0, 0), state[2])
    assert walker.holds({"all": [], "none": [], "min": {"trust": 5}, "max": {}}, state_high_trust) is True


def test_holds_edge_case_empty_none_list():
    """holds returns True for an empty 'none' list (no exclusions)."""
    state, _ = walker.initial()
    # Empty 'none' means no flags are excluded, so it should pass regardless of flags
    assert walker.holds({"all": [], "none": [], "min": {}, "max": {}}, state) is True
