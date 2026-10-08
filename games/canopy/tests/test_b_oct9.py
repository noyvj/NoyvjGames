"""B-2 (2026-10-09): the legacy bonus as a chip with a tooltip naming its source and the cap."""


def test_chip_says_none_before_anything_is_banked(game_env):
    m = game_env.module
    m.legacy_multiplier = 1.0
    assert m.legacy_chip_text() == "Legacy: none yet"
    assert "none yet" in m.legacy_chip_tooltip()
    assert "+25%" in m.legacy_chip_tooltip()


def test_chip_shows_the_percentage_and_the_tooltip_names_source_and_cap_share(game_env):
    m = game_env.module
    m.legacy_multiplier = m.legacy_bonus_for(250)  # +5%
    m._read_banked_legacy_value = lambda: 250.0
    assert m.legacy_chip_text() == "Legacy +5% from your last forest"
    tip = m.legacy_chip_tooltip()
    assert "250 standing forest value" in tip
    assert "0.02% per point" in tip
    assert "20% of it" in tip  # 5% of a 25% cap


def test_cap_is_explained_when_reached(game_env):
    m = game_env.module
    m.legacy_multiplier = m.legacy_bonus_for(5000)  # well past the cap
    m._read_banked_legacy_value = lambda: 5000.0
    assert m.legacy_multiplier == 1.0 + m.LEGACY_MAX_BONUS
    assert "100% of it" in m.legacy_chip_tooltip()
    assert "no longer adds growth" in m.legacy_chip_tooltip()


def test_bonus_function_is_capped_and_never_negative(game_env):
    m = game_env.module
    assert m.legacy_bonus_for(-50) == 1.0
    assert m.legacy_bonus_for(0) == 1.0
    assert m.legacy_bonus_for(10 ** 9) == 1.0 + m.LEGACY_MAX_BONUS


def test_render_sets_the_chip_title_and_label(game_env):
    m = game_env.module
    m.legacy_multiplier = m.legacy_bonus_for(250)
    m._read_banked_legacy_value = lambda: 250.0
    m.render_legacy_bonus()
    el = game_env.elements["legacy-bonus-display"]
    assert el.innerText == "Legacy +5% from your last forest"
    assert el.title == m.legacy_chip_tooltip()


# ---- B-22: the while-away chip ----

def _snap(value, ticks, seasons=0):
    return {"value": value, "ticks": ticks, "seasons": seasons}


def test_no_chip_when_away_briefly_or_nothing_advanced(game_env):
    m = game_env.module
    assert m.away_summary(_snap(10, 5), _snap(30, 9), m.AWAY_MIN_SECONDS - 1) == ""
    assert m.away_summary(_snap(10, 5), _snap(10, 5), 600) == ""  # paused while hidden: nothing to explain


def test_chip_text_has_value_ticks_and_season_changes(game_env):
    m = game_env.module
    text = m.away_summary(_snap(100.0, 10, 1), _snap(314.2, 70, 3), 125)
    assert text == "While you were away (2 min 5 s): standing value +214.2, 60 ticks, 2 season changes."
    one = m.away_summary(_snap(5.0, 0), _snap(4.0, 1), 30)
    assert one == "While you were away (30 s): standing value -1.0, 1 tick."


def test_show_and_dismiss_the_chip(game_env):
    m = game_env.module
    chip = game_env.elements["away-chip"]
    m.show_away_chip("While you were away (30 s): standing value +1.0, 3 ticks.")
    assert chip.hidden is False and chip.innerText.endswith("(click to dismiss)")
    m.on_dismiss_away_chip()
    assert chip.hidden is True


def test_visibility_cycle_shows_a_chip_only_if_the_forest_advanced(game_env):
    m = game_env.module
    m.document.visibilityState = "hidden"
    m.on_visibility_change()
    m._away_started_at -= 120  # two minutes away
    m._session_ticks += 40  # the forest kept ticking in the background
    m.document.visibilityState = "visible"
    m.on_visibility_change()
    assert game_env.elements["away-chip"].hidden is False
    assert "40 ticks" in game_env.elements["away-chip"].innerText
    # a second cycle with no ticks shows nothing
    m.document.visibilityState = "hidden"
    m.on_visibility_change()
    m._away_started_at -= 120
    m.document.visibilityState = "visible"
    m.on_visibility_change()
    assert game_env.elements["away-chip"].hidden is True


# ---- B-14: the request-history table ----

def _answer(m, grant, plot_index=None):
    """Raise a clear request on a standing plot and answer it."""
    target = plot_index if plot_index is not None else m._most_established_plot_index()
    m.pending_stakeholder_request = {"plot_index": target, "reason": "jobs", "kind": m.STAKEHOLDER_KIND_CLEAR}
    return (m.grant_stakeholder_request if grant else m.decline_stakeholder_request)()


def test_declined_and_granted_requests_are_recorded(game_env):
    m = game_env.module
    for plot in m.plots[:3]:
        plot.value = 10.0
    _answer(m, grant=False, plot_index=0)
    _answer(m, grant=True, plot_index=1)
    assert [e["choice"] for e in m.request_history] == ["declined", "granted"]
    assert m.request_history[0]["plot"] == 0 and m.request_history[0]["value_then"] == 10.0
    assert m.request_history[1]["kind"] == m.STAKEHOLDER_KIND_CLEAR


def test_rows_sort_filter_and_show_the_change_since(game_env):
    m = game_env.module
    for plot in m.plots[:2]:
        plot.value = 20.0
    _answer(m, grant=False, plot_index=0)
    m.forest_tick += 5
    _answer(m, grant=True, plot_index=1)
    m.plots[0].value = 50.0  # the preserved plot kept growing
    rows = m.request_history_rows("delta-high")
    assert [r["choice"] for r in rows] == ["declined", "granted"]
    assert rows[0]["delta"] == 30.0 and rows[1]["delta"] <= 0
    assert [r["choice"] for r in m.request_history_rows("oldest")] == ["declined", "granted"]
    assert [r["choice"] for r in m.request_history_rows("newest")] == ["granted", "declined"]
    assert m.request_history_rows("newest", kind="incentive") == []


