"""Shared save widget integration (SAVE-BUTTON-INTEGRATION.md): get_state()
packages every module-level mutable global into one plain, JSON-safe dict,
and load_state() is its exact inverse. Canopy is not the reference
integration (SOL is) — this just adopts the same contract."""

import json


def test_get_state_includes_every_expected_key(game_env):
    data = game_env.module.get_state()
    assert set(data.keys()) == {
        "plots",
        "selected_index",
        "total_income",
        "community_relations",
        "pending_stakeholder_request",
        "_ticks_since_last_request",
        "_stakeholder_request_count",
        "info_page_open",
        "total_replants",
        "total_recoveries",
        "plots_with_wildlife_ever",
        "stakeholder_grants_count",
        "stakeholder_declines_count",
        "community_relations_min_ever",
        "current_grid_size",
        "current_difficulty",
        "forest_log",
        "forest_tick",
        "adopted_plot_index",
        "highland_unlocked",
        "highland_selected_index",
        "highland_income",
        "highland_plots",
        "achievements_earned",
    }


def test_get_state_expands_every_plot_into_a_plain_dict(game_env):
    data = game_env.module.get_state()
    assert len(data["plots"]) == len(game_env.module.plots)
    for plot_data in data["plots"]:
        assert set(plot_data.keys()) == {
            "index",
            "state",
            "value",
            "ticks_intact",
            "clear_count",
            "replant_ticks_remaining",
            "just_recovered",
            "biodiversity",
            "mature_celebrated",
            "requests_survived",
            "specialization",
        }


def test_get_state_is_json_serialisable(game_env):
    game_env.tick(5)
    game_env.select(0)
    game_env.clear()
    data = game_env.module.get_state()
    # Round-tripping through json.dumps/loads must not raise, and must
    # reproduce the same plain-data structure (no custom objects survive
    # a real JSON boundary, so this also catches anything non-JSON-safe
    # that snuck into the dict).
    assert json.loads(json.dumps(data)) == data


def test_get_state_deep_copies_pending_stakeholder_request(game_env):
    game_env.tick(game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS + 1)
    assert game_env.module.pending_stakeholder_request is not None
    data = game_env.module.get_state()

    # Mutating the live global's dict afterward must not leak into the
    # already-returned snapshot.
    game_env.module.pending_stakeholder_request["reason"] = "mutated"
    assert data["pending_stakeholder_request"]["reason"] != "mutated"


def test_get_state_pending_stakeholder_request_is_none_when_unset(game_env):
    data = game_env.module.get_state()
    assert data["pending_stakeholder_request"] is None


def test_load_state_full_round_trip_restores_every_tracked_field(game_env):
    # Build up varied, non-default state across every tracked field.
    game_env.tick(game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS + 1)
    game_env.select(2)
    game_env.clear()  # PRESERVED -> BARE, so it can be replanted below
    game_env.replant()  # BARE -> REPLANTING
    game_env.select(3)
    game_env.clear()
    game_env.module.info_page_open = True
    game_env.module.render()

    snapshot = game_env.module.get_state()
    plots_before = [dict(p) for p in snapshot["plots"]]
    income_before = snapshot["total_income"]
    relations_before = snapshot["community_relations"]
    selected_before = snapshot["selected_index"]
    pending_before = snapshot["pending_stakeholder_request"]
    ticks_since_before = snapshot["_ticks_since_last_request"]
    request_count_before = snapshot["_stakeholder_request_count"]
    info_open_before = snapshot["info_page_open"]

    # Diverge substantially from the snapshot on every field.
    game_env.tick(20)
    game_env.select(5)
    game_env.clear()
    game_env.module.community_relations = 1
    game_env.module.info_page_open = False
    game_env.module.decline_stakeholder_request()

    assert game_env.module.get_state()["plots"] != plots_before

    result = game_env.module.load_state(snapshot)
    assert result is True

    restored = game_env.module.get_state()
    assert restored["plots"] == plots_before
    assert restored["total_income"] == income_before
    assert restored["community_relations"] == relations_before
    assert restored["selected_index"] == selected_before
    assert restored["pending_stakeholder_request"] == pending_before
    assert restored["_ticks_since_last_request"] == ticks_since_before
    assert restored["_stakeholder_request_count"] == request_count_before
    assert restored["info_page_open"] == info_open_before


def test_load_state_restores_plots_in_place_not_by_replacing_the_list(game_env):
    """Restoring must mutate the existing Plot objects rather than swap in
    a fresh list, so nothing else holding `plots[i]` is left stale."""
    original_plot_objects = list(game_env.module.plots)
    game_env.select(0)
    game_env.clear()
    snapshot = game_env.module.get_state()

    game_env.module.load_state(snapshot)
    assert game_env.module.plots == original_plot_objects
    for plot, before in zip(game_env.module.plots, original_plot_objects):
        assert plot is before


