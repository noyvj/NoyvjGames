"""GB-21: clear-cut for a quick payout. A fixed bonus now, a visible soil dip that heals over about three seasons,
no dice, a Harvester badge, Undo, saves."""

import json

from .gb_helpers import advance_to, make_mature, tile, tile_marks


def _cut(env):
    env.elements["clear-cut-button"].dispatch("click", None)


def _mature_selected(env, index=5, value=100.0):
    plot = make_mature(env.module, index)
    plot.value = value
    env.select(index)
    return plot


def test_the_bonus_is_a_fixed_share_of_the_standing_value(game_env):
    m = game_env.module
    _mature_selected(game_env)
    before = m.total_income
    _cut(game_env)
    assert m.total_income == before + 100.0 * (1 + m.CLEAR_CUT_BONUS)
    assert m.plots[5].state == m.BARE
    assert m.clear_cuts_total == 1


def test_a_plain_clear_pays_no_bonus_and_leaves_no_dip(game_env):
    m = game_env.module
    _mature_selected(game_env)
    game_env.clear()
    assert m.total_income == 100.0
    assert m.plots[5].soil_dip_ticks == 0
    assert m.clear_cuts_total == 0


def test_the_dip_is_visible_in_the_soil_number_and_heals_in_a_straight_line(game_env):
    m = game_env.module
    plot = _mature_selected(game_env)
    full = plot.productivity_multiplier()
    _cut(game_env)
    assert plot.clear_count == 1
    permanent = max(m.MIN_PRODUCTIVITY_MULTIPLIER, 1 - m.current_degrade_per_clear())
    assert abs(plot.productivity_multiplier() - (permanent - m.CLEAR_CUT_DIP)) < 1e-9 or plot.productivity_multiplier() == m.MIN_PRODUCTIVITY_MULTIPLIER
    assert plot.productivity_multiplier() < permanent < full
    half = m.CLEAR_CUT_HEAL_TICKS // 2
    advance_to(game_env, half)
    assert plot.soil_dip_ticks == m.CLEAR_CUT_HEAL_TICKS - half
    assert abs(m.clear_cut_dip_fraction(plot) - m.CLEAR_CUT_DIP / 2) < 1e-9


def test_the_dip_heals_completely_in_three_seasons_and_the_permanent_cost_stays(game_env):
    m = game_env.module
    plot = _mature_selected(game_env)
    _cut(game_env)
    advance_to(game_env, m.CLEAR_CUT_HEAL_TICKS)
    assert plot.soil_dip_ticks == 0
    assert m.clear_cut_dip_fraction(plot) == 0.0
    assert abs(plot.productivity_multiplier() - (1 - m.current_degrade_per_clear())) < 1e-9
    assert any(e["kind"] == "heal" for e in m.forest_log)


def test_healing_goes_on_while_the_plot_is_replanted_and_growing(game_env):
    m = game_env.module
    plot = _mature_selected(game_env)
    _cut(game_env)
    game_env.replant()
    game_env.tick(30)
    assert plot.soil_dip_ticks == m.CLEAR_CUT_HEAL_TICKS - 30
    assert plot.state in (m.REPLANTING, m.RECOVERED)


def test_a_dipped_plot_grows_slower_than_a_healed_one(game_env):
    m = game_env.module
    a = _mature_selected(game_env, 5)
    b = make_mature(m, 6)
    b.value = 100.0
    for p in (a, b):
        p.state = m.PRESERVED
    a.clear_count = b.clear_count = 1
    a.soil_dip_ticks = m.CLEAR_CUT_HEAL_TICKS
    b.soil_dip_ticks = 0
    assert a.productivity_multiplier() < b.productivity_multiplier()
    assert a.accrue_tick() < b.accrue_tick()


def test_the_soil_never_drops_below_the_floor(game_env):
    m = game_env.module
    plot = _mature_selected(game_env)
    plot.clear_count = 9
    _cut(game_env)
    assert plot.productivity_multiplier() == m.MIN_PRODUCTIVITY_MULTIPLIER


def test_no_randomness_two_identical_runs_agree(game_env):
    m = game_env.module
    plot = _mature_selected(game_env)
    _cut(game_env)
    first = (m.total_income, plot.soil_dip_ticks, plot.productivity_multiplier())
    game_env.reset_session()
    _mature_selected(game_env)
    _cut(game_env)
    assert first == (m.total_income, m.plots[5].soil_dip_ticks, m.plots[5].productivity_multiplier())