def test_history_is_saved_validated_and_reset(game_env):
    m = game_env.module
    m.plots[0].value = 10.0
    _answer(m, grant=False, plot_index=0)
    state = m.get_state()
    assert state["request_history"][0]["choice"] == "declined"
    state["request_history"].extend([
        {"tick": "x"}, {"kind": "bogus", "choice": "granted", "tick": 1, "plot": 0, "value_then": 1},
        {"kind": "clear", "choice": "maybe", "tick": 1, "plot": 0, "value_then": 1}, "junk", None,
    ])
    m.load_state(state)
    assert len(m.request_history) == 1
    m.reset_session()
    assert m.request_history == []


def test_old_saves_without_history_load(game_env):
    m = game_env.module
    state = m.get_state()
    state.pop("request_history", None)
    m.load_state(state)
    assert m.request_history == []


def test_table_text_and_empty_state(game_env):
    m = game_env.module
    m.render_request_history()
    assert "No answered requests yet" in game_env.elements["request-history-table"].innerText
    m.plots[0].value = 10.0
    _answer(m, grant=False, plot_index=0)
    m.render_request_history()
    text = game_env.elements["request-history-table"].innerText
    assert text.startswith("Plot | Request | Your choice | Value then | Change since")
    assert "Clear request | declined | 10.0 | +0.0" in text


# ---- B-24: plot notes ----

def test_notes_are_cleaned_truncated_and_removed_when_empty(game_env):
    m = game_env.module
    assert m.set_plot_note(3, "  hello   world \t") == "hello world"
    assert m.plot_notes == {3: "hello world"}
    assert m.set_plot_note(4, "x" * 50) == "x" * m.PLOT_NOTE_MAX
    assert m.set_plot_note(3, "   ") == ""
    assert 3 not in m.plot_notes
    assert m.set_plot_note(10 ** 6, "nope") == "" and 10 ** 6 not in m.plot_notes
    assert m.set_plot_note(-1, "nope") == ""
    assert m.clean_plot_note("a\x00b\x07c") == "abc"


def test_save_button_stores_the_note_on_the_selected_plot(game_env):
    m = game_env.module
    m.select_plot(5)
    game_env.elements["plot-note-input"].value = "old oak"
    m.on_save_plot_note()
    assert m.plot_notes[5] == "old oak"
    game_env.elements["plot-note-input"].value = ""
    m.on_save_plot_note()
    assert 5 not in m.plot_notes


def test_noted_tile_gets_a_class_title_and_dot(game_env):
    m = game_env.module
    m.set_plot_note(2, "check soil")
    m.render()
    tile = game_env.elements["plot-2"] if "plot-2" in game_env.elements else None
    grid = game_env.elements["plot-grid"]
    tiles = [c for c in getattr(grid, "children", []) if getattr(c, "id", "") == "plot-2"]
    tile = tiles[-1] if tiles else tile
    assert tile is not None
    assert "plot-has-note" in tile.className
    assert tile.title.endswith("note: check soil")
    assert any("note-mark" in getattr(c, "className", "") for c in tile.children)


def test_notes_save_validate_and_reset(game_env):
    m = game_env.module
    m.set_plot_note(1, "keep")
    state = m.get_state()
    assert state["plot_notes"] == {"1": "keep"}
    state["plot_notes"].update({"x": "bad key", "999": "out of range", "2": 5, "3": "y" * 99})
    m.load_state(state)
    assert m.plot_notes == {1: "keep", 3: "y" * m.PLOT_NOTE_MAX}
    m.reset_session()
    assert m.plot_notes == {}
    assert "plot_notes" not in m.get_state()


def test_tile_id_parsing_and_note_box_follows_the_selection(game_env):
    m = game_env.module
    assert m.plot_index_from_tile_id("plot-12") == 12
    for bad in ("highland-plot-3", "plot-", "plot-x", "plot-9999", None, ""):
        assert m.plot_index_from_tile_id(bad) is None
    m.set_plot_note(7, "seven")
    m._note_input_for = None
    m.select_plot(7)
    assert game_env.elements["plot-note-input"].value == "seven"


# ---- B-9: lifetime statistics ----

def _memory_storage(m):
    store = {}
    m._read_local_storage_item = lambda key: store.get(key)
    m._write_local_storage_item = lambda key, value: store.__setitem__(key, value)
    return store


def test_nothing_banked_when_the_session_never_ticked(game_env):
    m = game_env.module
    store = _memory_storage(m)
    m._session_ticks = 0
    m._bank_lifetime()
    assert store == {}
    assert dict(m.lifetime_rows())["Finished sessions"] == "0"


def test_banking_adds_totals_and_per_difficulty_averages(game_env):
    import json
    m = game_env.module
    store = _memory_storage(m)
    m._session_ticks = 600
    m.total_replants = 4
    m.plots[0].clear_count = 2
    m.plots[1].clear_count = 1
    m.current_difficulty = m.DIFFICULTY_NORMAL
    m._bank_lifetime()
    m._bank_lifetime()  # a second session with the same numbers
    life = json.loads(store[m.LIFETIME_STORAGE_KEY])
    assert (life["sessions"], life["clears"], life["replants"], life["ticks"]) == (2, 6, 8, 1200)
    assert life["by_difficulty"]["normal"]["n"] == 2


def test_rows_add_the_live_session_to_the_banked_ones(game_env):
    m = game_env.module
    _memory_storage(m)
    m._session_ticks = 3600
    m.plots[0].clear_count = 1
    m.reset_session()  # banks the ending session
    m._session_ticks = 1800
    m.plots[2].clear_count = 3
    rows = dict(m.lifetime_rows())
    assert rows["Finished sessions"] == "1"
    assert rows["Plots cleared (all time)"] == "4"
    assert rows["Time in the forest"] == "1.5 hours"
    assert any(label.startswith("Average standing value, normal") for label in rows)


def test_reset_session_banks_the_ending_session(game_env):
    m = game_env.module
    store = _memory_storage(m)
    m._session_ticks = 120
    m.reset_session()
    assert m.LIFETIME_STORAGE_KEY in store


def test_bad_stored_lifetime_is_sanitised(game_env):
    m = game_env.module
    store = _memory_storage(m)
    store[m.LIFETIME_STORAGE_KEY] = "not json"
    assert m.load_lifetime() == m._empty_lifetime()
    store[m.LIFETIME_STORAGE_KEY] = '{"sessions": -5, "clears": "x", "by_difficulty": {"ranger": {"n": "3", "sum": -2, "best": "oops"}, "bad": 7}}'
    life = m.load_lifetime()
    assert life["sessions"] == 0 and life["clears"] == 0
    assert "bad" not in life["by_difficulty"] and life["by_difficulty"].get("ranger") is None


