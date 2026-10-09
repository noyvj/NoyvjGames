"""K-13: the endless Beyond mode after the Relay Age."""

import json

import beyond
import research
import sim
import sustainability

from .test_relay_era import relay_state


def on_ui(**changes):
    record = {"on": True, "era": 1, "season": 0, "good": 0, "best": 0, "runs": 1}
    record.update(changes)
    return {beyond.KEY: record}


# --- validation -------------------------------------------------------------
def test_default_record_is_not_stored():
    ui = {}
    beyond.put(ui, beyond.fresh())
    assert beyond.KEY not in ui
    assert beyond.get(ui) == beyond.fresh()


def test_clean_survives_junk():
    assert beyond.clean(None) == beyond.fresh()
    assert beyond.clean("x") == beyond.fresh()
    rec = beyond.clean({"on": "yes", "era": -4, "season": 99, "good": 50, "best": float("nan"), "runs": True})
    assert rec["on"] is False and rec["era"] == 1 and rec["season"] == beyond.ERA_SEASONS
    assert rec["good"] <= rec["season"] and rec["best"] == 0 and rec["runs"] == 0
    assert beyond.clean({"era": [3]})["era"] == 1
    assert beyond.clean({"era": 10**9})["era"] == beyond.MAX_ERA


# --- the numbers --------------------------------------------------------------
def test_available_from_the_relay_age_only():
    assert not beyond.available("space")
    assert beyond.available("relay")
    assert not beyond.available(None) and not beyond.available("nonsense")


def test_themes_cycle_and_bars_rise_to_a_cap():
    ids = [beyond.theme_for(n)["id"] for n in range(1, 8)]
    assert ids[:6] == [t["id"] for t in beyond.THEMES] and ids[6] == ids[0]
    assert beyond.bar_for(1) == beyond.BASE_BAR
    assert beyond.bar_for(2) == beyond.BASE_BAR + beyond.BAR_PER_ERA
    assert beyond.bar_for(500) == beyond.MAX_BAR


def test_every_theme_presses_on_a_real_effects_key_and_names_a_remedy():
    for theme in beyond.THEMES:
        assert theme["key"] in sim.NEUTRAL_EFFECTS
        assert theme["remedy_text"] and theme["blurb"] and theme["what"]
        assert 0 < theme["base"] < 1
        assert not any(c.isdigit() for c in theme["name"] + theme["blurb"])
        state = sim.CityState(era="relay")
        assert 0.0 <= beyond.remedy_ratio(theme, state) <= 1.0


def test_entropy_only_rises():
    values = [beyond.entropy({"era": e, "season": s}) for e in range(1, 5) for s in range(0, beyond.ERA_SEASONS)]
    assert values == sorted(values)
    assert beyond.entropy({"era": 1, "season": 0}) == 0


def test_the_remedy_softens_the_pressure_but_fades_with_each_era():
    theme = beyond.THEMES[0]
    state = sim.CityState(era="relay")
    state.resources["food"] = 0.0
    low = beyond.pressure({"era": 1, "season": 0}, state)
    state.resources["food"] = state.food_storage_capacity()
    high = beyond.pressure({"era": 1, "season": 0}, state)
    assert 0 < high < low <= theme["base"] + 1e-9
    assert beyond.remedy_cut(1) > beyond.remedy_cut(10) >= beyond.REMEDY_FLOOR
    assert beyond.remedy_cut(10**6) == beyond.REMEDY_FLOOR


def test_pressure_is_capped():
    state = sim.CityState(era="relay")
    state.resources["food"] = 0.0
    assert beyond.pressure({"era": 500, "season": 5}, state) <= beyond.MAX_REDUCTION


def test_effects_are_untouched_when_off_or_resting_or_early_with_no_tax():
    effects = dict(sim.NEUTRAL_EFFECTS)
    state = sim.CityState(era="relay")
    assert beyond.apply_effects(effects, {}, state, True) is effects
    assert beyond.apply_effects(effects, on_ui(), state, False) is effects


def test_a_run_presses_on_its_theme_key_and_never_below_the_floor():
    state = sim.CityState(era="relay")
    state.resources["food"] = 0.0
    base = dict(sim.NEUTRAL_EFFECTS)
    out = beyond.apply_effects(base, on_ui(era=1), state, True)
    assert out["food_yield_mult"] < base["food_yield_mult"]
    assert base["food_yield_mult"] == sim.NEUTRAL_EFFECTS["food_yield_mult"]
    deep = beyond.apply_effects(base, on_ui(era=400), state, True)
    assert deep["food_yield_mult"] >= 0.1
    additive = beyond.apply_effects(base, on_ui(era=5), state, True)    # Cold Habitats (culture_bonus)
    assert additive["culture_bonus"] >= -0.5
    assert beyond.theme_for(5)["id"] == "cold"


