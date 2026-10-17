"""B-2 (2026-10-09): the legacy bonus as a chip with a tooltip naming its source and the cap. (part 2 of 3 of the old test_b_oct9.py)."""

from .pagefiles import game_css

# ---- B-9: lifetime statistics ----

def _memory_storage(m):
    store = {}
    m._read_local_storage_item = lambda key: store.get(key)
    m._write_local_storage_item = lambda key, value: store.__setitem__(key, value)
    return store

# ---- B-25: the counter-offer ----

def _request_on(m, index):
    reason = next(iter(m.STAKEHOLDER_REASON_TEXT))
    m.pending_stakeholder_request = {"plot_index": index, "reason": reason, "kind": m.STAKEHOLDER_KIND_CLEAR}


def test_empty_library_message(game_env):
    m = game_env.module
    _memory_storage(m)
    m.render_my_forests()
    assert "Nothing saved yet" in game_env.elements["my-forests-note"].innerText
    assert game_env.elements["my-forests-compare"].innerHTML == ""


# ---- B-3 replay scrubber ----

def test_frames_are_recorded_every_few_ticks(game_env):
    m = game_env.module
    m._replay_frames.clear()
    for tick in range(1, 21):
        m.forest_tick = tick
        m._record_replay_frame()
    assert [t for t, _ in m._replay_frames] == [1, 5, 10, 15, 20]
    assert all(len(letters) == len(m.plots) for _, letters in m._replay_frames)


def test_frames_are_thinned_and_spacing_doubles_when_full(game_env):
    m = game_env.module
    m._replay_frames.clear()
    m._replay_state["every"] = 1
    for tick in range(1, m.REPLAY_MAX_FRAMES + 10):
        m.forest_tick = tick
        m._record_replay_frame()
    assert len(m._replay_frames) <= m.REPLAY_MAX_FRAMES
    assert m._replay_state["every"] == 2
    ticks = [t for t, _ in m._replay_frames]
    assert ticks == sorted(ticks) and ticks[0] == 1


def test_replay_shows_a_plot_clearing_and_the_live_frame_is_last(game_env):
    m = game_env.module
    m._replay_frames.clear()
    m.forest_tick = 5
    before = m._plot_letters()
    m._record_replay_frame()
    m.plots[0].state = m.BARE
    m.forest_tick = 7
    frames = m.replay_frames()
    assert frames[0][1] == before and frames[-1] == (7, m._plot_letters())
    assert frames[0][1][0] != frames[-1][1][0]


def test_replay_svg_shows_letters_and_rejects_the_wrong_size(game_env):
    import xml.etree.ElementTree as ET
    m = game_env.module
    letters = m._plot_letters()
    svg = m.replay_grid_svg(letters)
    ET.fromstring(svg)
    assert svg.count("<rect") == len(m.plots) and ">P<" in svg
    assert m.replay_grid_svg("PB") == ""


def test_render_replay_follows_the_slider(game_env):
    m = game_env.module
    m._replay_frames.clear()
    for tick in (1, 5, 10):
        m.forest_tick = tick
        m._record_replay_frame()
    slider = game_env.elements["replay-slider"]
    slider.value = "0"
    m.render_replay()
    assert slider.max == "2" and "tick 1" in game_env.elements["replay-label"].innerText
    slider.value = "99"
    m.render_replay()
    assert slider.value == "2" and "tick 10" in game_env.elements["replay-label"].innerText


def test_new_session_clears_the_replay(game_env):
    m = game_env.module
    m.forest_tick = 5
    m._record_replay_frame()
    m.reset_session()
    assert m._replay_frames == [] or m._replay_frames[0][0] == 0


# ---- B-28 phone bottom sheet ----

class _ContextEvent:
    def __init__(self, tile_id):
        self.prevented = False
        self.target = type("T", (), {"closest": lambda self_, sel: type("Tile", (), {"id": tile_id})()})()

    def preventDefault(self):
        self.prevented = True


def test_desktop_contextmenu_never_opens_the_sheet(game_env):
    m = game_env.module
    m.is_phone_layout = lambda: False
    m.on_plot_contextmenu(_ContextEvent("plot-3"))
    assert m.plot_sheet_open is False and game_env.elements["plot-sheet"].hidden is True


def test_phone_long_press_opens_the_sheet_for_that_plot(game_env):
    m = game_env.module
    m.is_phone_layout = lambda: True
    event = _ContextEvent("plot-3")
    m.on_plot_contextmenu(event)
    assert event.prevented and m.selected_index == 3 and m.plot_sheet_open
    sheet = game_env.elements["plot-sheet"]
    assert sheet.hidden is False and m.plot_coordinate_label(3) in game_env.elements["plot-sheet-title"].innerText