def test_render_writes_the_table(game_env):
    m = game_env.module
    _memory_storage(m)
    m.render_lifetime_stats()
    assert "Finished sessions: 0" in game_env.elements["lifetime-stats-table"].innerText


# ---- B-11: scenario seeds ----

def test_scenario_layouts_on_the_default_grid(game_env):
    m = game_env.module
    rows, cols = m.GRID_ROWS, m.GRID_COLS
    clearcut = m.scenario_bare_indexes("clearcut", rows, cols)
    assert len(clearcut) == round(rows * cols * 0.6)
    assert clearcut == m.scenario_bare_indexes("clearcut", rows, cols)  # deterministic
    checker = m.scenario_bare_indexes("farmland", rows, cols)
    assert len(checker) == rows * cols // 2 and 0 in checker and 1 not in checker
    remnant = m.scenario_bare_indexes("remnant", rows, cols)
    standing = set(range(rows * cols)) - remnant
    assert len(standing) == 9  # one 3 x 3 core
    assert m.scenario_bare_indexes("none", rows, cols) == set()


def test_reset_with_a_scenario_builds_that_forest(game_env):
    m = game_env.module
    assert m.reset_session(scenario="farmland") is not False
    bare = [p.index for p in m.plots if p.state == m.BARE]
    assert len(bare) == len(m.plots) // 2
    m.reset_session(scenario="remnant")
    standing = [p for p in m.plots if p.state == m.PRESERVED]
    assert len(standing) == 9 and all(p.ticks_intact == m.SCENARIO_REMNANT_HEAD_START_TICKS for p in standing)
    assert m.reset_session(scenario="bogus") is False
    m.reset_session(scenario="none")
    assert all(p.state == m.PRESERVED for p in m.plots)


def test_a_challenge_overrides_the_scenario(game_env):
    m = game_env.module
    m.reset_session(scenario="remnant")
    m.reset_session(challenge="pacifist")
    assert m.current_scenario == m.SCENARIO_NONE
    assert all(p.state == m.PRESERVED for p in m.plots)


def test_each_scenario_keeps_its_own_best(game_env):
    import json
    m = game_env.module
    store = {}
    m._read_local_storage_item = lambda key: store.get(key)
    m._write_local_storage_item = lambda key, value: store.__setitem__(key, value)
    m.reset_session(scenario="remnant")
    m.plots[0].value = 500.0
    m._update_scenario_best()
    assert json.loads(store[m.SCENARIO_BESTS_STORAGE_KEY])["remnant"] >= 500.0
    m.reset_session(scenario="clearcut")
    assert m.scenario_best_text() == "Clear-cut Valley: no best yet"
    m.reset_session(scenario="remnant")
    assert m.scenario_best_text().startswith("Old-Growth Remnant best: standing")


def test_scenario_is_saved_only_when_chosen_and_validated(game_env):
    m = game_env.module
    assert "scenario" not in m.get_state()
    m.reset_session(scenario="clearcut")
    state = m.get_state()
    assert state["scenario"] == "clearcut"
    state["scenario"] = "junk"
    m.load_state(state)
    assert m.current_scenario == m.SCENARIO_NONE


# ---- B-4: the shareable forest card ----

def test_card_is_valid_xml_with_every_plot_and_the_headline_numbers(game_env):
    import xml.etree.ElementTree as ET
    m = game_env.module
    m.forest_name = 'Oak & "Ash" <grove>'
    svg = m.forest_card_svg()
    root = ET.fromstring(svg)  # raises if the markup is broken
    assert root.tag.endswith("svg") and root.get("width") == "1200" and root.get("height") == "630"
    texts = [t.text or "" for t in root.iter() if t.tag.endswith("text")]
    letters = [t for t in texts if t in ("P", "B", "R", "C")]
    assert len(letters) == len(m.plots)
    assert any('Oak & "Ash" <grove>' in t for t in texts)  # escaped in the file, intact when parsed
    fields = m.copy_result_fields()
    assert any(f"{fields['score']:.1f}" == t for t in texts)
    assert any(stat in texts for stat in fields["stats"])


def test_every_plot_state_has_a_colour_and_a_letter(game_env):
    m = game_env.module
    for state in (m.PRESERVED, m.BARE, m.REPLANTING, m.RECOVERED):
        colour, letter = m.CARD_STATE_STYLE[state]
        assert colour.startswith("#") and len(letter) == 1
    assert len({letter for _c, letter in m.CARD_STATE_STYLE.values()}) == 4


def test_bare_and_preserved_plots_appear_with_their_own_letters(game_env):
    m = game_env.module
    m.plots[0].state = m.BARE
    svg = m.forest_card_svg()
    assert svg.count(">B</text>") == 1 and svg.count(">P</text>") == len(m.plots) - 1


def test_download_is_a_safe_no_op_outside_the_browser(game_env):
    m = game_env.module
    assert m._download_text_file("x.svg", "<svg/>", "image/svg+xml") in (True, False)
    m.on_download_forest_card()  # must not raise


# ---- B-27: Coach hints ----

def _prefs(m, **values):
    store = {m.UI_PREF_COACH: values.get("coach")} if "coach" in values else {}
    m._read_local_storage_item = lambda key: store.get(key)


def test_no_hints_for_a_fresh_forest(game_env):
    m = game_env.module
    assert m.coach_hints() == []


def test_repeat_clear_hint_names_the_plot_and_its_soil(game_env):
    m = game_env.module
    m.plots[4].clear_count = 3
    ids = [h[0] for h in m.coach_hints()]
    assert f"repeat-clear-{m.plots[4].index}" in ids
    text = dict(m.coach_hints())[f"repeat-clear-{m.plots[4].index}"]
    assert "cleared 3 times" in text and "soil is now at" in text


def test_other_hints_fire_on_their_conditions(game_env):
    m = game_env.module
    for plot in m.plots[:4]:
        plot.state = m.BARE
    m.total_replants = 0
    m.community_relations = 10
    ids = [h[0] for h in m.coach_hints()]
    assert "replant-first" in ids and "relations-low" in ids
    m.total_replants = 2
    assert "replant-first" not in [h[0] for h in m.coach_hints()]


