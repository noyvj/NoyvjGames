"""K-5: living ruins (heritage sites)."""

import json

import heritage
import sim
import views


def test_no_sites_in_the_first_era():
    assert heritage.sites_before("tribal", {}) == []
    assert heritage.counts({}, "tribal") == (0, 0)
    assert heritage.culture_delta({}, "tribal") == 0


def test_one_site_per_era_left_behind_and_none_for_the_last():
    sites = heritage.sites_before("relay", {})
    assert [s["era"] for s in sites] == sim.ERA_ORDER[:-1]
    assert all(s["kept"] for s in sites)
    assert set(heritage.SITES) == set(sim.ERA_ORDER[:-1])
    assert heritage.sites_before("bogus", {}) == []
    assert heritage.sites_before(None, {}) == []


def test_names_are_distinct_and_free_of_digits():
    names = [name for name, _ in heritage.SITES.values()]
    assert len(set(names)) == len(names)
    for name, blurb in heritage.SITES.values():
        assert not any(c.isdigit() for c in name + blurb)


def test_demolished_list_is_validated():
    assert heritage.demolished({}) == []
    assert heritage.demolished(None) == []
    ui = {heritage.KEY: {"demolished": ["agrarian", "tribal", "tribal", "relay", 3, ["x"], None, "nonsense"]}}
    assert heritage.demolished(ui) == ["tribal", "agrarian"]
    assert heritage.demolished({heritage.KEY: "x"}) == []
    assert heritage.demolished({heritage.KEY: {"demolished": "tribal"}}) == []


def test_kept_sites_add_culture_and_cleared_ones_cost_it():
    ui = {}
    assert heritage.culture_delta(ui, "medieval") == round(3 * heritage.KEEP_BONUS, 4)
    ui[heritage.KEY] = {"demolished": ["tribal"]}
    assert heritage.culture_delta(ui, "medieval") == round(2 * heritage.KEEP_BONUS - heritage.DEMOLISH_PENALTY, 4)
    kept, cleared = heritage.counts(ui, "medieval")
    assert (kept, cleared) == (2, 1)


def test_apply_effects_leaves_effects_alone_when_nothing_changes_or_resting():
    effects = dict(sim.NEUTRAL_EFFECTS)
    assert heritage.apply_effects(effects, {}, "tribal", False) is effects
    assert heritage.apply_effects(effects, {}, "medieval", True) is effects
    out = heritage.apply_effects(effects, {}, "classical", False)
    assert out["culture_bonus"] == round(effects["culture_bonus"] + 2 * heritage.KEEP_BONUS, 6)
    assert effects["culture_bonus"] == sim.NEUTRAL_EFFECTS["culture_bonus"]


def test_the_culture_bonus_cannot_run_away_negative():
    ui = {heritage.KEY: {"demolished": list(heritage.SITES)}}
    out = heritage.apply_effects(dict(sim.NEUTRAL_EFFECTS), ui, "relay", False)
    assert out["culture_bonus"] >= -0.5


def test_demolish_pays_once_and_costs_culture():
    state = sim.CityState()
    state.land_health = 0.5
    ui = {}
    before = state.resources["materials"]
    ok, text = heritage.demolish(ui, state, "classical", "tribal", False, False)
    assert ok and "cleared" in text
    assert state.resources["materials"] == before + heritage.demolish_gain("tribal")
    assert abs(state.land_health - (0.5 + heritage.DEMOLISH_LAND)) < 1e-9
    assert heritage.demolished(ui) == ["tribal"]
    ok, text = heritage.demolish(ui, state, "classical", "tribal", False, False)
    assert not ok and "already cleared" in text
    assert state.resources["materials"] == before + heritage.demolish_gain("tribal")


def test_later_eras_pay_more_and_land_is_capped():
    assert heritage.demolish_gain("space") > heritage.demolish_gain("tribal")
    state = sim.CityState()
    state.land_health = 0.99
    heritage.demolish({}, state, "medieval", "agrarian", False, False)
    assert state.land_health == 1.0


def test_demolish_refuses_unknown_future_resting_and_look_back():
    state = sim.CityState()
    ui = {}
    assert heritage.demolish(ui, state, "tribal", "tribal", False, False)[0] is False       # not left yet
    assert heritage.demolish(ui, state, "classical", "relay", False, False)[0] is False     # no site there
    assert heritage.demolish(ui, state, "classical", ["x"], False, False)[0] is False       # junk
    assert heritage.demolish(ui, state, "classical", "tribal", True, False)[0] is False     # resting
    assert heritage.demolish(ui, state, "classical", "tribal", False, True)[0] is False     # look back
    assert ui == {} and state.resources["materials"] == sim.CityState().resources["materials"]