def test_sheet_buttons_follow_the_plot_state(game_env):
    m = game_env.module
    m.selected_index = 3
    m.plots[3].state = m.BARE
    actions = m.plot_sheet_actions()
    assert actions["clear"][0] is False and actions["replant"][0] is True
    m.plots[3].state = m.PRESERVED
    actions = m.plot_sheet_actions()
    assert actions["clear"][0] is True and actions["replant"][0] is False
    m.adopted_plot_index = 3
    assert m.plot_sheet_actions()["adopt"][1] == "Release plot"


def test_sheet_actions_run_the_normal_handlers_and_close(game_env):
    m = game_env.module
    m.is_phone_layout = lambda: True
    m.select_plot(2)
    m.plots[2].state = m.PRESERVED
    m.plots[2].value = 10.0
    m.open_plot_sheet()
    income = m.total_income
    m.on_plot_sheet_action("clear")
    assert m.plots[2].state == m.BARE and m.total_income > income
    assert m.plot_sheet_open is False and game_env.elements["plot-sheet"].hidden is True
    m.open_plot_sheet()
    m.on_plot_sheet_action("replant")
    assert m.plots[2].state == m.REPLANTING


def test_sheet_stays_closed_with_no_selection(game_env):
    m = game_env.module
    m.selected_index = None
    m.open_plot_sheet()
    assert m.plot_sheet_open is False


# ---- B-13 Survey mode ----

def _standing(m, index, value):
    m.plots[index].state = m.PRESERVED
    m.plots[index].value = value


def test_tick_is_frozen_while_surveying(game_env):
    m = game_env.module
    ticks = m._session_ticks
    m.enter_survey_mode()
    m.tick()
    assert m._session_ticks == ticks and m.forest_tick == getattr(m, "forest_tick")
    m.cancel_survey()
    m.tick()
    assert m._session_ticks == ticks + 1


def test_clear_and_replant_queue_instead_of_acting(game_env):
    m = game_env.module
    _standing(m, 4, 12.0)
    m.select_plot(4)
    m.enter_survey_mode()
    m.on_clear()
    assert m.plots[4].state == m.PRESERVED and m.total_income == 0
    assert m.survey_queue == [{"kind": "clear", "plot": 4}]
    m.on_replant()  # allowed: the plan leaves the plot bare
    assert [i["kind"] for i in m.survey_queue] == ["clear", "replant"]
    assert m.plots[4].state == m.PRESERVED


def test_asking_twice_takes_the_action_back_out_and_invalid_ones_are_refused(game_env):
    m = game_env.module
    _standing(m, 4, 12.0)
    m.enter_survey_mode()
    assert m.queue_survey_action("clear", 4) is True
    assert m.queue_survey_action("clear", 4) is True and m.survey_queue == []
    assert m.queue_survey_action("replant", 4) is False  # still standing
    m.plots[5].state = m.BARE
    assert m.queue_survey_action("replant", 5) is True
    assert m.queue_survey_action("decline") is False  # no pending request


def test_projection_counts_income_value_loss_gap_and_soil(game_env):
    m = game_env.module
    _standing(m, 4, 12.0)
    _standing(m, 5, 8.0)
    m._session_ticks = 50
    m.enter_survey_mode()
    m.queue_survey_action("clear", 4)
    m.queue_survey_action("clear", 5)
    p = m.survey_projection()
    assert p["income"] == 20.0 and p["standing_after"] == p["standing_now"] - 20.0
    assert p["gap_after"] >= p["gap_now"] and len(p["soil"]) == 2 and all(pct < 100 for _l, pct in p["soil"])
    assert "Income +20.0" in m.survey_projection_text()
    assert m.plots[4].clear_count == 0  # projecting never changes the forest


def test_commit_runs_the_plan_in_order_and_resumes_time(game_env):
    m = game_env.module
    _standing(m, 4, 12.0)
    m.select_plot(1)
    m.enter_survey_mode()
    m.queue_survey_action("clear", 4)
    m.queue_survey_action("replant", 4)
    income = m.total_income
    assert m.commit_survey() == 2
    assert m.survey_mode is False and m.survey_queue == []
    assert m.plots[4].state == m.REPLANTING and m.total_income == income + 12.0
    assert m.selected_index == 1


def test_cancel_discards_the_plan(game_env):
    m = game_env.module
    _standing(m, 4, 12.0)
    m.enter_survey_mode()
    m.queue_survey_action("clear", 4)
    m.cancel_survey()
    assert m.survey_mode is False and m.plots[4].state == m.PRESERVED and m.total_income == 0