def test_clear_cut_marks_the_tile_and_the_tooltip(game_env):
    m = game_env.module
    _mature_selected(game_env)
    _cut(game_env)
    assert "plot-soil-dip" in tile(game_env, 5).className
    assert "soil-dip-mark" in tile_marks(game_env, 5)
    label = tile(game_env, 5).getAttribute("aria-label")
    assert "clear-cut soil dip" in label and "seasons" in label
    assert "healing" in game_env.elements["soil-hint"].innerText
    assert "heals by itself" in game_env.elements["soil-hint"].title
    assert "1 plot healing" in game_env.elements["clear-cut-status"].innerText
    assert "1 clear-cut so far" in game_env.elements["clear-cut-status"].innerText
    assert m.plots[5].soil_dip_ticks > 0


def test_the_button_follows_the_selected_plot(game_env):
    m = game_env.module
    button = game_env.elements["clear-cut-button"]
    assert button.disabled is True
    game_env.select(5)
    assert button.disabled is False
    assert "income now" in button.title
    m.plots[5].state = m.BARE
    game_env.select(5)
    assert button.disabled is True
    m.plots[6].state = m.REPLANTING
    game_env.select(6)
    assert button.disabled is True


def test_the_heart_tree_is_never_clear_cut(game_env):
    m = game_env.module
    m.heart_tree_index = 14
    game_env.select(14)
    assert game_env.elements["clear-cut-button"].disabled is True
    _cut(game_env)
    assert m.plots[14].state == m.PRESERVED and m.clear_cuts_total == 0


def test_survey_mode_does_not_plan_a_clear_cut(game_env):
    m = game_env.module
    m.survey_mode = True
    game_env.select(5)
    assert game_env.elements["clear-cut-button"].disabled is True
    _cut(game_env)
    assert m.survey_queue == [] and m.clear_cuts_total == 0


def test_the_hotkey_needs_a_selected_plot_then_cuts(game_env):
    m = game_env.module
    assert m.hotkey_clear_cut_selected() is False
    assert "press K" in game_env.elements["sr-announcer"].innerText
    game_env.select(5)
    assert m.hotkey_clear_cut_selected() is True
    assert m.plots[5].state == m.BARE and m.clear_cuts_total == 1


def test_undo_takes_back_the_bonus_the_dip_and_the_count(game_env):
    m = game_env.module
    plot = _mature_selected(game_env)
    income = m.total_income
    _cut(game_env)
    assert game_env.elements["undo-clear-button"].hidden is False
    assert "clear-cutting" in game_env.elements["undo-clear-button"].getAttribute("aria-label")
    assert m.undo_last_clear() is True
    assert m.total_income == income
    assert plot.state == m.PRESERVED and plot.soil_dip_ticks == 0 and plot.clear_count == 0
    assert m.clear_cuts_total == 0


def test_it_counts_as_an_ordinary_clear_for_the_permanent_soil_cost(game_env):
    m = game_env.module
    plot = _mature_selected(game_env)
    _cut(game_env)
    assert plot.clear_count == 1
    assert m._total_clear_count() == 1


def test_the_log_names_the_bonus(game_env):
    m = game_env.module
    _mature_selected(game_env)
    _cut(game_env)
    entry = [e for e in m.forest_log if e["kind"] == "clear"][-1]
    assert "Clear-cut" in entry["text"] and "+20.0 bonus" in entry["text"] and "3 seasons" in entry["text"]


# --- the Harvester badge --------------------------------------------------------------

def test_the_badge_text_names_the_clear_cuts(game_env):
    m = game_env.module
    _mature_selected(game_env)
    _cut(game_env)
    game_env.toggle_session_summary()
    game_env.tick()
    assert "1 clear-cut" in game_env.elements["session-summary-badge"].innerText
    assert "1 of them clear-cuts" in m.badge_share_text()


def test_quick_payout_is_earned_by_the_first_clear_cut_only(game_env):
    m = game_env.module
    _mature_selected(game_env, 5)
    game_env.clear()
    assert "quick_payout" not in m.achievement_ids_earned()
    _mature_selected(game_env, 6)
    _cut(game_env)
    assert "quick_payout" in m.achievement_ids_earned()


