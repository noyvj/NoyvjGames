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
