"""Edge-case tests for challenges.py."""

import challenges


def test_clean_handles_malformed_and_edge_inputs():
    # None and non-dict inputs return default empty state
    assert challenges.clean(None) == challenges.empty_state()
    assert challenges.clean([]) == challenges.empty_state()
    assert challenges.clean("active") == challenges.empty_state()

    # Valid empty dict
    assert challenges.clean({}) == challenges.empty_state()

    # Malformed active challenge: bad baseline type
    raw = {"active": {"id": "lean_harvest", "baseline": "not_a_number", "seasons_done": 0}}
    assert challenges.clean(raw)["active"] is None

    # Valid active challenge with correct types
    raw = {"active": {"id": "lean_harvest", "baseline": 10.0, "seasons_done": 2}}
    result = challenges.clean(raw)
    assert result["active"]["id"] == "lean_harvest"
    assert result["active"]["baseline"] == 10.0
    assert result["active"]["seasons_done"] == 2

    # Completed dict with mixed valid/invalid entries
    raw = {"completed": {"lean_harvest": 5, "bad_key": -1, "land_recovery": True}}
    result = challenges.clean(raw)
    assert result["completed"]["lean_harvest"] == 5
    assert "bad_key" not in result["completed"]
    assert "land_recovery" not in result["completed"]


def test_abandon_handles_edge_cases():
    state = type("State", (), {"challenge": challenges.empty_state()})()

    # No active challenge -> returns False, state unchanged
    assert challenges.abandon(state) is False

    # Has active challenge -> returns True, clears active
    state.challenge["active"] = {"id": "lean_harvest", "seasons_done": 1, "baseline": 5.0}
    assert challenges.abandon(state) is True
    assert state.challenge["active"] is None


def test_reward_for_scales_with_era():
    # Tribal is era_index 0 -> 4.0 + 2.0 * 0 = 4.0
    assert challenges.reward_for("tribal") == 4.0
    # Agrarian is era_index 1 -> 4.0 + 2.0 * 1 = 6.0
    assert challenges.reward_for("agrarian") == 6.0
    # Industrial is era_index 4 -> 4.0 + 2.0 * 4 = 12.0
    assert challenges.reward_for("industrial") == 12.0