def test_harvester_needs_the_badge_and_a_clear_cut(game_env):
    m = game_env.module
    # Harvester by plain clears alone does not earn the achievement.
    for index in range(24):
        plot = m.plots[index]
        plot.state, plot.value, plot.ticks_intact = m.PRESERVED, 10.0, 5
        game_env.select(index)
        game_env.clear()
    assert m.playstyle_badge() == m.BADGE_HARVESTER
    assert "harvester_badge" not in m.achievement_ids_earned()
    plot = m.plots[30]
    plot.state, plot.value = m.PRESERVED, 10.0
    game_env.select(30)
    _cut(game_env)
    assert "harvester_badge" in m.achievement_ids_earned()
    assert "Harvester" in game_env.elements["achievement-toast"].innerText or m._harvester_badge_announced


def test_the_new_achievements_have_story_chapters_and_catalog_entries(game_env):
    m = game_env.module
    ids = {a["id"] for a in m.ACHIEVEMENTS}
    assert {"quick_payout", "harvester_badge"} <= ids
    chapters = json.load(open(m.__file__.replace("game.py", "story.json")))["chapters"]
    assert {"quick_payout", "harvester_badge"} <= {c["id"] for c in chapters}


# --- saves ----------------------------------------------------------------------------

def test_a_fresh_game_writes_no_new_keys(game_env):
    state = game_env.module.get_state()
    assert "clear_cuts_total" not in state
    assert all("soil_dip_ticks" not in p for p in state["plots"])


def test_the_dip_and_the_count_round_trip(game_env):
    m = game_env.module
    plot = _mature_selected(game_env)
    _cut(game_env)
    game_env.tick(10)
    state = json.loads(json.dumps(m.get_state()))
    assert state["clear_cuts_total"] == 1
    assert state["plots"][5]["soil_dip_ticks"] == plot.soil_dip_ticks
    game_env.reset_session()
    assert m.plots[5].soil_dip_ticks == 0 and m.clear_cuts_total == 0
    m.load_state(state)
    assert m.plots[5].soil_dip_ticks == state["plots"][5]["soil_dip_ticks"]
    assert m.clear_cuts_total == 1


def test_an_old_save_loads_unchanged_and_clears_a_live_dip(game_env):
    m = game_env.module
    _mature_selected(game_env)
    _cut(game_env)
    old = json.loads(json.dumps(m.get_state()))
    del old["clear_cuts_total"]
    for p in old["plots"]:
        p.pop("soil_dip_ticks", None)
    m.load_state(old)
    assert m.clear_cuts_total == 0
    assert all(p.soil_dip_ticks == 0 for p in m.plots)


def test_bad_saved_values_fall_back(game_env):
    m = game_env.module
    state = json.loads(json.dumps(m.get_state()))
    state["clear_cuts_total"] = True
    state["plots"][0]["soil_dip_ticks"] = True
    state["plots"][1]["soil_dip_ticks"] = "many"
    state["plots"][2]["soil_dip_ticks"] = 10 ** 9
    state["plots"][3]["soil_dip_ticks"] = -4
    state["plots"][4]["soil_dip_ticks"] = float("nan")
    m.load_state(state)
    assert m.clear_cuts_total == 0
    assert [m.plots[i].soil_dip_ticks for i in range(5)] == [0, 0, m.CLEAR_CUT_HEAL_TICKS, 0, 0]


# --- markup / phone dock ----------------------------------------------------------------

def test_the_button_hotkey_and_sheet_entry_exist_on_both_pages():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    for page in ("index.html", "pc.html"):
        html = (root / page).read_text()
        assert html.count('id="clear-cut-button"') == 1 and html.count('id="clear-cut-status"') == 1
        assert html.count('id="plot-sheet-cut"') == 1
        assert 'key !== "k"' in html and "hotkey_clear_cut_selected" in html


def test_the_phone_dock_scrolls_sideways_and_folds_the_tree_picker():
    import pathlib
    css = (pathlib.Path(__file__).resolve().parents[1] / "style.css").read_text()
    start = css.index("Mobile condensed action panel")
    block = css[start:css.index("Mobile docked stats + legend")]
    assert "overflow-x: auto" in block
    for needle in (".plot-note-row", ".species-label", "#species-select", "#species-note"):
        assert f".action-dock--expanded) {needle}" in block
