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
