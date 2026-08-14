"""Save system (SAVE-SYSTEM-DESIGN.md Phase 1) reference integration:
serialize_state/deserialize_state package every module-level mutable
global into a JSON-safe dict and back, and get_save_state_json/
load_save_state_json are the plain-string bridge the JS side calls
across the Pyodide boundary.
"""

import json

import pytest


def test_serialize_state_includes_every_expected_key(game_env):
    data = game_env.module.serialize_state()
    assert set(data.keys()) == {
        "planet_state",
        "research_progress",
        "completed_tiers",
        "unlocked_bodies",
        "current_planet",
        "governor_priority",
        "governor_budget_pct",
        "governor_tick_count",
    }


def test_serialize_state_converts_unlocked_bodies_set_to_a_list(game_env):
    game_env.module.unlocked_bodies.add("Mars")
    data = game_env.module.serialize_state()
    assert isinstance(data["unlocked_bodies"], list)
    assert data["unlocked_bodies"] == ["Mars"]


def test_get_save_state_json_round_trips_through_json(game_env):
    game_env.click("Earth")
    raw = game_env.module.get_save_state_json()
    parsed = json.loads(raw)
    assert parsed == game_env.module.serialize_state()


def test_deserialize_state_restores_planet_state(game_env):
    game_env.click("Earth")
    game_env.click("Earth")
    snapshot = game_env.module.serialize_state()
    assert snapshot["planet_state"]["Earth"]["resource_count"] == 2

    game_env.click("Earth")  # diverge from the snapshot
    assert game_env.earth["resource_count"] == 3

    game_env.module.deserialize_state(snapshot)
    assert game_env.earth["resource_count"] == 2


def test_deserialize_state_restores_unlocked_bodies_as_a_set(game_env):
    game_env.module.unlocked_bodies.add("Mars")
    snapshot = game_env.module.serialize_state()

    game_env.module.unlocked_bodies.clear()
    game_env.module.deserialize_state(snapshot)

    assert game_env.module.unlocked_bodies == {"Mars"}
    assert isinstance(game_env.module.unlocked_bodies, set)


def test_deserialize_state_restores_scalar_globals(game_env):
    game_env.module.unlocked_bodies.add("Mars")
    game_env.travel_to_mars()
    game_env.module.governor_priority = "ecology"
    game_env.module.governor_budget_pct = 75.0
    snapshot = game_env.module.serialize_state()

    game_env.module.governor_priority = "growth"
    game_env.module.governor_budget_pct = 10.0

    game_env.module.deserialize_state(snapshot)
    assert game_env.module.current_planet == "Mars"
    assert game_env.module.governor_priority == "ecology"
    assert game_env.module.governor_budget_pct == 75.0


def test_load_save_state_json_full_round_trip(game_env):
    game_env.click("Earth")
    game_env.click("Earth")
    game_env.click("Earth")
    saved_json = game_env.module.get_save_state_json()

    game_env.click("Earth")  # diverge
    assert game_env.earth["resource_count"] == 4

    result = game_env.module.load_save_state_json(saved_json)
    assert result is True
    assert game_env.earth["resource_count"] == 3


def test_load_save_state_json_switches_the_visible_view(game_env):
    game_env.module.unlocked_bodies.add("Mars")
    game_env.travel_to_mars()
    saved_json = game_env.module.get_save_state_json()

    game_env.module.deserialize_state(
        {**game_env.module.serialize_state(), "current_planet": "Earth"}
    )
    game_env.module._full_render()
    assert game_env.elements["earth-view"].hidden is False
    assert game_env.elements["mars-view"].hidden is True

    game_env.module.load_save_state_json(saved_json)
    assert game_env.elements["mars-view"].hidden is False
    assert game_env.elements["earth-view"].hidden is True
