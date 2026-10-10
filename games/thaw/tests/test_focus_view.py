"""G-17: the single-region focus view with its own lever buttons."""


def _pick(game_env, key):
    game_env.elements["focus-region"].value = key
    game_env.elements["focus-region"].dispatch("change")


def test_default_focus_is_region_a(game_env):
    assert "Region A" in game_env.elements["focus-title"].innerText
    assert "Temperature" in game_env.elements["focus-readouts"].innerHTML


def test_focus_follows_the_selected_region(game_env):
    m = game_env.module
    m.region_b.temperature = 7.5
    _pick(game_env, "b")
    assert "Region B" in game_env.elements["focus-title"].innerText
    assert "+7.5°" in game_env.elements["focus-readouts"].innerHTML


def test_unknown_region_value_falls_back_to_a(game_env):
    _pick(game_env, "zzz")
    assert "Region A" in game_env.elements["focus-title"].innerText


def test_graph_needs_two_rounds_then_draws_labels_and_guides(game_env):
    assert "after the second round" in game_env.elements["focus-graph"].innerHTML
    for _ in range(3):
        game_env.advance_round()
    svg = game_env.elements["focus-graph"].innerHTML
    assert "focus-graph-svg" in svg and "R1" in svg and "R3" in svg
    assert "focus-guide--melt" in svg and "focus-guide--second" in svg
    assert 'role="img"' in svg and "aria-label" in svg


def test_graph_labels_follow_the_unit_setting(game_env):
    for _ in range(3):
        game_env.advance_round()
    game_env.module.set_temp_unit("f")
    game_env.module.render()
    assert "+18°F" in game_env.elements["focus-graph"].innerHTML


def test_lever_buttons_invest_in_the_focused_region(game_env):
    m = game_env.module
    _pick(game_env, "c")
    before = m.region_c.funds
    game_env.elements["focus-invest-preserve"].dispatch("click")
    assert m.region_c.capacity["preserve"] == 1
    assert m.region_c.funds == before - m.INVEST_COST["preserve"]
    assert m.region.capacity["preserve"] == 0


def test_lever_buttons_disable_when_unaffordable(game_env):
    m = game_env.module
    m.region_b.funds = 5
    _pick(game_env, "b")
    assert all(game_env.elements[f"focus-invest-{c}"].disabled for c in m.CATEGORIES)
    m.region_b.funds = 100
    m.render()
    assert not any(game_env.elements[f"focus-invest-{c}"].disabled for c in m.CATEGORIES)


def test_rescue_button_only_when_critical_and_affordable(game_env):
    m = game_env.module
    assert game_env.elements["focus-rescue-button"].hidden is True
    m.region.temperature = 30.0
    m.region.funds = 500
    m.render()
    assert game_env.elements["focus-rescue-button"].hidden is False
    assert game_env.elements["focus-rescue-button"].disabled is False
    game_env.elements["focus-rescue-button"].dispatch("click")
    assert m.region.rescue_used is True
    assert game_env.elements["focus-rescue-button"].hidden is True
    assert "Emergency rescue" in game_env.elements["focus-readouts"].innerHTML


def test_levers_do_nothing_after_a_run_ends(game_env):
    m = game_env.module
    m.run_over = True
    m.run_result = {"survived": 5, "saved": 1.0, "reason": "tipped"}
    m.render()
    assert all(game_env.elements[f"focus-invest-{c}"].disabled for c in m.CATEGORIES)
    before = m.region.funds
    game_env.elements["focus-invest-output"].dispatch("click")
    assert m.region.funds == before


def test_readouts_cover_the_key_numbers(game_env):
    m = game_env.module
    labels = [label for label, _ in m.focus_readouts(m.region)]
    for wanted in ("Temperature", "Status", "Funds", "Warming rate", "Feedback dampening", "Saved versus no action"):
        assert wanted in labels