def test_a_queued_decline_runs_on_commit(game_env):
    m = game_env.module
    m.plots[14].value = 10.0
    _request_on(m, 14)
    m.enter_survey_mode()
    assert m.queue_survey_action("decline") is True
    assert m.pending_stakeholder_request is not None
    relations = m.community_relations
    m.commit_survey()
    assert m.pending_stakeholder_request is None and m.community_relations == relations + m.STAKEHOLDER_DECLINE_RELATIONS_DELTA


def test_panel_renders_the_queue_and_hides_when_off(game_env):
    m = game_env.module
    _standing(m, 4, 12.0)
    m.render_survey()
    assert game_env.elements["survey-panel"].hidden is True
    m.enter_survey_mode()
    m.queue_survey_action("clear", 4)
    assert game_env.elements["survey-panel"].hidden is False
    assert "Clear" in game_env.elements["survey-queue"].innerHTML
    assert game_env.elements["survey-commit-button"].disabled is False


# ---- B-5 Forest Lab ----

def test_lab_values_are_snapped_and_clamped(game_env):
    m = game_env.module
    assert m.clean_lab_value(1.1) == 1.0 and m.clean_lab_value(9) == 2.0 and m.clean_lab_value(0) == 0.5
    assert m.clean_lab_value("x") == 1.0 and m.clean_lab_value(True) == 1.0 and m.clean_lab_value(float("nan")) == 1.0


def test_default_lab_is_the_normal_game(game_env):
    m = game_env.module
    assert m.lab_active() is False
    assert m.growth_per_tick() == m.GROWTH_PER_TICK
    assert m.current_season_multiplier() == m.SEASON_GROWTH_MULTIPLIER[m.current_season()]
    assert m.current_degrade_per_clear() == m.DEGRADE_PER_CLEAR * m.vault_soil_factor()


def test_each_dial_changes_its_own_rule(game_env):
    m = game_env.module
    base_interval = m.current_request_interval()
    base_degrade = m.current_degrade_per_clear()
    m.lab["soil"] = 2.0
    assert m.current_degrade_per_clear() == base_degrade * 2
    m.lab["requests"] = 2.0
    assert m.current_request_interval() < base_interval
    m.lab["maturity"] = 2.0
    assert m.growth_per_tick() == m.GROWTH_PER_TICK * 2
    m.lab["season"] = 2.0
    winter = m.season_multiplier_for("winter")
    assert winter < m.SEASON_GROWTH_MULTIPLIER["winter"]
    m.lab["season"] = 0.5
    assert m.season_multiplier_for("spring") < m.SEASON_GROWTH_MULTIPLIER["spring"]


def test_faster_growth_grows_a_plot_faster(game_env):
    m = game_env.module
    a, b = m.Plot(0), m.Plot(1)
    for _ in range(10):
        a.accrue_tick()
    m.lab["maturity"] = 2.0
    for _ in range(10):
        b.accrue_tick()
    assert b.value > a.value


def test_apply_starts_a_new_forest_and_banks_the_old_one_normally(game_env):
    import json
    m = game_env.module
    store = _memory_storage(m)
    m._session_ticks = 30
    m.lab_pending["soil"] = 2.0
    m.apply_lab()
    assert m.lab["soil"] == 2.0 and m.lab_active() and m._session_ticks == 0
    assert json.loads(store[m.LIFETIME_STORAGE_KEY])["sessions"] == 1  # the normal forest was banked
    m._session_ticks = 30
    m.reset_session()
    assert json.loads(store[m.LIFETIME_STORAGE_KEY])["sessions"] == 1  # the sandbox forest was not


def test_sandbox_forests_set_no_bests_legacy_or_my_forests(game_env):
    m = game_env.module
    store = _memory_storage(m)
    m.lab["maturity"] = 1.5
    m._session_ticks = 40
    m.plots[0].value = 500.0
    m._maybe_update_personal_best()
    assert m.PERSONAL_BEST_STORAGE_KEY not in store
    m._bank_legacy_value()
    assert m.LEGACY_STORAGE_KEY not in store
    m._bank_lifetime()
    assert m.MY_FORESTS_KEY not in store and m.LIFETIME_STORAGE_KEY not in store
    assert "Forest Lab sandbox" in m.session_tag_text()