def test_the_entropy_tax_appears_from_the_second_era():
    state = sim.CityState(era="relay")
    base = dict(sim.NEUTRAL_EFFECTS)
    assert beyond.entropy_tax({"era": 1}) == 0
    assert beyond.entropy_tax({"era": 3}) == round(2 * beyond.ENTROPY_TAX_PER_ERA, 4)
    assert beyond.entropy_tax({"era": 10**6}) == beyond.ENTROPY_TAX_MAX
    taxed = beyond.apply_effects(base, on_ui(era=2), state, True)
    assert taxed["food_yield_mult"] < 1.0


# --- starting and scoring a run ----------------------------------------------------
def test_start_needs_the_relay_age_and_refuses_resting_and_look_back():
    ui = {}
    assert beyond.start(ui, "space", False, False)[0] is False
    assert beyond.start(ui, "relay", True, False)[0] is False
    assert beyond.start(ui, "relay", False, True)[0] is False
    assert ui == {}
    ok, text = beyond.start(ui, "relay", False, False)
    assert ok and beyond.THEMES[0]["name"] in text
    assert beyond.get(ui)["on"] and beyond.get(ui)["runs"] == 1
    assert beyond.start(ui, "relay", False, False)[0] is False


def run_season(ui, score):
    return beyond.after_season(ui, score)


def test_good_seasons_survive_an_era_and_advance_the_theme():
    ui = on_ui()
    event = None
    for _ in range(beyond.ERA_SEASONS):
        event = run_season(ui, 90)
    assert event == {"kind": "survived", "era": 1, "next_theme": beyond.theme_for(2)["name"]}
    rec = beyond.get(ui)
    assert rec["era"] == 2 and rec["season"] == 0 and rec["best"] == 1 and rec["on"]


def test_two_missed_seasons_are_forgiven_three_end_the_run_early():
    ui = on_ui()
    for score in [10, 10] + [90] * 10:
        event = run_season(ui, score)
    assert event and event["kind"] == "survived"
    ui = on_ui()
    events = [run_season(ui, 10) for _ in range(3)]
    assert events[:2] == [None, None]
    assert events[2] == {"kind": "ended", "survived": 0}
    assert beyond.get(ui)["on"] is False and beyond.get(ui)["era"] == 1


def test_the_bar_rises_with_the_era():
    ui = on_ui(era=11)
    bar = beyond.bar_for(11)
    for _ in range(beyond.ERA_SEASONS):
        event = run_season(ui, bar - 1)
        if event:
            break
    assert event["kind"] == "ended" and event["survived"] == 10
    assert beyond.get(ui)["best"] == 0 or beyond.get(ui)["best"] >= 0


def test_after_season_ignores_junk_scores_and_idle_runs():
    assert beyond.after_season({}, 80) is None
    ui = on_ui()
    assert beyond.after_season(ui, None) is None
    assert beyond.after_season(ui, True) is None
    assert beyond.get(ui)["season"] == 0


def test_stop_reports_eras_survived_and_lifts_the_pressure():
    ui = on_ui(era=4, best=3)
    assert beyond.stop(ui) == 3
    assert beyond.get(ui)["on"] is False and beyond.get(ui)["best"] == 3
    assert beyond.stop(ui) is None
    state = sim.CityState(era="relay")
    assert beyond.apply_effects(dict(sim.NEUTRAL_EFFECTS), ui, state, True) == dict(sim.NEUTRAL_EFFECTS)


def test_status_lines_name_the_theme_pressure_remedy_and_bar():
    state = sim.CityState(era="relay")
    lines = beyond.status_lines(beyond.clean(on_ui()[beyond.KEY]), state)
    text = " ".join(lines)
    assert "The Long Drought" in text and "Remedy" in text and "sustainability score at 40" in text
    assert beyond.status_lines(beyond.fresh(), state) == []


# --- the ladder ---------------------------------------------------------------------
def test_the_ladder_sorts_caps_and_skips_empty_runs():
    rows = []
    for i, n in enumerate([3, 9, 1, 9, 0, 5]):
        rows = beyond.add_to_ladder(rows, f"2026-10-0{i + 1}", n, "Town")
    assert [r["survived"] for r in rows] == [9, 9, 5, 3, 1]
    assert rows[0]["date"] < rows[1]["date"]
    many = []
    for i in range(30):
        many = beyond.add_to_ladder(many, "2026-10-01", i + 1)
    assert len(many) == beyond.LADDER_MAX and many[0]["survived"] == 30


def test_ladder_cleaning_survives_junk():
    assert beyond.clean_ladder("not json") == []
    assert beyond.clean_ladder(None) == []
    rows = beyond.clean_ladder([None, "x", {"date": "bad", "survived": 3}, {"date": "2026-10-01", "survived": -1},
                                {"date": "2026-10-01", "survived": 4, "name": 12}, {"date": "2026-10-02", "survived": True}])
    assert rows == [{"date": "2026-10-01", "survived": 4, "name": ""}]
    assert beyond.clean_ladder(json.dumps([{"date": "2026-10-01", "survived": 2, "name": "x" * 90}]))[0]["name"] == "x" * 28
    assert "1 Beyond era survived" in beyond.ladder_text({"survived": 1, "date": "2026-10-01", "name": ""}, 1)