def test_hints_are_capped_and_can_be_dismissed(game_env):
    m = game_env.module
    m.plots[0].clear_count = 5
    for plot in m.plots[1:5]:
        plot.state = m.BARE
    m.community_relations = 0
    assert 1 <= len(m.coach_hints()) <= m.COACH_MAX_HINTS
    m.on_dismiss_coach_hints()
    assert m.coach_hints() == []
    m.reset_session()
    m.plots[0].clear_count = 5
    assert m.coach_hints() != []  # a new session starts with nothing dismissed


def test_panel_is_hidden_until_the_player_opts_in(game_env):
    m = game_env.module
    m.plots[0].clear_count = 4
    _prefs(m)
    m.render_coach_hints()
    assert game_env.elements["coach-hints-panel"].hidden is True
    _prefs(m, coach="true")
    m.render_coach_hints()
    assert game_env.elements["coach-hints-panel"].hidden is False
    assert game_env.elements["coach-hints"].innerText.startswith("• ")


# ---- B-30: the performance guard ----

def test_three_lagging_ticks_switch_the_guard_on_and_steady_ticks_switch_it_off(game_env):
    m = game_env.module
    m.perf_mode, m._perf_strikes, m._perf_steady = False, 0, 0
    slow = m.PERF_LAG_FACTOR * m.TICK_INTERVAL_MS / 1000 + 0.5
    assert m.update_perf_guard(slow) is False and m.update_perf_guard(slow) is False
    assert m.update_perf_guard(slow) is True and m.perf_mode is True
    for _ in range(m.PERF_STEADY_TICKS_TO_RECOVER - 1):
        assert m.update_perf_guard(1.0) is False
    assert m.perf_mode is True
    assert m.update_perf_guard(1.0) is True and m.perf_mode is False


def test_a_good_tick_in_between_does_not_reset_strikes_but_a_steady_run_does_recover(game_env):
    m = game_env.module
    m.perf_mode, m._perf_strikes, m._perf_steady = False, 0, 0
    slow = m.PERF_LAG_FACTOR * m.TICK_INTERVAL_MS / 1000 + 1
    m.update_perf_guard(slow)
    m.update_perf_guard(1.0)
    m.update_perf_guard(slow)
    m.update_perf_guard(slow)
    assert m.perf_mode is True  # three strikes in total


def test_indicator_text_and_attribute_follow_the_guard(game_env):
    m = game_env.module
    m.perf_mode = True
    m.render_perf_indicator()
    el = game_env.elements["perf-indicator"]
    assert el.hidden is False and "Performance mode" in el.innerText
    m.perf_mode = False
    m.render_perf_indicator()
    assert el.hidden is True and el.innerText == ""


def test_pops_are_skipped_while_throttled_but_values_still_grow(game_env):
    m = game_env.module
    m.perf_mode = True
    before = m.standing_forest_value()
    m.tick()
    assert m.standing_forest_value() > before
    assert m._pending_value_pops == {}
    m.perf_mode = False


# ---- B-25: the counter-offer ----

def _request_on(m, index):
    reason = next(iter(m.STAKEHOLDER_REASON_TEXT))
    m.pending_stakeholder_request = {"plot_index": index, "reason": reason, "kind": m.STAKEHOLDER_KIND_CLEAR}


def test_no_counter_offer_without_a_clear_request(game_env):
    m = game_env.module
    m.pending_stakeholder_request = None
    assert m.counter_offer_plan() is None
    m.pending_stakeholder_request = {"plot_index": 0, "reason": "x", "kind": m.STAKEHOLDER_KIND_INCENTIVE}
    assert m.counter_offer_plan() is None
    assert m.counter_stakeholder_request() is False


def test_with_bare_plots_the_counter_replants_the_two_nearest(game_env):
    m = game_env.module
    for index in (8, 20, 35):
        m.plots[index].state = m.BARE
    _request_on(m, 14)
    plan = m.counter_offer_plan()
    assert plan["kind"] == "replant" and plan["plots"] == [8, 20]
    assert plan["relations"] == m.COUNTER_RELATIONS_TWO_PLOTS and "replant" in plan["preview"]
    m.community_relations = 50
    income_before = m.total_income
    assert m.counter_stakeholder_request() is True
    assert m.plots[8].state == m.REPLANTING and m.plots[20].state == m.REPLANTING
    assert m.plots[14].state == m.PRESERVED and m.plots[35].state == m.BARE
    assert m.community_relations == 50 + m.COUNTER_RELATIONS_TWO_PLOTS
    assert m.total_income == income_before
    assert m.pending_stakeholder_request is None
    assert m.request_history[-1]["choice"] == "countered"
    assert m.plots[14].requests_survived == 1


def test_one_bare_plot_gives_a_smaller_relations_boost(game_env):
    m = game_env.module
    m.plots[3].state = m.BARE
    _request_on(m, 14)
    plan = m.counter_offer_plan()
    assert plan["plots"] == [3] and plan["relations"] == m.COUNTER_RELATIONS_ONE_PLOT


def test_without_bare_plots_the_counter_harvests_half_and_keeps_the_plot(game_env):
    m = game_env.module
    m.plots[14].value = 40.0
    _request_on(m, 14)
    plan = m.counter_offer_plan()
    assert plan["kind"] == "half" and plan["income"] == 20.0
    assert "20.0 income" in plan["preview"] and "keeps 20.0" in plan["preview"]
    m.community_relations = 40
    clears_before = m.plots[14].clear_count
    income_before = m.total_income
    assert m.counter_stakeholder_request() is True
    assert m.plots[14].value == 20.0 and m.plots[14].state == m.PRESERVED
    assert m.plots[14].clear_count == clears_before  # the soil is not degraded
    assert m.total_income == income_before + 20.0
    assert m.community_relations == 40 + m.COUNTER_RELATIONS_HALF


def test_relations_are_capped_and_the_button_follows_the_request(game_env):
    m = game_env.module
    m.community_relations = 98
    m.plots[14].value = 10.0
    _request_on(m, 14)
    m.render_stakeholder_panel()
    button = game_env.elements["stakeholder-counter-button"]
    assert button.hidden is False and "Counter-offer" in button.title
    m.counter_stakeholder_request()
    assert m.community_relations == 100
    m.render_stakeholder_panel()
    assert button.hidden is True or m.pending_stakeholder_request is None