def test_lab_is_saved_only_when_set_and_loads_safely(game_env):
    m = game_env.module
    assert "lab" not in m.get_state()
    m.lab["soil"] = 1.5
    state = m.get_state()
    assert state["lab"]["soil"] == 1.5
    m.lab["soil"] = 1.0
    m.load_state(state)
    assert m.lab["soil"] == 1.5
    bad = m.get_state()
    bad["lab"] = {"soil": 99, "season": "x", "extra": 3}
    m.load_state(bad)
    assert m.lab["soil"] == 2.0 and m.lab["season"] == 1.0
    bad.pop("lab")
    m.load_state(bad)
    assert m.lab_active() is False


def test_variants_save_load_and_cap(game_env):
    m = game_env.module
    _memory_storage(m)
    m.lab_pending.update({"soil": 2.0, "maturity": 0.5})
    assert m.save_lab_variant("  Harsh   soil ") == "Harsh soil"
    for i in range(8):
        m.save_lab_variant(f"V{i}")
    names = [v["name"] for v in m.load_lab_variants()]
    assert len(names) == m.LAB_VARIANTS_MAX and "Harsh soil" not in names
    m.lab_pending.update({"soil": 1.0, "maturity": 1.0})
    assert m.load_lab_variant("V7") and m.lab_pending["soil"] == 2.0
    assert m.load_lab_variant("missing") is False


def test_panel_stages_values_without_changing_the_forest_and_shows_the_banner(game_env):
    m = game_env.module
    _memory_storage(m)
    game_env.elements["lab-soil"].value = "2"
    m.on_lab_slider("soil")
    assert m.lab_pending["soil"] == 2.0 and m.lab["soil"] == 1.0
    assert "Apply" in game_env.elements["lab-status"].innerText
    assert game_env.elements["lab-banner"].hidden is True
    m.on_lab_apply()
    assert game_env.elements["lab-banner"].hidden is False and "Sandbox" in game_env.elements["lab-banner"].innerText
    m.reset_lab_to_normal()
    assert m.lab_pending["soil"] == 1.0 and m.lab["soil"] == 2.0


# ---- GB-6 species on replant ----

def _bare(m, index=0):
    plot = m.plots[index]
    plot.state = m.BARE
    plot.value = 0.0
    return plot


def test_species_change_recovery_time(game_env):
    m = game_env.module
    base = m.RECOVERY_TICKS
    for species, expected in (("standard", base), ("pine", max(1, round(base * 0.5))), ("oak", base * 2), ("orchard", base)):
        plot = _bare(m)
        assert plot.replant(species=species)
        assert plot.replant_ticks_remaining == expected
        assert plot.species == (None if species == "standard" else species)


def test_species_value_and_biodiversity_rules(game_env):
    m = game_env.module

    def grown(species, ticks=40):
        plot = m.Plot(0)
        plot.state = m.RECOVERED
        plot.species = species
        for _ in range(ticks):
            plot.accrue_tick()
        return plot
    standard, pine, oak, orchard = grown(None), grown("pine"), grown("oak"), grown("orchard")
    assert pine.value < standard.value < oak.value
    assert oak.biodiversity > standard.biodiversity > 0 and orchard.biodiversity == 0
    assert orchard.value < standard.value  # it stops compounding after 30 ticks
    steady = grown("orchard", 60).value - grown("orchard", 59).value
    assert abs(steady - (grown("orchard", 61).value - grown("orchard", 60).value)) < 1e-9


def test_mixed_forest_bonus_counts_distinct_standing_species(game_env):
    m = game_env.module
    assert m.mixed_forest_multiplier() == 1.0
    m.plots[0].species, m.plots[1].species = "pine", "pine"
    assert m.mixed_forest_multiplier() == 1.0
    m.plots[2].species = "oak"
    assert abs(m.mixed_forest_multiplier() - 1.05) < 1e-9
    m.plots[3].species = "orchard"
    assert abs(m.mixed_forest_multiplier() - 1.10) < 1e-9
    m.plots[3].state = m.BARE  # a bare plot does not count
    assert abs(m.mixed_forest_multiplier() - 1.05) < 1e-9


def test_clearing_forgets_the_species_and_the_replant_picker_is_used(game_env):
    m = game_env.module
    m.plots[2].species = "oak"
    m.plots[2].clear()
    assert m.plots[2].species is None
    m.species_choice = "pine"
    m.selected_index = 2
    m.on_replant()
    assert m.plots[2].species == "pine" and "pine" in m.species_planted
    assert any("Pioneer pine".lower() in e["text"] for e in m.forest_log)


