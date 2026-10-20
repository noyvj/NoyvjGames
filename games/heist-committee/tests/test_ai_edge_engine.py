import engine


def test_roll_determinism_and_boundaries():
    """roll(seed, *keys) must be deterministic and return values in [0, 1)."""
    r1 = engine.roll(0, "a", "b")
    r2 = engine.roll(0, "a", "b")
    assert r1 == r2
    assert 0 <= r1 < 1

    # Large seed and many keys should still work without error
    r_large = engine.roll(2**31 - 1, "k1", "k2", "k3", "k4", "k5")
    assert 0 <= r_large < 1

    # Empty keys list
    r_empty_keys = engine.roll(123)
    assert 0 <= r_empty_keys < 1


def test_outcome_for_boundaries():
    """outcome_for(margin, r) returns correct outcomes at margin boundaries."""
    # Margin >= 3
    assert engine.outcome_for(3, 0.4) == "crit"
    assert engine.outcome_for(3, 0.5) == "success"
    assert engine.outcome_for(10, 0.9) == "success"

    # Margin == 1
    assert engine.outcome_for(1, 0.0) == "success"

    # Margin == 0
    assert engine.outcome_for(0, 0.54) == "success"
    assert engine.outcome_for(0, 0.55) == "partial"
    assert engine.outcome_for(0, 0.84) == "partial"
    assert engine.outcome_for(0, 0.85) == "fail"

    # Margin == -1
    assert engine.outcome_for(-1, 0.19) == "success"
    assert engine.outcome_for(-1, 0.20) == "partial"
    assert engine.outcome_for(-1, 0.49) == "partial"
    assert engine.outcome_for(-1, 0.50) == "fail"

    # Margin == -2
    assert engine.outcome_for(-2, 0.04) == "success"
    assert engine.outcome_for(-2, 0.05) == "partial"
    assert engine.outcome_for(-2, 0.19) == "partial"
    assert engine.outcome_for(-2, 0.20) == "fail"

    # Margin < -2
    assert engine.outcome_for(-3, 0.0) == "fail"
    assert engine.outcome_for(-10, 0.99) == "fail"


def test_odds_word_boundaries():
    """odds_word(margin) returns the correct word for margin ranges."""
    assert engine.odds_word(1) == engine.SOLID
    assert engine.odds_word(5) == engine.SOLID

    assert engine.odds_word(0) == engine.RISKY

    assert engine.odds_word(-1) == engine.LONG
    assert engine.odds_word(-2) == engine.LONG

    assert engine.odds_word(-3) == engine.NONE
    assert engine.odds_word(-10) == engine.NONE


def test_parse_cell_edge_cases():
    """parse_cell handles None, empty strings, and valid/invalid formats."""
    assert engine.parse_cell(None) == (None, None)
    assert engine.parse_cell("") == (None, None)
    assert engine.parse_cell("lockpick") == ("lockpick", None)
    assert engine.parse_cell("standby:noise") == ("standby", "noise")
    assert engine.parse_cell("standby:") == ("standby", None)
    assert engine.parse_cell(123) == (None, None)


def test_empty_plan_sizes():
    """empty_plan(n_beats) creates a plan with the correct number of lanes and beats."""
    p0 = engine.empty_plan(0)
    assert len(p0["lanes"]) == 5
    for lane in p0["lanes"]:
        assert len(lane) == 0

    p10 = engine.empty_plan(10)
    assert len(p10["lanes"]) == 5
    for lane in p10["lanes"]:
        assert len(lane) == 10


def test_clean_plan_malformed_input(C):
    """clean_plan rejects or sanitizes malformed plans without raising."""
    # Missing lanes key
    bad_plan = {"rows": [[None] * 5 for _ in range(5)]}
    clean = engine.clean_plan(C, bad_plan, 5)
    assert all(cell is None for lane in clean["lanes"] for cell in lane)

    # Unknown action
    bad_action_plan = {"lanes": [["unknown_action"] * 5 for _ in range(5)]}
    clean = engine.clean_plan(C, bad_action_plan, 5)
    assert all(cell is None for lane in clean["lanes"] for cell in lane)

    # Standby with invalid kind
    bad_standby = {"lanes": [["standby:ghost"] * 5 for _ in range(5)]}
    clean = engine.clean_plan(C, bad_standby, 5)
    assert all(cell is None for lane in clean["lanes"] for cell in lane)

    # Valid plan passes through correctly (assuming 'lockpick' is a valid action id in C)
    valid_action = "lockpick" if "lockpick" in C.actions else list(C.actions.keys())[0]
    good_plan = {"lanes": [[valid_action] * 5 for _ in range(5)]}
    clean = engine.clean_plan(C, good_plan, 5)
    assert all(cell == valid_action for lane in clean["lanes"] for cell in lane)
