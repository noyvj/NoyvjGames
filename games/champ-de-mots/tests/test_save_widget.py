"""Milestone 5: the shared save widget contract (SAVE-BUTTON-INTEGRATION.md §2).

`shared/save-widget.js` is dropped into this game unchanged; the whole per-game
contract is `get_state()` returning one plain JSON-safe dict and `load_state()`
being its exact inverse. These tests round-trip the farm's SRS state through
that pair — including through a real `json.dumps`, since the widget POSTs it.
"""

import json


EXPECTED_KEYS = {"version", "current_day", "plots"}
PLOT_KEYS = {"ease_factor", "interval_days", "last_reviewed", "next_due", "correct_streak", "stage"}


def _water(game_env, plot_id, times=1, correct=True):
    for _ in range(times):
        game_env.state.review(plot_id, correct)
        game_env.state.advance_day(game_env.plot(plot_id).interval_days)


def test_get_state_returns_the_documented_top_level_shape(game_env):
    data = game_env.module.get_state()
    assert set(data) == EXPECTED_KEYS
    assert data["current_day"] == 0
    assert data["plots"] == {}


def test_an_untouched_farm_saves_almost_nothing(game_env):
    """722 plots × 6 SRS fields would be a ~100KB payload on every save. Only
    plots that have actually been watered are stored; everything else is
    reconstructed from the catalog at load, which is where it came from."""
    raw = json.dumps(game_env.module.get_state())
    assert len(raw) < 200