def test_species_save_load_and_old_saves(game_env):
    m = game_env.module
    assert "species_planted" not in m.get_state() and "species" not in m.get_state()["plots"][0]
    m.plots[3].species = "oak"
    m.species_planted.add("oak")
    state = m.get_state()
    assert state["plots"][3]["species"] == "oak" and state["species_planted"] == ["oak"]
    m.plots[3].species = None
    m.species_planted.clear()
    m.load_state(state)
    assert m.plots[3].species == "oak" and "oak" in m.species_planted
    state["plots"][3]["species"] = "banyan"
    state["species_planted"] = ["standard", "banyan", 7]
    m.load_state(state)
    assert m.plots[3].species is None and not m.species_planted


def test_replant_progress_fraction_uses_the_species_wait(game_env):
    m = game_env.module
    plot = _bare(m)
    plot.replant(species="oak")
    assert plot.maturity_fraction() == 0.0
    plot.replant_ticks_remaining = plot.replant_ticks_total // 2
    assert abs(plot.maturity_fraction() - 0.5) < 1e-9


def test_species_marks_and_picker_note(game_env):
    m = game_env.module
    m.plots[1].species = "orchard"
    m.render_grid()
    tile = game_env.elements["plot-grid"].children[1]
    assert "plot-species--orchard" in tile.className and "Orchard" in tile.getAttribute("data-tooltip")
    m.species_choice = "oak"
    m.render_species_note()
    assert "Hardwood oak" in game_env.elements["species-note"].innerText


# ---- GB-7 blight in monocultures ----

def _plant_row(m, indexes, species="oak"):
    for i in indexes:
        m.plots[i].state = m.PRESERVED
        m.plots[i].species = species
        m.plots[i].value = 10.0 + i


def test_patches_are_connected_groups_of_one_species(game_env):
    m = game_env.module
    for p in m.plots:
        p.species = None
    _plant_row(m, [0, 1, 2], "oak")
    _plant_row(m, [3], "pine")      # a neighbour of another species does not join
    _plant_row(m, [13, 14], "oak")  # two rows down: not adjacent to 0-2
    patches = m.species_patches()
    assert [0, 1, 2] in patches and [3] in patches and [13, 14] in patches
    m.plots[0].species = None
    assert all(0 not in p for p in m.species_patches())


def test_standard_seedlings_and_bare_plots_never_form_patches(game_env):
    m = game_env.module
    assert m.species_patches() == []
    _plant_row(m, [0, 1, 2, 3, 4], "oak")
    m.plots[2].state = m.BARE
    assert [0, 1] in m.species_patches() and [3, 4] in m.species_patches()


def test_small_patches_never_gather_pressure(game_env):
    m = game_env.module
    _plant_row(m, [0, 1, 2, 3], "oak")  # one short of BLIGHT_MIN_PATCH
    for _ in range(100):
        m._blight_tick()
    assert m.blight_pressure == {} and all(m.plots[i].state == m.PRESERVED for i in range(4))


def test_a_big_patch_is_warned_then_loses_its_least_valuable_plot_every_ten_ticks(game_env):
    m = game_env.module
    _plant_row(m, [0, 1, 2, 3, 4], "oak")
    for _ in range(m.BLIGHT_WARN_TICKS):
        m._blight_tick()
    assert any(e["kind"] == "blight" and "warning" in e["text"] for e in m.forest_log)
    assert "blight warning" in m.blight_status_for(0)
    assert all(m.plots[i].state == m.PRESERVED for i in range(5))
    for _ in range(m.BLIGHT_HIT_TICKS - m.BLIGHT_WARN_TICKS):
        m._blight_tick()
    assert m.plots[0].state == m.BARE and m.plots[0].species is None and m.plots[0].clear_count == 0
    assert [m.plots[i].state for i in range(1, 5)] == [m.PRESERVED] * 4
    for _ in range(m.BLIGHT_SPREAD_TICKS):
        m._blight_tick()
    assert m.plots[1].state == m.BARE
    # The blight keeps working through the patch while two or more plots remain, and leaves the last one alone.
    for _ in range(m.BLIGHT_SPREAD_TICKS * 5):
        m._blight_tick()
    assert [m.plots[i].state for i in range(5)].count(m.PRESERVED) == 1


def test_tending_a_plot_in_the_patch_resets_the_pressure(game_env):
    m = game_env.module
    _plant_row(m, [0, 1, 2, 3, 4], "oak")
    for _ in range(50):
        m._blight_tick()
    assert m.blight_pressure[0] == 50
    m.selected_index = 2
    assert m.tend_plot(2) is True
    assert m.blight_pressure == {}


def test_a_different_species_in_the_middle_breaks_the_patch(game_env):
    m = game_env.module
    _plant_row(m, [0, 1, 2, 3, 4], "oak")
    for _ in range(45):
        m._blight_tick()
    m.plots[2].species = "pine"
    m._blight_tick()
    assert m.blight_pressure == {}  # two small patches of two remain, no pressure


