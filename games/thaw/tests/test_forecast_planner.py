"""G-5: the forecast planner (a what-if on a scratch copy of one region)."""

import copy


def _set(game_env, **units):
    for category in ("output", "preserve", "monitor"):
        game_env.elements[f"planner-{category}"].value = str(units.get(category, ""))
    game_env.elements["planner-output"].dispatch("input")


def test_no_plan_matches_the_regions_real_future(game_env):
    m = game_env.module
    base, skipped = m.planner_projection(m.region, {c: 0 for c in m.CATEGORIES})
    assert skipped == 0 and len(base) == m.PLANNER_ROUNDS + 1
    probe = m.RegionState()
    m._apply_region_state(probe, m._region_state_dict(m.region))
    for _ in range(m.PLANNER_ROUNDS):
        probe.advance_round()
    assert base[-1] == probe.temperature


def test_planning_never_touches_the_real_region(game_env):
    m = game_env.module
    before = copy.deepcopy(m.get_state())
    _set(game_env, preserve=5, monitor=3)
    game_env.elements["planner-repeat"].checked = True
    game_env.elements["planner-repeat"].dispatch("change")
    assert m.get_state() == before


def test_protection_ends_cooler_than_no_change_once_melting(game_env):
    m = game_env.module
    for _ in range(9):
        game_env.advance_round()
    m.region.funds = 1000
    base, _s = m.planner_projection(m.region, {c: 0 for c in m.CATEGORIES})
    planned, _s = m.planner_projection(m.region, {"preserve": 8})
    assert planned[-1] < base[-1]


def test_output_only_plan_is_not_cooler(game_env):
    m = game_env.module
    for _ in range(9):
        game_env.advance_round()
    base, _s = m.planner_projection(m.region, {c: 0 for c in m.CATEGORIES})
    planned, _s = m.planner_projection(m.region, {"output": 5})
    assert planned[-1] == base[-1]


def test_unaffordable_units_are_skipped_and_reported(game_env):
    m = game_env.module
    m.region.funds = 30
    planned, skipped = m.planner_projection(m.region, {"preserve": 4})
    assert skipped == 3
    _set(game_env, preserve=4)
    assert "3 units could not be afforded" in game_env.elements["planner-readout"].innerText


def test_repeat_buys_again_each_round(game_env):
    m = game_env.module
    m.region.funds = 100
    once, skipped_once = m.planner_projection(m.region, {"monitor": 2}, repeat=False)
    again, skipped_again = m.planner_projection(m.region, {"monitor": 2}, repeat=True)
    assert skipped_again >= skipped_once


def test_input_parsing_is_defensive(game_env):
    m = game_env.module
    assert m._plan_int("") == 0
    assert m._plan_int("abc") == 0
    assert m._plan_int("-4") == 0
    assert m._plan_int("2.9") == 2
    assert m._plan_int("1e9") == m.PLANNER_MAX_UNITS
    assert m._plan_int("nan") == 0
    assert m._plan_int("inf") == 0
    assert m._plan_int(None) == 0


def test_chart_and_readout_render_for_each_region(game_env):
    for key in ("a", "b", "c"):
        game_env.elements["planner-region"].value = key
        _set(game_env, preserve=2)
        chart = game_env.elements["planner-chart"].innerHTML
        assert "planner-svg" in chart and f"Region {key.upper()}" in chart
        assert "10 rounds" in game_env.elements["planner-readout"].innerText


def test_readout_prompts_for_a_plan_when_empty(game_env):
    assert "Type a number of units" in game_env.elements["planner-readout"].innerText


def test_reset_clears_the_boxes(game_env):
    _set(game_env, preserve=3)
    game_env.elements["planner-repeat"].checked = True
    game_env.elements["planner-reset-button"].dispatch("click")
    assert game_env.elements["planner-preserve"].value == ""
    assert game_env.elements["planner-repeat"].checked is False


def test_advance_round_tooltip_carries_the_outlook(game_env):
    tip = game_env.elements["advance-round-button"].title
    assert "In 10 rounds with no change: A +" in tip
    assert "B +" in tip and "C +" in tip
    assert tip.startswith("Next round preview")


def test_plan_cost_adds_up(game_env):
    m = game_env.module
    assert m.plan_cost({"output": 1, "preserve": 1, "monitor": 2}) == 20 + 25 + 40


def test_long_game_and_hold_the_line_projections_still_run(game_env):
    m = game_env.module
    m.set_long_game(True)
    base, _s = m.planner_projection(m.region, {})
    assert base[-1] < 10
    m.set_long_game(False)
    m.set_hold_the_line(True)
    base, _s = m.planner_projection(m.region, {})
    assert base[-1] >= 10
