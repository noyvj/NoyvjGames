"""Shared save widget integration (SAVE-BUTTON-INTEGRATION.md). Grid's
get_state()/load_state() are the per-game contract the shared
shared/save-widget.js drives — get_state() packages the GridState
instance's attributes (plus the info-page toggle) into one JSON-safe
dict, load_state() is its exact inverse and re-renders. Unlike SOL, Grid
has no non-JSON-native types (no sets) in its state, which the
json.dumps round trip below confirms directly.
"""

import json


EXPECTED_KEYS = {
    "round_number",
    "demand",
    "funds",
    "plant_counts",
    "cumulative_built",
    "emissions",
    "event_log",
    "last_event",
    "clean_fraction_log",
    "emissions_history",
    "avg_renewable_cost_history",
    "renewable_unlocked",
    "plant_age",
    "global_reference_emissions",
    "global_reference_emissions_history",
    "last_aging_event",
    "info_page_open",
}


def test_get_state_includes_every_expected_key(game_env):
    data = game_env.module.get_state()
    assert set(data.keys()) == EXPECTED_KEYS


def test_get_state_deep_copies_nested_containers(game_env):
    """A snapshot must not alias live mutable containers — building more
    plants (or advancing a round) after taking the snapshot must not
    silently change what was already "saved"."""
    game_env.build("coal")
    snapshot = game_env.module.get_state()

    game_env.build("gas")
    game_env.advance_round()

    assert snapshot["plant_counts"]["gas"] == 0
    assert game_env.state.plant_counts["gas"] == 1
    assert snapshot["event_log"] == []
    assert snapshot["round_number"] == 1
    assert game_env.state.round_number == 2


def test_load_state_deep_copies_the_input_dict(game_env):
    """The inverse aliasing risk: mutating the dict handed to load_state()
    afterwards must not reach back into live game state."""
    game_env.build("coal")
    data = game_env.module.get_state()

    game_env.module.load_state(data)
    data["plant_counts"]["coal"] = 999
    data["plant_age"]["coal"] = 999.0

    assert game_env.state.plant_counts["coal"] == 1
    assert game_env.state.plant_age["coal"] != 999.0


def test_full_round_trip_restores_every_tracked_field(game_env):
    state = game_env.state

    game_env.build("coal")
    game_env.build("solar")
    game_env.advance_round()
    game_env.advance_round()
    game_env.toggle_info_page()

    # Seed the harder-to-trigger event fields directly, so the round trip
    # exercises the full dict shape rather than only whatever the
    # probabilistic disruption/aging systems happened to fire.
    state.last_event = {"type": "damage", "severity": 0.7, "revenue_loss": 12.5, "damaged_plant": "coal"}
    state.event_log.append(dict(state.last_event))
    state.last_aging_event = {"type": "aging_breakdown", "plant": "coal", "repair_cost": 30.0}

    snapshot = game_env.module.get_state()

    # Diverge from the snapshot in every field before loading it back.
    game_env.build("wind")
    game_env.advance_round()
    game_env.toggle_info_page()
    state.last_event = None
    state.last_aging_event = None
    assert game_env.module.get_state() != snapshot

    result = game_env.module.load_state(snapshot)

    assert result is True
    assert game_env.module.get_state() == snapshot
    assert state.round_number == snapshot["round_number"]
    assert state.demand == snapshot["demand"]
    assert state.funds == snapshot["funds"]
    assert state.plant_counts == snapshot["plant_counts"]
    assert state.cumulative_built == snapshot["cumulative_built"]
    assert state.emissions == snapshot["emissions"]
    assert state.event_log == snapshot["event_log"]
    assert state.last_event == snapshot["last_event"]
    assert state.clean_fraction_log == snapshot["clean_fraction_log"]
    assert state.emissions_history == snapshot["emissions_history"]
    assert state.avg_renewable_cost_history == snapshot["avg_renewable_cost_history"]
    assert state.renewable_unlocked == snapshot["renewable_unlocked"]
    assert state.plant_age == snapshot["plant_age"]
    assert state.global_reference_emissions == snapshot["global_reference_emissions"]
    assert state.global_reference_emissions_history == snapshot["global_reference_emissions_history"]
    assert state.last_aging_event == snapshot["last_aging_event"]
    assert game_env.module.info_page_open == snapshot["info_page_open"]


def test_load_state_re_renders_the_ui(game_env):
    game_env.build("coal")
    game_env.build("coal")
    snapshot = game_env.module.get_state()

    game_env.build("gas")  # diverge

    game_env.module.load_state(snapshot)

    assert game_env.elements["funds-display"].innerText == f"Funds: {game_env.state.funds:.0f}"
    assert game_env.elements["coal-count"].innerText == "2"
    assert game_env.elements["gas-count"].innerText == "0"


def test_load_state_re_renders_the_info_page_visibility(game_env):
    game_env.toggle_info_page()  # open it
    snapshot = game_env.module.get_state()
    assert snapshot["info_page_open"] is True

    game_env.toggle_info_page()  # close it, diverging from the snapshot
    assert game_env.elements["info-page-panel"].hidden is True

    game_env.module.load_state(snapshot)
    assert game_env.module.info_page_open is True
    assert game_env.elements["info-page-panel"].hidden is False


def test_get_state_round_trips_cleanly_through_json(game_env):
    """Confirms every value in the dict is genuinely JSON-native (Grid
    tracks no sets or other non-JSON types, unlike SOL's unlocked_bodies)
    — json.dumps would raise on anything that wasn't."""
    game_env.build("coal")
    game_env.build("wind")
    game_env.advance_round()
    game_env.toggle_info_page()

    data = game_env.module.get_state()
    raw = json.dumps(data)
    restored = json.loads(raw)

    assert restored == data

    game_env.build("hydro")  # diverge
    result = game_env.module.load_state(restored)

    assert result is True
    assert game_env.state.plant_counts == data["plant_counts"]
    assert game_env.state.round_number == data["round_number"]