def test_blight_can_be_switched_off_and_is_not_saved(game_env):
    m = game_env.module
    _plant_row(m, [0, 1, 2, 3, 4], "oak")
    m.ui_pref = lambda key, default="": "true" if key == m.UI_PREF_BLIGHT_OFF else default
    for _ in range(100):
        m._blight_tick()
    assert all(m.plots[i].state == m.PRESERVED for i in range(5))
    m.ui_pref = lambda key, default="": default
    m._blight_tick()
    assert m.blight_pressure
    assert "blight_pressure" not in m.get_state()
    m.load_state(m.get_state())
    assert m.blight_pressure == {}


# ---- GB-5 neighbour synergy ----

def _mature(m, index, ticks=None):
    plot = m.plots[index]
    plot.state = m.PRESERVED
    plot.ticks_intact = m.MATURITY_TICKS if ticks is None else ticks
    return plot


def test_edge_neighbours_respect_the_grid_edges(game_env):
    m = game_env.module
    cols = m.GRID_COLS
    assert sorted(m._edge_neighbours(0)) == [1, cols]
    assert sorted(m._edge_neighbours(cols - 1)) == [cols - 2, 2 * cols - 1]
    assert len(m._edge_neighbours(cols + 1)) == 4


def test_synergy_needs_the_plot_and_its_neighbours_to_be_mature(game_env):
    m = game_env.module
    for p in m.plots:
        p.ticks_intact = 0
    centre = m.GRID_COLS + 1
    _mature(m, centre)
    assert m.synergy_multiplier(m.plots[centre]) == 1.0  # alone
    _mature(m, centre - 1)
    _mature(m, centre + 1)
    assert abs(m.synergy_multiplier(m.plots[centre]) - (1 + 2 * m.SYNERGY_PER_NEIGHBOUR)) < 1e-9
    m.plots[centre - 1].ticks_intact = m.MATURITY_TICKS - 1  # not quite mature
    assert abs(m.synergy_multiplier(m.plots[centre]) - (1 + m.SYNERGY_PER_NEIGHBOUR)) < 1e-9
    m.plots[centre].ticks_intact = 5
    assert m.synergy_multiplier(m.plots[centre]) == 1.0  # the plot itself must be mature


def test_a_solid_block_outgrows_a_checkerboard(game_env):
    m = game_env.module
    for p in m.plots:
        p.state, p.ticks_intact, p.value = m.BARE, 0, 0.0
    cols = m.GRID_COLS
    block = [0, 1, cols, cols + 1]
    for i in block:
        _mature(m, i)
    solid = m.plots[0].accrue_tick()
    for p in m.plots:
        p.state, p.ticks_intact = m.BARE, 0
    for i in (0, 2, cols + 1, cols + 3):  # no two share an edge
        _mature(m, i)
    spaced = m.plots[0].accrue_tick()
    assert solid > spaced


def test_replant_next_to_a_mature_plot_recovers_faster(game_env):
    m = game_env.module
    for p in m.plots:
        p.state, p.ticks_intact = m.BARE, 0
    lone = m.plots[0]
    lone.replant()
    assert lone.replant_ticks_remaining == m.RECOVERY_TICKS
    _mature(m, 1)
    lone.state = m.BARE
    lone.replant()
    assert lone.replant_ticks_remaining == round(m.RECOVERY_TICKS * m.SYNERGY_REPLANT_FACTOR)


def test_other_regions_get_no_synergy(game_env):
    m = game_env.module
    plot = m.Plot(0, region="highland")
    plot.state, plot.ticks_intact = m.PRESERVED, m.MATURITY_TICKS
    assert m.synergy_multiplier(plot) == 1.0


def test_link_marks_appear_and_can_be_hidden(game_env):
    m = game_env.module
    for p in m.plots:
        p.ticks_intact = 0
    _mature(m, 0)
    _mature(m, 1)
    m.render_grid()
    tile = game_env.elements["plot-grid"].children[0]
    assert "plot-linked" in tile.className and "canopy link" in tile.getAttribute("data-tooltip")
    assert any(getattr(c, "className", "") == "link-mark" for c in tile.children)
    m.ui_pref = lambda key, default="": "true" if key == m.UI_PREF_SYNERGY_MARKS_OFF else default
    m.render_grid()
    tile = game_env.elements["plot-grid"].children[0]
    assert "plot-linked" not in tile.className and "canopy link" in tile.getAttribute("data-tooltip")


# ---- GB-25 stakeholder faces ----