def test_preview_text_names_the_site_and_its_state():
    assert "still standing" in heritage.preview_text("tribal", {})
    assert "cleared" in heritage.preview_text("tribal", {heritage.KEY: {"demolished": ["tribal"]}})
    assert heritage.preview_text("relay", {}) == ""


def test_civic_map_gains_a_heritage_row_with_words_and_shapes():
    state = sim.CityState()
    plain = views.civic_map_svg(state)
    sites = heritage.sites_before("medieval", {heritage.KEY: {"demolished": ["agrarian"]}})
    with_sites = views.civic_map_svg(state, 0, sites)
    assert "Heritage, kept" in with_sites and "Heritage, cleared" in with_sites
    assert "Tribal ruin" in with_sites and "map-heritage--cleared" in with_sites
    assert "Heritage" not in plain
    assert views.civic_map_svg(state, 0, []) == plain


# --- the game --------------------------------------------------------------
def to_classical(game_env):
    module = game_env.module
    module.campaign.furthest_era = "classical"
    module.state.era = "classical"
    module.tree.current_era = "classical"
    module.render()
    return module


def test_a_kept_site_raises_culture_capacity_in_the_season_loop(game_env):
    module = to_classical(game_env)
    with_sites = module.state.culture_capacity(module.current_effects())
    module.campaign.ui[heritage.KEY] = {"demolished": ["tribal", "agrarian"]}
    cleared = module.state.culture_capacity(module.current_effects())
    assert with_sites > cleared


def test_the_panel_lists_sites_and_clearing_takes_two_clicks(game_env):
    module = to_classical(game_env)
    elements = game_env.elements
    module.on_toggle_heritage()
    assert elements["heritage-panel"].hidden is False
    assert len(elements["heritage-list"].children) == 2
    materials = module.state.resources["materials"]
    button = elements["heritage-tribal-demolish-button"]
    button.dispatch("click", None)
    assert module.state.resources["materials"] == materials
    assert heritage.demolished(module.campaign.ui) == []
    assert "cannot be undone" in elements["heritage-status"].innerText
    elements["heritage-tribal-demolish-button"].dispatch("click", None)
    assert heritage.demolished(module.campaign.ui) == ["tribal"]
    assert module.state.resources["materials"] == materials + heritage.demolish_gain("tribal")
    assert "heritage-tribal-demolish-button" not in [c.id for card in elements["heritage-list"].children for c in card.children]


def test_cancelling_keeps_the_site(game_env):
    module = to_classical(game_env)
    elements = game_env.elements
    module.on_toggle_heritage()
    elements["heritage-agrarian-demolish-button"].dispatch("click", None)
    elements["heritage-agrarian-cancel-button"].dispatch("click", None)
    assert heritage.demolished(module.campaign.ui) == []


def test_heritage_is_visible_in_the_visual_state_and_hidden_while_resting(game_env):
    module = to_classical(game_env)
    module.campaign.ui[heritage.KEY] = {"demolished": ["tribal"]}
    data = module.get_visual_state()
    assert data["heritage"] == [{"era": "tribal", "kept": False}, {"era": "agrarian", "kept": True}]
    json.dumps(data)
    module.campaign.ui["challenge_run"] = {"kind": "custom"}
    try:
        if module._resting():
            assert module.get_visual_state()["heritage"] == []
    finally:
        module.campaign.ui.pop("challenge_run", None)


def test_leaving_an_era_logs_the_site_left_standing(game_env):
    module = game_env.module
    module.campaign.furthest_era = "agrarian"
    module.state.era = "agrarian"
    module._log_heritage_left_behind()
    texts = [e.text for e in module.chronicle.entries]
    assert any("Founders' Circle" in t and "left standing" in t for t in texts)


def test_look_back_rows_preview_the_heritage(game_env):
    module = to_classical(game_env)
    module.campaign.era_snapshots["tribal"] = module.campaign.to_dict()["current_state"]
    module.render()
    rows = game_env.elements["revisit-era-list"].children
    texts = [c.innerText for row in rows for c in row.children]
    assert any("Heritage: The Founders' Circle" in t for t in texts)


def test_dashboard_has_a_heritage_row(game_env):
    module = to_classical(game_env)
    rows = module._extra_dashboard_sections()[0]["rows"]
    assert ("Heritage sites", "2 kept, 0 cleared") in rows


def test_old_saves_load_with_every_site_kept(game_env):
    module = to_classical(game_env)
    data = json.loads(json.dumps(module.get_state()))
    data["ui"].pop(heritage.KEY, None)
    module.load_state(data)
    assert heritage.demolished(module.campaign.ui) == []
    data["ui"][heritage.KEY] = {"demolished": ["tribal", 7, None]}
    module.load_state(data)
    assert heritage.demolished(module.campaign.ui) == ["tribal"]
    data["ui"][heritage.KEY] = "junk"
    module.load_state(data)
    assert heritage.demolished(module.campaign.ui) == []