def test_watered_plots_are_stored_with_their_full_srs_state(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    _water(game_env, plot.plot_id, times=2)

    saved = module.get_state()["plots"]
    assert set(saved) == {plot.plot_id}
    assert set(saved[plot.plot_id]) == PLOT_KEYS
    assert saved[plot.plot_id]["interval_days"] == plot.interval_days
    assert saved[plot.plot_id]["correct_streak"] == plot.correct_streak
    assert saved[plot.plot_id]["stage"] == plot.stage
    assert saved[plot.plot_id]["ease_factor"] == plot.ease_factor
    assert saved[plot.plot_id]["last_reviewed"] == plot.last_reviewed
    assert saved[plot.plot_id]["next_due"] == plot.next_due


def test_a_plot_answered_only_incorrectly_is_still_saved(game_env):
    """Its streak is 0 and its stage is still Seed, but it has a review
    history and an ease penalty — dropping it would silently undo that."""
    module, state = game_env.module, game_env.state
    plot = state.plots[5]
    state.review(plot.plot_id, False)

    saved = module.get_state()["plots"]
    assert plot.plot_id in saved
    assert saved[plot.plot_id]["last_reviewed"] == 0
    assert saved[plot.plot_id]["ease_factor"] < module.DEFAULT_EASE


def test_get_state_snapshot_does_not_alias_live_state(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    _water(game_env, plot.plot_id)
    snapshot = module.get_state()
    day_at_snapshot = state.current_day

    _water(game_env, plot.plot_id)
    state.advance_day(5)

    assert snapshot["plots"][plot.plot_id]["interval_days"] == 1
    assert snapshot["current_day"] == day_at_snapshot
    assert state.current_day != day_at_snapshot
    assert plot.interval_days != 1


def test_load_state_does_not_alias_the_dict_it_is_given(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    _water(game_env, plot.plot_id)
    data = module.get_state()

    module.load_state(data)
    data["plots"][plot.plot_id]["interval_days"] = 999
    data["current_day"] = 999

    assert plot.interval_days != 999
    assert state.current_day != 999


def test_full_round_trip_restores_every_plot_and_the_calendar(game_env):
    module, state = game_env.module, game_env.state
    first, second, third = state.plots[0], state.plots[1], state.plots[400]
    _water(game_env, first.plot_id, times=4)
    _water(game_env, second.plot_id, times=2)
    state.review(third.plot_id, False)
    state.advance_day(3)

    snapshot = module.get_state()

    # Diverge in every direction before loading the snapshot back.
    _water(game_env, first.plot_id)
    _water(game_env, second.plot_id, correct=False)
    _water(game_env, third.plot_id)
    state.advance_day(11)
    assert module.get_state() != snapshot

    assert module.load_state(snapshot) is True
    assert module.get_state() == snapshot
    assert state.current_day == snapshot["current_day"]
    for plot_id, saved in snapshot["plots"].items():
        plot = state.plots_by_id[plot_id]
        assert plot.ease_factor == saved["ease_factor"]
        assert plot.interval_days == saved["interval_days"]
        assert plot.last_reviewed == saved["last_reviewed"]
        assert plot.next_due == saved["next_due"]
        assert plot.correct_streak == saved["correct_streak"]
        assert plot.stage == saved["stage"]


def test_load_state_resets_plots_absent_from_the_save(game_env):
    """Loading someone else's save must not leave this session's plants
    standing in a farm that never grew them."""
    module, state = game_env.module, game_env.state
    kept, stray = state.plots[0], state.plots[1]
    _water(game_env, kept.plot_id, times=2)
    snapshot = module.get_state()

    _water(game_env, stray.plot_id, times=3)
    module.load_state(snapshot)

    assert stray.stage == module.STAGE_SEED
    assert stray.interval_days == 0
    assert stray.last_reviewed is None
    assert stray.next_due is None
    assert stray.correct_streak == 0
    assert stray.ease_factor == module.DEFAULT_EASE
    assert kept.stage != module.STAGE_SEED


def test_round_trip_survives_real_json_serialisation(game_env):
    """The widget POSTs this dict as JSON, so every value has to be
    JSON-native — json.dumps raises on anything that isn't."""
    module, state = game_env.module, game_env.state
    _water(game_env, state.plots[0].plot_id, times=3)
    state.review(state.plots[9].plot_id, False)

    data = module.get_state()
    restored = json.loads(json.dumps(data))
    assert restored == data

    _water(game_env, state.plots[20].plot_id)  # diverge
    assert module.load_state(restored) is True
    assert module.get_state() == data


def test_load_state_repaints_the_farm(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    _water(game_env, plot.plot_id, times=2)
    snapshot = module.get_state()

    module.load_state({"version": 1, "current_day": 0, "plots": {}})
    assert "plot--seed" in game_env.elements[f"plot-{plot.plot_id}"].className

    module.load_state(snapshot)
    cell = game_env.elements[f"plot-{plot.plot_id}"]
    assert f"plot--{plot.stage}" in cell.className
    assert cell.innerText == module.STAGE_ICON[plot.stage]
    assert game_env.elements["day-display"].innerText == f"Day {state.current_day + 1}"


def test_load_state_closes_any_open_practice_question(game_env):
    """A question generated against the pre-load farm is meaningless once a
    different save is in place."""
    module, state = game_env.module, game_env.state
    module.open_practice(state.plots[0].plot_id)
    assert module.current_question is not None

    module.load_state({"version": 1, "current_day": 4, "plots": {}})

    assert module.current_question is None
    assert game_env.elements["practice-panel"].hidden is True


def test_load_state_ignores_plot_ids_that_are_not_in_the_catalog(game_env):
    """Old saves from a different catalog revision must not crash the farm."""
    module = game_env.module
    assert module.load_state(
        {"version": 1, "current_day": 2, "plots": {"fren999-w9-vocab001-i00": {
            "ease_factor": 2.5, "interval_days": 3, "last_reviewed": 0,
            "next_due": 3, "correct_streak": 2, "stage": "budding",
        }}}
    ) is True
    assert game_env.state.current_day == 2


def test_load_state_tolerates_a_partial_plot_record(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    assert module.load_state(
        {"current_day": 1, "plots": {plot.plot_id: {"interval_days": 5, "stage": "blooming"}}}
    ) is True
    assert plot.interval_days == 5
    assert plot.stage == module.STAGE_BLOOMING
    assert plot.ease_factor == module.DEFAULT_EASE


def test_load_state_on_a_truly_empty_dict_starts_a_fresh_farm(game_env):
    """PR #1 (sean-hart) review finding: every existing test always passes
    explicit version/current_day/plots keys (even if plots is {}) — none
    exercises data.get("plots") or {} and data.get("current_day", 0)
    together against a dict missing both entirely, the "truly empty save"
    case CLAUDE.md's Milestone 5 notes call out as in-scope. Unlike
    aftermath/canopy's load_state (which intentionally raise KeyError on a
    malformed dict — see their own save-system tests), this game's
    load_state is written to tolerate exactly this: every field already
    defaults via .get(), so a genuinely empty dict should succeed cleanly
    rather than raise, restoring day 0 with every plot reset to its
    just-planted state."""
    module, state = game_env.module, game_env.state
    state.current_day = 5
    state.plots[0].stage = module.STAGE_BLOOMING

    assert module.load_state({}) is True
    assert state.current_day == 0
    assert state.plots[0].stage == module.STAGE_SEED


def test_load_state_falls_back_to_seed_stage_for_an_unrecognized_stage_string(game_env):
    """The other half of the same finding: no test exercised the
    `if plot.stage not in STAGE_RANK: plot.stage = STAGE_SEED` fallback a
    few lines below the .get() defaults — e.g. a save written by a future
    build with a stage name this build doesn't know, or a hand-edited
    payload."""
    module, state = game_env.module, game_env.state
    plot = state.plots[0]

    assert module.load_state(
        {"current_day": 1, "plots": {plot.plot_id: {"stage": "not-a-real-stage"}}}
    ) is True
    assert plot.stage == module.STAGE_SEED


def test_the_page_includes_the_shared_save_widget_unchanged(game_env):
    """SAVE-BUTTON-INTEGRATION.md §4: the one drop-in line, with this game's
    id, and window.pyodide exposed for it by the boot script."""
    from pathlib import Path

    html = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
    assert '<script src="../../shared/save-widget.js" data-game-id="champ-de-mots"></script>' in html
    assert "window.pyodide = pyodide;" in html