def test_each_reason_has_a_recurring_character(game_env):
    m = game_env.module
    for reason in list(m.STAKEHOLDER_REASONS) + list(m.STAKEHOLDER_INCENTIVE_REASONS):
        assert m.REASON_FACE[reason] in m.FACES
    assert m.face_for_request({"reason": "housing", "kind": m.STAKEHOLDER_KIND_CLEAR}) == "mayor"
    assert m.face_for_request({"reason": "x", "kind": m.STAKEHOLDER_KIND_REPLANT_GRANT}) == "ranger"
    assert m.face_for_request(None) is None


def test_choices_build_trust_and_a_decline_only_changes_the_mood(game_env):
    m = game_env.module
    req = {"reason": "farming", "kind": m.STAKEHOLDER_KIND_CLEAR}
    assert m.face_mood("farmer") == "reserved"
    m.note_face_choice("granted", req, m.STAKEHOLDER_KIND_CLEAR)
    assert m.stakeholder_faces["farmer"]["trust"] == 1 and m.face_mood("farmer") == "pleased"
    m.note_face_choice("countered", req, m.STAKEHOLDER_KIND_CLEAR)
    assert m.stakeholder_faces["farmer"]["trust"] == 3 and m.face_mood("farmer") == "friendly"
    m.note_face_choice("declined", req, m.STAKEHOLDER_KIND_CLEAR)
    assert m.stakeholder_faces["farmer"]["trust"] == 3 and m.face_mood("farmer") == "disappointed"
    incentive = {"reason": "ecotourism", "kind": m.STAKEHOLDER_KIND_INCENTIVE}
    m.note_face_choice("granted", incentive, m.STAKEHOLDER_KIND_INCENTIVE)
    assert m.stakeholder_faces["broker"]["trust"] == 2 and m.stakeholder_faces["broker"]["last"] == "accepted"


def test_trust_is_capped_and_perks_stretch_the_request_gap(game_env):
    m = game_env.module
    base = m.current_request_interval()
    m.stakeholder_faces["mayor"] = {"trust": 5, "last": "granted", "met": 5}
    assert m.friendship_interval_factor() == 1.1 and m.current_request_interval() > base
    m.stakeholder_faces["farmer"] = {"trust": 9, "last": "granted", "met": 9}
    assert abs(m.friendship_interval_factor() - 1.3) < 1e-9
    for face in ("foreman", "broker", "ranger"):
        m.stakeholder_faces[face] = {"trust": 10, "last": "granted", "met": 9}
    assert m.friendship_interval_factor() == 1.5  # capped
    req = {"reason": "housing", "kind": m.STAKEHOLDER_KIND_CLEAR}
    for _ in range(30):
        m.note_face_choice("countered", req, m.STAKEHOLDER_KIND_CLEAR)
    assert m.stakeholder_faces["mayor"]["trust"] == m.FACE_TRUST_MAX


def test_real_answers_flow_through_the_request_handlers(game_env):
    m = game_env.module
    m.plots[14].value = 10.0
    _request_on(m, 14)
    reason = m.pending_stakeholder_request["reason"]
    face = m.REASON_FACE.get(reason)
    m.grant_stakeholder_request()
    assert m.stakeholder_faces[face]["met"] == 1 and m.stakeholder_faces[face]["last"] == "granted"


def test_portrait_is_valid_svg_and_names_the_mood(game_env):
    import xml.etree.ElementTree as ET
    m = game_env.module
    for face_id in m.FACES:
        ET.fromstring(m.face_portrait_svg(face_id))
    m.stakeholder_faces["mayor"] = {"trust": 0, "last": "declined", "met": 1}
    assert "disappointed" in m.face_portrait_svg("mayor")


def test_panel_and_summary_show_the_character(game_env):
    m = game_env.module
    m.plots[14].value = 10.0
    _request_on(m, 14)
    m.render_stakeholder_panel()
    assert "<svg" in game_env.elements["stakeholder-face"].innerHTML
    assert game_env.elements["stakeholder-speaker"].innerText
    assert "Nobody met yet" in game_env.elements["faces-list"].innerText
    m.stakeholder_faces["mayor"] = {"trust": 5, "last": "granted", "met": 2}
    m.render_faces()
    assert "Mayor Odalys" in game_env.elements["faces-list"].innerText and "Perk" in game_env.elements["faces-list"].innerText


