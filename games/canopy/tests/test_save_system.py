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
