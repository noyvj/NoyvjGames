"""F8 (planning/TODO.md "Per-game: Herd"): a small "record decoupling
ratio" marker on the coupling gauge, like Grid's best-round marker --
a per-browser record of the best (lowest) coupling ratio ever reached on
this browser, persisted via localStorage.

This is a different axis from the existing F14 "Session best" label
(`#gauge-range-display`): coupling_ratio() only ever falls *within* a
single session (investment counts never go down), so a session-scoped
best is always just the current value -- the exact reason the Round-2
pass explicitly skipped this idea at the time (see CLAUDE.md). What makes
this meaningful is that a *fresh* session starts back at
BASE_COUPLING_RATIO, so the browser's all-time record and the current
session's value genuinely diverge once a player has played before.
"""

import json


def test_no_record_on_a_brand_new_browser(game_env):
    m = game_env.module
    assert m.record_coupling_ratio is None


def test_marker_does_not_appear_without_a_record(game_env):
    svg = game_env.elements["coupling-gauge"].innerHTML
    assert "gauge-record-marker" not in svg


def test_record_label_hidden_without_a_record(game_env):
    element = game_env.elements["coupling-gauge-record-display"]
    assert element.hidden is True


def test_first_investment_sets_a_record(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 1000.0
    game_env.invest_decoupling("capture")

    assert m.record_coupling_ratio == farm.coupling_ratio()
    assert m.record_coupling_ratio < m.BASE_COUPLING_RATIO


def test_marker_appears_once_a_record_exists(game_env):
    farm = game_env.farm
    farm.funds = 1000.0
    game_env.invest_decoupling("capture")

    svg = game_env.elements["coupling-gauge"].innerHTML
    assert "gauge-record-marker" in svg


def test_record_label_shown_and_states_the_value(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 1000.0
    game_env.invest_decoupling("capture")

    element = game_env.elements["coupling-gauge-record-display"]
    assert element.hidden is False
    assert f"{m.record_coupling_ratio:.2f}" in element.innerText


def test_record_persisted_to_local_storage(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 1000.0
    game_env.invest_decoupling("capture")

    stored = game_env.local_storage.getItem(m.RECORD_COUPLING_RATIO_STORAGE_KEY)
    assert stored is not None
    assert json.loads(stored) == m.record_coupling_ratio


def test_marker_moves_when_the_ratio_improves_to_a_new_best(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 1000.0

    game_env.invest_decoupling("capture")
    first_svg = game_env.elements["coupling-gauge"].innerHTML
    first_record = m.record_coupling_ratio

    game_env.invest_decoupling("capture")
    second_svg = game_env.elements["coupling-gauge"].innerHTML
    second_record = m.record_coupling_ratio

    assert second_record < first_record
    assert first_svg != second_svg


def test_marker_does_not_move_on_a_non_record_result(game_env):
    """Re-rendering with no new investment (coupling_ratio() unchanged, so
    nothing beats the stored record) must leave the record -- and
    therefore the marker's position -- exactly where it was."""
    m = game_env.module
    farm = game_env.farm
    farm.funds = 1000.0
    game_env.invest_decoupling("capture")

    record_after_investment = m.record_coupling_ratio
    svg_after_investment = game_env.elements["coupling-gauge"].innerHTML

    m.render()  # no state change -- coupling_ratio() is identical
    m.render()

    assert m.record_coupling_ratio == record_after_investment
    assert game_env.elements["coupling-gauge"].innerHTML == svg_after_investment


def test_advancing_a_round_alone_never_creates_a_record(game_env):
    """Advancing rounds grows accumulated methane but never changes
    coupling_ratio() itself (that only moves via decoupling/pivot
    investment) -- so it must never touch the record."""
    m = game_env.module
    game_env.advance_round()
    game_env.advance_round()
    assert m.record_coupling_ratio is None


def test_record_never_gets_worse_than_a_previous_session(game_env):
    """A fresh farm starts at BASE_COUPLING_RATIO (1.0), which is never
    better than any previously-stored record (record_ratio <=
    BASE_COUPLING_RATIO always) -- so booting against an existing record
    must leave it untouched until the new session actually beats it."""
    m = game_env.module
    farm = game_env.farm
    farm.funds = 1000.0
    game_env.invest_decoupling("capture")
    stored_record = m.record_coupling_ratio

    reloaded = game_env.reload()
    assert reloaded.record_coupling_ratio == stored_record


def test_record_persists_across_a_fresh_module_load(game_env):
    """The core cross-session contract: a record written to localStorage
    by one "session" (module load) is picked back up by the very next
    one, exactly like a real page reload on the same browser."""
    m = game_env.module
    farm = game_env.farm
    farm.funds = 1000.0
    game_env.invest_decoupling("capture")
    game_env.invest_decoupling("capture")
    record_before_reload = m.record_coupling_ratio
    assert record_before_reload is not None

    reloaded_module = game_env.reload()

    assert reloaded_module.record_coupling_ratio == record_before_reload
    assert reloaded_module.load_record_coupling_ratio() == record_before_reload


def test_load_record_coupling_ratio_defaults_to_none_on_malformed_storage(game_env):
    m = game_env.module
    game_env.local_storage.setItem(m.RECORD_COUPLING_RATIO_STORAGE_KEY, "not json")
    assert m.load_record_coupling_ratio() is None


def test_record_is_not_part_of_get_state(game_env):
    """Deliberately independent of the save-code system, same distinction
    Canopy's B14/Tide's D13/Thaw's G19 draw: this is a per-browser device
    record across every session/save, not one save's snapshot."""
    m = game_env.module
    assert "record_coupling_ratio" not in m.get_state()