def test_faces_save_load_validate_and_reset(game_env):
    m = game_env.module
    assert "stakeholder_faces" not in m.get_state()
    m.stakeholder_faces["ranger"] = {"trust": 4, "last": "accepted", "met": 3}
    state = m.get_state()
    m.stakeholder_faces.clear()
    m.load_state(state)
    assert m.stakeholder_faces["ranger"] == {"trust": 4, "last": "accepted", "met": 3}
    state["stakeholder_faces"] = {"ranger": {"trust": 99, "last": "weird", "met": "x"}, "ghost": {"trust": 1}, "mayor": 5}
    m.load_state(state)
    assert m.stakeholder_faces == {"ranger": {"trust": 10, "last": "", "met": 0}}
    m.reset_session()
    assert m.stakeholder_faces == {}


# ---- B-17 tile sprites ----

def test_sprite_kind_follows_the_growth_stage(game_env):
    m = game_env.module
    plot = m.plots[0]
    plot.state, plot.ticks_intact = m.PRESERVED, 3
    assert m.sprite_kind(plot) == "tree"
    plot.ticks_intact = m.MATURITY_TICKS
    assert m.sprite_kind(plot) == "mature"
    plot.state = m.REPLANTING
    assert m.sprite_kind(plot) == "sapling"
    plot.state = m.BARE
    assert m.sprite_kind(plot) == "stump"


def test_every_tile_gets_a_sprite_unless_switched_off(game_env):
    m = game_env.module
    m.plots[1].state = m.BARE
    m.render_grid()
    grid = game_env.elements["plot-grid"]
    sprites = [[c.className for c in t.children if c.className.startswith("tile-sprite")] for t in grid.children]
    assert all(len(s) == 1 for s in sprites)
    assert sprites[1] == ["tile-sprite tile-sprite--stump"]
    m.ui_pref = lambda key, default="": "true" if key == m.UI_PREF_SPRITES_OFF else default
    m.render_grid()
    assert all(not c.className.startswith("tile-sprite") for t in game_env.elements["plot-grid"].children for c in t.children)


def test_the_season_is_published_for_the_foliage_colours(game_env):
    m = game_env.module
    m.forest_tick = 0
    m.render_season_indicator()
    assert game_env.module.document.documentElement.getAttribute("data-season") == "spring"
    m.forest_tick = m.SEASON_CYCLE_TICKS * 2
    m.render_season_indicator()
    assert game_env.module.document.documentElement.getAttribute("data-season") == "autumn"


def test_sprite_css_respects_reduced_motion_and_perf_mode(game_env):
    css = game_css()
    assert 'html[data-reduced-motion="true"] .tile-sprite' in css and 'data-perf-mode="on"] .tile-sprite' in css
    assert "@media (prefers-reduced-motion: reduce) { .tile-sprite { animation: none; } }" in css


# ---- GB-1 wildfire season ----

def _wildfire(m):
    m.current_difficulty = m.DIFFICULTY_WILDFIRE
    m._reset_fire()
    for p in m.plots:
        p.state, p.value, p.ticks_intact = m.PRESERVED, 20.0, 5
    m.heart_tree_index = None


def test_fire_only_exists_on_the_wildfire_difficulty(game_env):
    m = game_env.module
    m.forest_tick = 90
    for _ in range(200):
        m.forest_tick += 1
        m._fire_tick()
    assert m.fires == {} and m.fire_warning is None and m.fire_status_text() == ""


def test_ignition_schedule_is_deterministic_and_seasonal(game_env):
    m = game_env.module
    blocks = range(0, 200)
    schedule = [m.fire_ignition_tick(b) for b in blocks]
    assert schedule == [m.fire_ignition_tick(b) for b in blocks]
    for b, t in zip(blocks, schedule):
        season = m._season_at(b * m.FIRE_BLOCK_TICKS + m.FIRE_BLOCK_TICKS // 2)
        if season in ("spring", "winter"):
            assert t is None
        if t is not None:
            assert b * m.FIRE_BLOCK_TICKS + m.FIRE_WARNING_TICKS <= t < (b + 1) * m.FIRE_BLOCK_TICKS
    summer_blocks = [b for b in blocks if m._season_at(b * m.FIRE_BLOCK_TICKS + 15) == "summer"]
    assert all(m.fire_ignition_tick(b) is not None for b in summer_blocks)
    autumn_blocks = [b for b in blocks if m._season_at(b * m.FIRE_BLOCK_TICKS + 15) == "autumn"]
    assert 0 < sum(1 for b in autumn_blocks if m.fire_ignition_tick(b) is not None) < len(autumn_blocks)


def _first_summer_block(m):
    return next(b for b in range(0, 100) if m._season_at(b * m.FIRE_BLOCK_TICKS + 15) == "summer" and m.fire_ignition_tick(b) is not None)