def test_countered_history_survives_a_save(game_env):
    m = game_env.module
    m.plots[14].value = 10.0
    _request_on(m, 14)
    m.counter_stakeholder_request()
    state = m.get_state()
    m.load_state(state)
    assert [e["choice"] for e in m.request_history] == ["countered"]


# ---- B-19 Forest Rank ----

def test_rank_ladder_thresholds(game_env):
    m = game_env.module
    assert m.rank_for_xp(0)[1] == "Sapling Warden"
    assert m.rank_for_xp(99)[0] == 0 and m.rank_for_xp(100)[1] == "Grove Tender"
    assert m.rank_for_xp(3000)[1] == "Grove Keeper" and m.rank_for_xp(3000)[2] is None
    assert m.rank_for_xp(299)[2] == 300


def test_session_xp_uses_standing_and_seasons(game_env):
    m = game_env.module
    assert m.session_xp(1000.0, 3) == 100 + 15
    assert m.session_xp(-5, -2) == 0


def test_banking_stores_xp_and_each_badge_once(game_env):
    import json
    m = game_env.module
    store = _memory_storage(m)
    m._session_ticks = 60
    m._bank_lifetime()
    m._bank_lifetime()
    life = json.loads(store[m.LIFETIME_STORAGE_KEY])
    assert life["xp"] >= 0 and len(life["badges"]) == len(set(life["badges"]))
    store[m.LIFETIME_STORAGE_KEY] = '{"xp": "x", "badges": ["a", 3, "b"]}'
    life = m.load_lifetime()
    assert life["xp"] == 0 and life["badges"] == ["a", "b"]


def test_rank_info_adds_badge_bonus_and_the_live_session(game_env):
    m = game_env.module
    store = _memory_storage(m)
    store[m.LIFETIME_STORAGE_KEY] = '{"xp": 90, "badges": ["Steward", "Gardener"]}'
    m._session_ticks = 10
    info = m.forest_rank_info()
    assert info["xp"] >= 90 + 2 * m.XP_PER_BADGE_TYPE
    assert info["rank_index"] == 1 and info["badge_types"] >= 2


def test_locked_cosmetics_fall_back_and_options_are_disabled(game_env):
    m = game_env.module
    store = _memory_storage(m)
    m.ui_pref = lambda key, default=None: "crest" if key == m.UI_PREF_FRAME else default
    assert m.chosen_cosmetic(m.UI_PREF_FRAME, m.FRAME_UNLOCKS, "none", 0) == "none"
    assert m.chosen_cosmetic(m.UI_PREF_FRAME, m.FRAME_UNLOCKS, "none", 5) == "crest"
    m._session_ticks = 5
    m.render_forest_rank()
    text = game_env.elements["forest-rank-text"].innerText
    assert "Sapling Warden" in text and "XP" in text


# ---- B-21 timeline chart ----

def _fill_history(m, n=90):
    m._report_history.clear()
    for i in range(n):
        m._report_history.append((float(i), 10.0 + i, 50.0))
    m.forest_tick = 100 + n - 1


