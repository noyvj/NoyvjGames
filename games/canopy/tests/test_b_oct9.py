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
