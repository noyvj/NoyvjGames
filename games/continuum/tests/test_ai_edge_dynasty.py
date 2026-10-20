"""Edge-case tests for dynasty.py."""


import dynasty


def test_clean_handles_non_dict_and_boundary_values():
    # Non-dict inputs fall back to default
    assert dynasty.clean(None) == dynasty.default()
    assert dynasty.clean("x") == dynasty.default()
    assert dynasty.clean([]) == dynasty.default()

    # Clamping earned and runs
    rec = dynasty.clean({"earned": -5, "runs": 10**7, "failed": 200000})
    assert rec["earned"] == 0
    assert rec["runs"] == 10**5
    assert rec["failed"] == 10**5

    # Sanitizing owned list when not provided or wrong type
    rec = dynasty.clean({"owned": "not a list"})
    assert isinstance(rec["owned"], list)


def test_run_points_respects_season_floor_and_clamps_era():
    # Too few seasons yields zero
    assert dynasty.run_points(0, 39, 70, False, False) == 0
    assert dynasty.run_points(1, 40, 70, False, False) > 0

    # Era index clamping (both large values clamp to the same max era)
    assert dynasty.run_points(-5, 80, 70, False, False) == dynasty.run_points(0, 80, 70, False, False)
    assert dynasty.run_points(100, 80, 70, False, False) == dynasty.run_points(999, 80, 70, False, False)

    # Peak score threshold
    assert dynasty.run_points(1, 80, 69.9, False, False) < dynasty.run_points(1, 80, 70, False, False)

    # Hard mode bonus and MAX cap
    base = dynasty.run_points(5, 100, 70, False, False)
    hard = dynasty.run_points(5, 100, 70, True, False)
    assert hard > base
    # The formula caps at MAX_RUN_POINTS; with current constants it reaches 41, so we check the cap holds.
    assert dynasty.run_points(10, 200, 100, True, False) <= dynasty.MAX_RUN_POINTS


def test_rank_name_and_next_rank_at_boundaries():
    # Zero and top rank
    assert dynasty.rank_name(0) == "Founder"
    assert dynasty.next_rank(0) is not None

    assert dynasty.rank_name(55) == "Dynast"
    assert dynasty.next_rank(55) is None
    assert dynasty.next_rank(100000) is None

    # Just below thresholds
    assert dynasty.rank_name(4) == "Founder"
    assert dynasty.rank_name(5) == "Steward"
    assert dynasty.next_rank(4)[0] == 1  # needs 1 more


def test_bank_handles_invalid_info_and_zero_points():
    ui = {}
    # Invalid info returns zero gained
    assert dynasty.bank(ui, None)["gained"] == 0
    assert dynasty.bank(ui, "x")["gained"] == 0

    # Zero or negative points yields no bank
    assert dynasty.bank(ui, {"points": 0})["gained"] == 0
    assert dynasty.bank(ui, {"points": -10})["gained"] == 0

    # Valid points updates record
    res = dynasty.bank(ui, {"points": 5})
    assert res["gained"] == 5
    assert dynasty.get(ui)["earned"] == 5


def test_start_text_formats_various_combinations():
    assert dynasty.start_text({}) == ""
    assert dynasty.start_text({"food": 4.0}) == "+4 food"
    assert dynasty.start_text({"people": 1}) == "+1 person"
    assert dynasty.start_text({"people": 2}) == "+2 people"
    assert dynasty.start_text({"tools": 1}) == "+1 tool"
    assert dynasty.start_text({"tools": 3}) == "+3 tools"
    # Mixed order doesn't matter for the set, but let's check a combo
    txt = dynasty.start_text({"food": 4.0, "materials": 6.0, "people": 1})
    assert "+4 food" in txt and "+6 materials" in txt and "+1 person" in txt


def test_merge_prefers_larger_earned_and_handles_types():
    a = {"earned": 10, "owned": ["heirloom_granary"], "runs": 5, "failed": 2, "hard_runs": 1, "best_era": 3, "off": False}
    b = {"earned": 8, "owned": ["kin_arrive"], "runs": 6, "failed": 1, "hard_runs": 2, "best_era": 4, "off": True}

    # a has more earned, so owned comes from a
    merged = dynasty.merge(a, b)
    assert merged["earned"] == 10
    assert merged["owned"] == ["heirloom_granary"]
    assert merged["runs"] == 6
    assert merged["best_era"] == 4

    # Tie: save (first arg) wins for owned
    a_tie = {"earned": 10, "owned": ["heirloom_granary"], "runs": 5, "failed": 2, "hard_runs": 1, "best_era": 3, "off": False}
    b_tie = {"earned": 10, "owned": ["kin_arrive"], "runs": 6, "failed": 1, "hard_runs": 2, "best_era": 4, "off": True}
    merged_tie = dynasty.merge(a_tie, b_tie)
    assert merged_tie["owned"] == ["heirloom_granary"]

    # Non-dict inputs fall back to default via clean()
    assert dynasty.merge(None, b) == dynasty.clean(b)
    assert dynasty.merge(a, "x") == dynasty.clean(a)