def test_timeline_model_aligns_ticks_and_builds_season_bands(game_env):
    m = game_env.module
    _fill_history(m, 90)
    model = m.timeline_model("standing")
    assert model["points"][0] == (100, 10.0) and model["points"][-1] == (189, 99.0)
    assert [b["season"] for b in model["bands"]][0] == m.SEASONS[(100 // 40) % 4]
    assert model["bands"][0]["start"] == 100 and model["bands"][-1]["end"] == 189
    assert all(b["end"] >= b["start"] for b in model["bands"])
    assert m.timeline_model("nonsense")["metric"] == "standing"


def test_timeline_markers_join_the_log_and_request_history(game_env):
    m = game_env.module
    _fill_history(m, 90)
    m.forest_log[:] = [
        {"tick": 120, "kind": "clear", "plot": 3, "text": "Cleared A4 for 5.0 income"},
        {"tick": 130, "kind": "replant", "plot": 3, "text": "Replanted A4"},
        {"tick": 140, "kind": "specialize", "plot": 2, "text": "A3 became a Economic specialist"},
        {"tick": 141, "kind": "wildlife", "plot": 2, "text": "ignored"},
        {"tick": 5, "kind": "clear", "plot": 1, "text": "outside the window"},
    ]
    m.request_history[:] = [{"plot": 4, "kind": m.STAKEHOLDER_KIND_CLEAR, "value_then": 5.0, "tick": 150, "choice": "declined"}]
    kinds = [mk["kind"] for mk in m.timeline_model()["markers"]]
    assert kinds == ["clear", "replant", "specialize", "declined"]
    assert len(m.timeline_marker_lines()) == 4


def test_timeline_svg_has_hover_titles_bands_and_distinct_marker_shapes(game_env):
    import xml.etree.ElementTree as ET
    m = game_env.module
    assert m.timeline_chart_svg() == ""
    _fill_history(m, 60)
    m.forest_log[:] = [
        {"tick": 150, "kind": "clear", "plot": 0, "text": "Cleared A1"},
        {"tick": 151, "kind": "replant", "plot": 0, "text": "Replanted A1"},
    ]
    svg = m.timeline_chart_svg("biodiversity")
    ET.fromstring(svg)
    assert "Tick 150:" in svg and "Cleared A1" in svg and "Spring" in svg or "Summer" in svg or "Autumn" in svg or "Winter" in svg
    assert svg.count("<circle") == 60
    assert "M" in svg and "Z" in svg  # a cross and a triangle path


def test_render_timeline_writes_chart_legend_and_empty_message(game_env):
    m = game_env.module
    m.render_timeline_chart()
    assert "Not enough time" in game_env.elements["timeline-chart"].innerText
    _fill_history(m, 30)
    game_env.elements["timeline-metric"].value = "relations"
    m.render_timeline_chart()
    assert "<svg" in game_env.elements["timeline-chart"].innerHTML
    assert "No events" in game_env.elements["timeline-legend"].innerText


# ---- B-31 grove wall ----

def test_grove_wall_cards_carry_a_wildlife_glyph_and_a_text_status(game_env):
    m = game_env.module
    m.achievements_open = True
    m.update_achievements_display()
    panel = game_env.elements["achievements-panel"]
    assert "grove-wall" in panel.className
    cards = [c for c in panel.children if "achievement-card" in (c.className or "") and getattr(c.dataset, "achievementId", None)]
    assert len(cards) == len(m.ACHIEVEMENTS)
    for card in cards:
        glyph, status = card.children[0], card.children[1]
        assert glyph.innerText in [icon for icon, _name in m.WILDLIFE_SPECIES]
        assert status.innerText in ("Earned", "Locked")
        assert ("achievement-card--earned" in card.className) == (status.innerText == "Earned")
        assert ("--locked" in glyph.className) == (status.innerText == "Locked")


def test_glyphs_cycle_through_the_wildlife_icons(game_env):
    m = game_env.module
    n = len(m.WILDLIFE_SPECIES)
    assert m.grove_wall_glyph(0) == m.grove_wall_glyph(n) != m.grove_wall_glyph(1)


# ---- B-1 My Forests ----

def _bank_one(m, ticks=100, name="Oak"):
    m._report_history.clear()
    for i in range(80):
        m._report_history.append((float(i), 10.0 + i, 40.0))
    m.forest_name = name
    m._session_ticks = ticks
    m._bank_lifetime()


def test_a_finished_session_is_saved_with_compact_series(game_env):
    import json
    m = game_env.module
    store = _memory_storage(m)
    _bank_one(m)
    saved = json.loads(store[m.MY_FORESTS_KEY])
    assert len(saved) == 1 and saved[0]["name"] == "Oak" and saved[0]["id"] == 1
    assert len(saved[0]["series"]["standing"]) == m.MY_FORESTS_SERIES_POINTS
    assert saved[0]["series"]["standing"][-1] == 89.0 and saved[0]["grid"] == f"{m.GRID_ROWS}x{m.GRID_COLS}"


def test_nothing_is_saved_for_a_session_that_never_ticked(game_env):
    m = game_env.module
    store = _memory_storage(m)
    m._session_ticks = 0
    m._bank_lifetime()
    assert m.MY_FORESTS_KEY not in store


def test_library_keeps_only_the_latest_twelve_with_rising_ids(game_env):
    m = game_env.module
    _memory_storage(m)
    for i in range(15):
        _bank_one(m, name=f"F{i}")
    records = m.load_my_forests()
    assert len(records) == m.MY_FORESTS_MAX
    assert [r["id"] for r in records] == list(range(4, 16))


def test_bad_stored_library_is_sanitised(game_env):
    m = game_env.module
    store = _memory_storage(m)
    store[m.MY_FORESTS_KEY] = "nope"
    assert m.load_my_forests() == []
    store[m.MY_FORESTS_KEY] = '[5, {"id": "x", "name": 7, "standing": "big", "series": {"standing": [1, "a", true, 2.5]}}, null]'
    records = m.load_my_forests()
    assert len(records) == 1 and records[0]["standing"] == 0.0 and records[0]["series"]["standing"] == [1.0, 2.5]


def test_downsample_keeps_the_last_value(game_env):
    m = game_env.module
    assert m._downsample([1, 2, 3], 30) == [1.0, 2.0, 3.0]
    out = m._downsample(list(range(100)), 10)
    assert len(out) == 10 and out[0] == 0.0 and out[-1] == 99.0


def test_compare_renders_a_table_and_six_graphs(game_env):
    m = game_env.module
    _memory_storage(m)
    _bank_one(m, name="Oak")
    _bank_one(m, name="Pine <b>")
    m.render_my_forests()
    assert "2 saved forests" in game_env.elements["my-forests-note"].innerText
    table = game_env.elements["my-forests-compare"].innerHTML
    assert "A: #2" in table and "B: #1" in table or "A: #1" in table
    assert "&lt;b&gt;" in table and "<b>" not in table
    assert game_env.elements["my-forests-graphs"].innerHTML.count("<svg") == 6


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
    css = open(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", "style.css"), encoding="utf-8").read()
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


def test_smoke_comes_three_ticks_before_the_spark_and_names_the_plot(game_env):
    m = game_env.module
    _wildfire(m)
    block = _first_summer_block(m)
    due = m.fire_ignition_tick(block)
    m.forest_tick = due - m.FIRE_WARNING_TICKS
    m._fire_tick()
    assert m.fire_warning is not None and m.fire_warning["ticks_left"] == m.FIRE_WARNING_TICKS
    target = m.fire_warning["plot"]
    assert "Smoke over" in m.fire_status_text()
    for _ in range(m.FIRE_WARNING_TICKS):
        m.forest_tick += 1
        m._fire_tick()
    assert target in m.fires and m.fire_warning is None


def test_fire_spreads_to_standing_neighbours_and_burns_out_to_bare(game_env):
    m = game_env.module
    _wildfire(m)
    m.forest_tick = 0  # a calm spring tick, so no new spark interferes
    centre = m.GRID_COLS + 1
    m._ignite(centre)
    m._fire_tick()
    assert set(m.fires) == {centre}
    m._fire_tick()  # age 2: spreads
    assert set(m._edge_neighbours(centre)) <= set(m.fires)
    for _ in range(m.FIRE_BURN_TICKS):
        m._fire_tick()
    assert m.plots[centre].state == m.BARE and m.plots[centre].clear_count == 0
    assert m.fire_value_lost >= 20.0


def test_bare_and_replanting_plots_are_firebreaks_and_the_heart_tree_never_burns(game_env):
    m = game_env.module
    _wildfire(m)
    m.forest_tick = 0
    start = m.GRID_COLS + 1
    left, right, up, down = start - 1, start + 1, start - m.GRID_COLS, start + m.GRID_COLS
    m.plots[left].state = m.BARE
    m.plots[right].state = m.REPLANTING
    m.heart_tree_index = up
    m._ignite(start)
    for _ in range(3):
        m._fire_tick()
    assert left not in m.fires and right not in m.fires and up not in m.fires and down in m.fires


def test_dampen_stops_a_fire_shields_the_plot_and_has_a_cooldown(game_env):
    m = game_env.module
    _wildfire(m)
    m.forest_tick = 0
    m._ignite(7)
    m.selected_index = 7
    assert m.can_dampen(7) is True and m.can_dampen(8) is False
    assert m.dampen_plot() is True
    assert 7 not in m.fires and m.fire_damp[7] == m.FIRE_DAMP_TICKS
    m._ignite(8)
    assert m.dampen_plot(8) is False  # cooling down
    for _ in range(m.FIRE_DAMPEN_COOLDOWN):
        m._fire_tick()
    m._ignite(9)
    assert m.can_dampen(9) is True  # the cooldown is over (the fire on 8 has burned out by now)
    m.fire_damp[10] = 5  # a damp neighbour is not set alight
    for _ in range(3):
        m._fire_tick()
    assert 10 not in m.fires


def test_dampening_the_smoking_plot_cancels_the_spark(game_env):
    m = game_env.module
    _wildfire(m)
    due = m.fire_ignition_tick(_first_summer_block(m))
    m.forest_tick = due - m.FIRE_WARNING_TICKS
    m._fire_tick()
    target = m.fire_warning["plot"]
    assert m.dampen_plot(target) is True and m.fire_warning is None
    for _ in range(5):
        m.forest_tick += 1
        m._fire_tick()
    assert target not in m.fires


def test_clearing_a_burning_plot_puts_it_out_and_new_game_is_calm(game_env):
    m = game_env.module
    _wildfire(m)
    m.forest_tick = 0
    m._ignite(3)
    m.plots[3].clear()
    m._fire_tick()
    assert 3 not in m.fires
    m._ignite(4)
    m.reset_session()
    assert m.fires == {} and m.fire_warning is None


def test_tiles_show_a_glyph_and_the_button_follows_the_difficulty(game_env):
    m = game_env.module
    _wildfire(m)
    m._ignite(2)
    m.fire_warning = {"plot": 5, "ticks_left": 2}
    m.selected_index = 2
    m.render()
    grid = game_env.elements["plot-grid"].children
    assert "plot-burning" in grid[2].className and any(c.className == "fire-mark" for c in grid[2].children)
    assert "plot-smoke" in grid[5].className and "BURNING" in grid[2].getAttribute("data-tooltip")
    assert game_env.elements["dampen-button"].hidden is False and game_env.elements["dampen-button"].disabled is False
    assert game_env.elements["fire-status"].hidden is False
    m.current_difficulty = m.DIFFICULTY_NORMAL
    m.render()
    assert game_env.elements["dampen-button"].hidden is True


def test_wildfire_is_a_valid_difficulty_with_normal_soil_damage_and_a_tag(game_env):
    m = game_env.module
    m.reset_session(difficulty=m.DIFFICULTY_WILDFIRE)
    assert m.current_difficulty == m.DIFFICULTY_WILDFIRE
    assert m.current_degrade_per_clear() == m.DEGRADE_PER_CLEAR * m.vault_soil_factor()
    assert "Wildfire season" in m.session_tag_text()
    state = m.get_state()
    m.reset_session()
    m.load_state(state)
    assert m.current_difficulty == m.DIFFICULTY_WILDFIRE


# ---- GB-24 wetland tides ----

def _wet(m):
    m.wetland_unlocked = True
    m.forest_tick = 0


def test_tide_turns_every_six_ticks_and_half_the_plots_are_under_water(game_env):
    m = game_env.module
    _wet(m)
    n = len(m.wetland_plots)
    for tick in range(0, 30):
        flooded = [i for i in range(n) if m.wetland_plot_flooded(i, tick)]
        assert len(flooded) == n // 2
    assert m.wetland_tide_high(0) is False and m.wetland_tide_high(6) is True and m.wetland_tide_high(12) is False
    now = {i for i in range(n) if m.wetland_plot_flooded(i, 0)}
    later = {i for i in range(n) if m.wetland_plot_flooded(i, 6)}
    assert now.isdisjoint(later) and now | later == set(range(n))
    m.forest_tick = 4
    assert m.wetland_ticks_to_tide_turn() == 2


def test_seedlings_only_go_in_dry_plots_and_mangroves_only_in_flooded_ones(game_env):
    m = game_env.module
    _wet(m)
    flooded = next(i for i in range(len(m.wetland_plots)) if m.wetland_plot_flooded(i))
    dry = next(i for i in range(len(m.wetland_plots)) if not m.wetland_plot_flooded(i))
    for i in (flooded, dry):
        m.wetland_plots[i].state = m.BARE
    m.wetland_selected_index = flooded
    m.on_wetland_replant()
    assert m.wetland_plots[flooded].state == m.BARE
    assert m.on_wetland_mangrove() is True
    assert m.wetland_plots[flooded].state == m.REPLANTING and m.wetland_plots[flooded].species == m.SPECIES_MANGROVE
    m.wetland_selected_index = dry
    assert m.on_wetland_mangrove() is False and m.wetland_plots[dry].state == m.BARE
    m.on_wetland_replant()
    assert m.wetland_plots[dry].state == m.REPLANTING and m.wetland_plots[dry].species is None


def test_mangroves_recover_fast_and_the_flood_cannot_harm_them(game_env):
    m = game_env.module
    plot = m.Plot(0, region="wetland")
    plot.state = m.BARE
    plot.replant(species=m.SPECIES_MANGROVE)
    assert plot.replant_ticks_remaining == round(m.RECOVERY_TICKS * 0.6)
    plot.state, plot.value, plot.ticks_intact = m.PRESERVED, 50.0, 3
    assert m.wetland_flood_loss_fraction(plot) == 0.0
    other = m.Plot(1, region="wetland")
    other.state, other.value, other.ticks_intact = m.PRESERVED, 50.0, 3
    assert m.wetland_flood_loss_fraction(other) == m.WETLAND_FLOOD_LOSS_YOUNG


def test_the_main_forest_picker_never_offers_or_accepts_a_mangrove(game_env):
    m = game_env.module
    m.species_choice = m.SPECIES_MANGROVE
    m.plots[0].state = m.BARE
    m.selected_index = 0
    m.on_replant()
    assert m.plots[0].species is None
    store = _memory_storage(m)
    store[m.SPECIES_CHOICE_KEY] = "mangrove"
    m.load_species_choice()
    assert m.species_choice == m.SPECIES_STANDARD


def test_tidal_wildlife_appears_in_the_almanac_once_the_wetland_is_open(game_env):
    m = game_env.module
    assert "Tidal wildlife" not in [t for t, _ in m.almanac_sections()]
    _wet(m)
    sections = dict(m.almanac_sections())
    assert [e[2] for e in sections["Tidal wildlife"]] == [False, False]
    for i in range(3):
        m.wetland_plots[i].state, m.wetland_plots[i].species = m.PRESERVED, m.SPECIES_MANGROVE
    m.note_wetland_wildlife()
    assert [e[2] for e in dict(m.almanac_sections())["Tidal wildlife"]] == [True, False]
    m.wetland_plots[0].ticks_intact = m.MATURITY_TICKS
    m.note_wetland_wildlife()
    for p in m.wetland_plots:
        p.species, p.state = None, m.BARE  # losing the mangroves does not un-find the wildlife
    assert [e[2] for e in dict(m.almanac_sections())["Tidal wildlife"]] == [True, True]


def test_tides_show_on_tiles_and_in_the_status_and_the_wildlife_is_saved(game_env):
    m = game_env.module
    _wet(m)
    m.render_wetland_grid()
    tiles = game_env.elements["wetland-plot-grid"].children
    flooded = [i for i, t in enumerate(tiles) if "plot-tidal" in t.className]
    assert flooded == [i for i in range(len(tiles)) if m.wetland_plot_flooded(i)]
    assert "under water now" in tiles[flooded[0]].getAttribute("data-tooltip")
    assert "Tide: low" in m.wetland_tide_text()
    m.wetland_wildlife_found.add("heron")
    state = m.get_state()
    assert state["wetland_wildlife"] == ["heron"]
    m.wetland_wildlife_found.clear()
    m.load_state(state)
    assert m.wetland_wildlife_found == {"heron"}


# ---- GB-29 carbon-credit market ----

def test_price_follows_a_known_bounded_cycle(game_env):
    m = game_env.module
    prices = [m.carbon_price(t) for t in range(0, 400)]
    assert prices == [m.carbon_price(t) for t in range(0, 400)]
    assert min(prices) > m.CARBON_BASE_PRICE * 0.5 and max(prices) < m.CARBON_BASE_PRICE * 1.5
    assert len({round(p, 1) for p in prices}) > 50  # it really moves
    assert m.carbon_trend(0) in ("rising", "falling", "steady")
    trends = {m.carbon_trend(t) for t in range(0, 200)}
    assert {"rising", "falling"} <= trends


def test_standing_plots_earn_credits_up_to_a_cap(game_env):
    m = game_env.module
    m._carbon_tick()
    assert abs(m.carbon["credits"] - len(m.plots) * m.CARBON_CREDIT_PER_PLOT_TICK) < 1e-9
    m.carbon["credits"] = m.CARBON_CREDIT_CAP - 0.001
    m._carbon_tick()
    assert m.carbon["credits"] == m.CARBON_CREDIT_CAP
    for p in m.plots:
        p.state = m.BARE
    before = m.carbon["credits"]
    m._carbon_tick()
    assert m.carbon["credits"] == before  # nothing standing, nothing earned


def test_selling_pays_now_and_slows_growth_for_a_while(game_env):
    m = game_env.module
    m.forest_tick = 20
    m.carbon["credits"] = 40.0
    preview = m.sale_preview()
    assert preview["income"] == round(40.0 * m.carbon_price(), 2) and preview["slump_ticks"] == m.CARBON_SLUMP_BASE_TICKS + 20
    income = m.total_income
    paid = m.sell_carbon(1.0)
    assert paid == preview["income"] and m.total_income == income + paid
    assert m.carbon["credits"] == 0.0 and m.carbon["slump"] == preview["slump_ticks"] and m.carbon["sold"] == 40.0
    assert m.carbon_slump_multiplier() == m.CARBON_SLUMP_MULTIPLIER
    a, b = m.Plot(0), m.Plot(1)
    a.state = b.state = m.PRESERVED
    slow = a.accrue_tick()
    m.carbon["slump"] = 0
    normal = b.accrue_tick()
    assert slow < normal


def test_slump_runs_out_and_a_tiny_balance_does_not_sell(game_env):
    m = game_env.module
    m.carbon["slump"] = 2
    m._carbon_tick()
    m._carbon_tick()
    assert m.carbon_slump_multiplier() == 1.0
    m.carbon["credits"] = 0.3
    assert m.sell_carbon(1.0) == 0.0 and m.carbon["credits"] == 0.3
    m.carbon["credits"] = 10.0
    m.sell_carbon(0.5)
    assert abs(m.carbon["credits"] - 5.0) < 1e-9


def test_slump_length_is_capped(game_env):
    m = game_env.module
    assert m.carbon_slump_ticks_for(1000) == m.CARBON_SLUMP_MAX_TICKS


def test_carbon_offer_from_the_broker_gifts_credits(game_env):
    m = game_env.module
    m.plots[14].value = 10.0
    m.pending_stakeholder_request = {"plot_index": 14, "reason": "carbon_credit", "kind": m.STAKEHOLDER_KIND_INCENTIVE}
    m.grant_stakeholder_request()
    assert m.carbon["credits"] == m.CARBON_OFFER_CREDITS
    m.pending_stakeholder_request = {"plot_index": 14, "reason": "ecotourism", "kind": m.STAKEHOLDER_KIND_INCENTIVE}
    m.grant_stakeholder_request()
    assert m.carbon["credits"] == m.CARBON_OFFER_CREDITS


def test_chart_text_and_buttons(game_env):
    import xml.etree.ElementTree as ET
    m = game_env.module
    m.forest_tick = 30
    svg = m.carbon_chart_svg()
    ET.fromstring(svg)
    assert "stroke-dasharray" in svg  # the forecast is dotted
    m.carbon["credits"] = 12.0
    m.render_carbon()
    assert "Carbon credits: 12.0" in game_env.elements["carbon-status"].innerText
    assert game_env.elements["carbon-sell-button"].disabled is False
    m.carbon["credits"] = 0.0
    m.render_carbon()
    assert game_env.elements["carbon-sell-button"].disabled is True


def test_carbon_saves_only_when_used_validates_and_resets(game_env):
    m = game_env.module
    assert "carbon" not in m.get_state()
    m.carbon.update({"credits": 7.5, "slump": 3, "sold": 20.0, "earned_from_sales": 300.0})
    state = m.get_state()
    m.reset_session()
    assert m.carbon["credits"] == 0.0
    m.load_state(state)
    assert m.carbon["credits"] == 7.5 and m.carbon["slump"] == 3 and m.carbon["sold"] == 20.0
    state["carbon"] = {"credits": 99999, "slump": -4, "sold": "x"}
    m.load_state(state)
    assert m.carbon["credits"] == m.CARBON_CREDIT_CAP and m.carbon["slump"] == 0 and m.carbon["sold"] == 0.0