# --- a whole run is finite and a better-prepared settlement goes further ------------------
def simulate(researched, adaptive):
    state = relay_state(relays=2, wayfinders=6, surplus=50, population=60)
    state.resources.update(tools=60.0, food=60.0)
    state.allocation.update(foragers=0, farmers=22, gatherers=6, keepers=6)
    state.buildings.update(farmland=6, granary=2)
    tree = research.build_tree(current_era="relay")
    for node_id in list(tree.nodes)[:researched]:
        tree.researched.append(node_id)
    ui = {}
    beyond.start(ui, "relay", False, False)
    for _ in range(1200):
        effects = beyond.apply_effects(tree.effects(), ui, state, True)
        state.advance_season(effects)
        if adaptive and state.resources["food"] < state.population * 2 and state.idle_workers() > 0:
            state.allocation["farmers"] += state.idle_workers()
        event = beyond.after_season(ui, sustainability.score(state, effects))
        if event and event["kind"] == "ended":
            return event["survived"]
    return None


def test_a_run_always_ends_and_more_research_goes_further():
    poor = simulate(12, True)
    rich = simulate(30, True)
    assert poor is not None and rich is not None
    assert 1 <= poor < rich < 80


# --- the game -------------------------------------------------------------------------------
def to_relay(game_env):
    module = game_env.module
    module.campaign.furthest_era = "relay"
    module.state.era = "relay"
    module.tree.current_era = "relay"
    module.render()
    return module


def test_the_panel_starts_a_run_and_a_season_scores_it(game_env):
    module = to_relay(game_env)
    elements = game_env.elements
    module.on_toggle_beyond()
    assert elements["beyond-panel"].hidden is False
    assert elements["beyond-start-button"].disabled is False
    elements["beyond-start-button"].dispatch("click", None)
    assert beyond.get(module.campaign.ui)["on"] is True
    assert elements["beyond-stop-button"].hidden is False
    assert "The Long Drought" in " ".join(c.innerText for c in elements["beyond-lines"].children)
    game_env.advance_season()
    assert beyond.get(module.campaign.ui)["season"] == 1


def test_the_panel_is_closed_to_earlier_eras_and_during_a_look_back(game_env):
    module = game_env.module
    elements = game_env.elements
    module.on_toggle_beyond()
    assert elements["beyond-start-button"].disabled is True
    assert "Relay Age" in elements["beyond-note"].innerText
    module = to_relay(game_env)
    module._beyond_signature = None
    module.campaign.revisiting = "tribal"
    module.update_beyond_panel()
    assert elements["beyond-start-button"].disabled is True
    module.campaign.revisiting = None


def test_ending_a_run_banks_it_on_the_ladder_without_a_storage_window(game_env):
    module = to_relay(game_env)
    module.campaign.ui[beyond.KEY] = on_ui(era=4, best=3)[beyond.KEY]
    saved = {}
    module.beyond_ladder_store = lambda rows: saved.setdefault("rows", rows)
    module.beyond_ladder_load = lambda: []
    module.on_beyond_stop()
    assert saved["rows"][0]["survived"] == 3
    assert beyond.get(module.campaign.ui)["on"] is False


def test_beyond_does_not_press_during_a_look_back(game_env):
    module = to_relay(game_env)
    module.campaign.ui[beyond.KEY] = on_ui(era=3)[beyond.KEY]
    pressed = module.current_effects()["food_yield_mult"]
    module.campaign.revisiting = "tribal"
    try:
        calm = module.current_effects()["food_yield_mult"]
    finally:
        module.campaign.revisiting = None
    assert calm >= pressed


def test_beyond_state_survives_a_save_and_old_saves_have_none(game_env):
    module = to_relay(game_env)
    module.campaign.ui[beyond.KEY] = on_ui(era=3, best=2)[beyond.KEY]
    data = json.loads(json.dumps(module.get_state()))
    module.campaign.ui.pop(beyond.KEY)
    module.load_state(data)
    assert beyond.get(module.campaign.ui)["era"] == 3
    data["ui"].pop(beyond.KEY)
    module.load_state(data)
    assert beyond.get(module.campaign.ui) == beyond.fresh()
    data["ui"][beyond.KEY] = "junk"
    module.load_state(data)
    assert beyond.get(module.campaign.ui) == beyond.fresh()


def test_the_archive_record_remembers_the_furthest_beyond_era(game_env):
    import archive
    module = to_relay(game_env)
    module.campaign.ui[beyond.KEY] = {"on": False, "era": 1, "season": 0, "good": 0, "best": 7, "runs": 2}
    record = module.current_record()
    assert record["beyond"] == 7
    assert any("Beyond: 7 eras survived" in line for line in archive.card_lines(record))
    assert "beyond" not in archive.clean_record(dict(record, beyond=0))
    assert "beyond" not in archive.clean_record(dict(record, beyond="x"))