def test_load_state_restores_replanting_plot_and_its_recovery_timer(game_env):
    game_env.select(0)
    game_env.clear()  # PRESERVED -> BARE, so it can be replanted below
    game_env.replant()  # BARE -> REPLANTING
    game_env.tick(4)
    snapshot = game_env.module.get_state()
    ticks_remaining_before = game_env.plot(0).replant_ticks_remaining
    assert game_env.plot(0).state == game_env.module.REPLANTING

    game_env.tick(4)  # diverge — timer keeps counting down
    assert game_env.plot(0).replant_ticks_remaining != ticks_remaining_before

    game_env.module.load_state(snapshot)
    assert game_env.plot(0).state == game_env.module.REPLANTING
    assert game_env.plot(0).replant_ticks_remaining == ticks_remaining_before


def test_load_state_restores_pending_stakeholder_request_to_none(game_env):
    game_env.tick(game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS + 1)
    assert game_env.module.pending_stakeholder_request is not None
    snapshot_before_request = {
        **game_env.module.get_state(),
        "pending_stakeholder_request": None,
    }

    game_env.module.load_state(snapshot_before_request)
    assert game_env.module.pending_stakeholder_request is None


def test_load_state_re_renders_the_ui(game_env):
    game_env.tick(3)
    game_env.select(0)
    game_env.clear()
    snapshot = game_env.module.get_state()
    income_text_after_snapshot = game_env.elements["income-display"].innerText

    game_env.select(1)
    game_env.clear()  # diverges total_income, and re-renders with the new value
    assert game_env.elements["income-display"].innerText != income_text_after_snapshot

    game_env.module.load_state(snapshot)
    # income-display is only updated inside render() — a stale value here
    # would mean load_state() forgot to re-render.
    assert game_env.elements["income-display"].innerText == income_text_after_snapshot


def test_load_state_on_an_empty_dict_does_not_raise_and_leaves_state_untouched(game_env):
    """Bug sweep (2026-09-06): a previous version of this test pinned
    load_state({}) as *intended* to raise KeyError, on the theory that a
    real save always comes from this same site's own get_state() so a
    malformed payload can only mean hand-edited garbage. That reasoning
    ignores forward-compatibility across this game's own version history —
    every field below (`biodiversity`, `pending_stakeholder_request`,
    `info_page_open`, ...) was added in a later milestone/pass than the one
    before it, so a save written before that pass is a *legitimate*, no-
    editing-involved dict missing that key, not a corrupted one. This exact
    bug class (bare `data["key"]` / wholesale dict-replace on load, so an
    older-format save crashes the next render/tick with a KeyError) has
    recurred across nearly every game in this hub — see BCM114-DEV-LOG.md's
    2026-09-02 entries. Fixed to merge key-by-key with a fallback to the
    current live value, so a missing key just means "don't touch this
    field" instead of crashing."""
    before = game_env.module.get_state()
    result = game_env.module.load_state({})
    assert result is True
    assert game_env.module.get_state() == before


def test_load_state_survives_a_plot_dict_missing_a_field_added_in_a_later_pass(game_env):
    """Simulates loading a save written before `biodiversity` existed on a
    plot (added in Iteration Pass 2) -- the other fields should still
    restore normally, and the missing field should fall back to the plot's
    current live value instead of raising."""
    game_env.select(0)
    game_env.clear()  # PRESERVED -> BARE
    game_env.replant()  # BARE -> REPLANTING
    game_env.tick(3)
    snapshot = game_env.module.get_state()
    old_format_plots = [dict(p) for p in snapshot["plots"]]
    del old_format_plots[0]["biodiversity"]
    old_format_snapshot = {**snapshot, "plots": old_format_plots}

    # Diverge every plot's live biodiversity before loading the old save.
    for plot in game_env.module.plots:
        plot.biodiversity = 999.0

    result = game_env.module.load_state(old_format_snapshot)
    assert result is True
    # Plot 0's biodiversity wasn't in the old-format save, so it's left at
    # whatever it was live (not crashed, not silently reset to 0).
    assert game_env.plot(0).biodiversity == 999.0
    # Every other tracked field on plot 0, and every field on the other
    # plots (whose dicts *did* carry biodiversity), still restores.
    assert game_env.plot(0).state == game_env.module.REPLANTING
    assert game_env.plot(0).replant_ticks_remaining == old_format_plots[0]["replant_ticks_remaining"]
    assert game_env.plot(1).biodiversity == old_format_plots[1]["biodiversity"]


def test_load_state_survives_a_top_level_key_missing_from_an_older_save(game_env):
    """Simulates a save written before `info_page_open` / stakeholder-
    tension state existed at the top level at all -- missing top-level keys
    must fall back to the current live value rather than raising."""
    game_env.module.info_page_open = True
    game_env.module.community_relations = 77
    snapshot = game_env.module.get_state()
    old_format_snapshot = dict(snapshot)
    del old_format_snapshot["info_page_open"]
    del old_format_snapshot["pending_stakeholder_request"]

    game_env.module.info_page_open = False  # diverge before loading
    game_env.module.community_relations = 12

    result = game_env.module.load_state(old_format_snapshot)
    assert result is True
    # community_relations *was* in the save, so it restores normally.
    assert game_env.module.community_relations == 77
    # info_page_open and pending_stakeholder_request were missing from the
    # save -- left at their current live value instead of crashing.
    assert game_env.module.info_page_open is False
    assert game_env.module.pending_stakeholder_request is None
