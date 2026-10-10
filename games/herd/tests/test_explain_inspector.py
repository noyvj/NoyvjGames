"""F-6: the "Why this number?" inspector. income_breakdown() is what advance_round() banks, so the
tree can never disagree with the game; the tree texts are plain and escaped."""

import itertools


def _click(env, id_):
    env.elements[id_].dispatch("click", None)


def _rich_farm(env, variation=False):
    m = env.module
    f = env.farm
    f.funds = 100000.0
    for _ in range(8):
        f.grow_herd()
    for key in ("feed", "caps", "capture", "capture", "capture"):
        f.invest_decoupling(key)
    f.invest_plant_pivot()
    f.invest_plant_pivot()
    f.invest_supply_chain()
    f.genetics_active = 2
    f.certified = True
    f.poultry_investment = {k: 0 for k in m.POULTRY_MEASURES}
    f.poultry_size = 3
    f.satellite_open = True
    f.satellite_size = 2
    f.variation_enabled = variation
    f.methane = 37.0
    return f


def test_the_breakdown_total_is_exactly_what_the_round_banks(game_env):
    for variation, rounds in itertools.product((False, True), (1, 2, 3, 4, 5, 7)):
        game_env.module.farm.__init__()
        f = _rich_farm(game_env, variation)
        f.round_number = rounds
        expected = f.income_breakdown()["total"]
        before = f.funds
        f.advance_round()
        bonus = f.just_streak_bonus[1] if f.just_streak_bonus else 0
        assert abs((f.funds - before - bonus) - expected) < 1e-9


def test_a_fresh_farm_earns_nothing_and_the_tree_says_so(game_env):
    assert game_env.farm.income_breakdown()["total"] == 0
    _click(game_env, "explain-income-button")
    out = game_env.elements["explain-output"]
    assert out.hidden is False and "+0.0" in out.innerHTML and "Herd income" in out.innerHTML


def test_income_tree_names_every_active_piece(game_env):
    _rich_farm(game_env, variation=True)
    html = game_env.module.explain_html("income")
    for piece in ("Base income", "Plant-based blend", "Sustainable certification", "Welfare", "Poultry flock",
                  "Satellite farm", "Supply chain", "Season", "Income before pressure", "Market/regulatory pressure"):
        assert piece in html, piece


def test_methane_tree_adds_up(game_env):
    f = _rich_farm(game_env)
    html = game_env.module.explain_html("methane")
    assert f"{f.methane_this_round():.2f}" in html and "Herd" in html and "Poultry flock" in html and "Satellite farm" in html


def test_coupling_tree_lists_each_lever_then_the_floor_and_pivot(game_env):
    _rich_farm(game_env)
    html = game_env.module.explain_html("coupling")
    for piece in ("Starting level", "Feed Additives", "Herd Caps", "Capture Systems", "Breeding program",
                  "After efficiency measures", "Plant-based pivot"):
        assert piece in html, piece
    assert f"{game_env.farm.coupling_ratio():.2f}" in html


def test_pressure_tree_shows_the_cap(game_env):
    game_env.farm.methane = 250.0
    html = game_env.module.explain_html("pressure")
    assert "80%" in html and "250.0" in html


def test_buttons_toggle_one_breakdown_at_a_time_and_update_with_play(game_env):
    el = game_env.elements
    _click(game_env, "explain-coupling-button")
    assert el["explain-coupling-button"].getAttribute("aria-pressed") == "true"
    assert el["explain-income-button"].getAttribute("aria-pressed") == "false"
    first = el["explain-output"].innerHTML
    game_env.farm.funds = 1000.0
    game_env.invest_decoupling("capture")
    assert el["explain-output"].innerHTML != first  # live: the new unit appears
    _click(game_env, "explain-coupling-button")
    assert el["explain-output"].hidden is True and el["explain-output"].innerHTML == ""


def test_text_is_escaped(game_env):
    html = game_env.module._tree_html([game_env.module._node("<b>x</b>", "1", "<i>n</i>")])
    assert "<b>" not in html and "&lt;b&gt;" in html
