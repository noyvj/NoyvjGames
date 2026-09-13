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
        "visited_bodies",
        "current_planet",
        "governor_priority",
        "governor_budget_pct",
        "governor_tick_count",
        "governor_purchase_count",
        "achievements_earned",
    }


def test_serialize_state_converts_unlocked_bodies_set_to_a_list(game_env):
    game_env.module.unlocked_bodies.add("Mars")
    data = game_env.module.serialize_state()
    assert isinstance(data["unlocked_bodies"], list)
    assert data["unlocked_bodies"] == ["Mars"]


def test_serialize_state_converts_visited_bodies_set_to_a_list(game_env):
    game_env.module.unlocked_bodies.add("Mars")
    game_env.travel_to_mars()
    data = game_env.module.serialize_state()
    assert isinstance(data["visited_bodies"], list)
    assert data["visited_bodies"] == ["Earth", "Mars"]


def test_deserialize_state_restores_visited_bodies_as_a_set(game_env):
    game_env.module.visited_bodies.add("Mars")
    snapshot = game_env.module.serialize_state()

    game_env.module.visited_bodies.clear()
    game_env.module.deserialize_state(snapshot)

    assert game_env.module.visited_bodies == {"Earth", "Mars"}
    assert isinstance(game_env.module.visited_bodies, set)


def test_deserialize_state_falls_back_to_default_visited_bodies_when_key_is_missing(game_env):
    """An old save made before this field existed has no "visited_bodies"
    key at all -- must fall back to whatever's already live rather than
    crashing or silently forgetting every world the player already visited
    this session."""
    game_env.module.unlocked_bodies.add("Mars")
    game_env.travel_to_mars()
    game_env.return_to_earth()
    snapshot = game_env.module.serialize_state()
    del snapshot["visited_bodies"]

    game_env.module.deserialize_state(snapshot)

    assert "Earth" in game_env.module.visited_bodies
    assert "Mars" in game_env.module.visited_bodies


def test_deserialize_state_adds_current_planet_to_visited_bodies_even_on_an_old_save(game_env):
    """Wherever a save says the player currently is, they have -- by
    definition -- actually been there. A save from before "visited_bodies"
    existed, loaded mid-Mars-trip, must not forget Mars was ever visited
    until the player travels there again."""
    game_env.module.unlocked_bodies.add("Mars")
    game_env.travel_to_mars()
    snapshot = game_env.module.serialize_state()
    del snapshot["visited_bodies"]
    game_env.module.visited_bodies = {"Earth"}  # simulate a fresh module, pre-travel

    game_env.module.deserialize_state(snapshot)

    assert game_env.module.current_planet == "Mars"
    assert "Mars" in game_env.module.visited_bodies


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


def test_deserialize_state_tolerates_a_save_missing_a_planet(game_env):
    """Defensive backward-compat: deserialize_state() used to `.clear()`
    planet_state before `.update()`-ing it with the loaded dict, so any
    planet absent from that dict (an older save format predating some
    body's economy, or a corrupted payload) vanished from planet_state
    entirely rather than just keeping its pre-load state -- and the next
    tick()'s `for planet in PLANETS: ... planet_state[planet]` loop would
    KeyError and crash the whole game. Loading must never be able to do
    that, per the project's "no dead-end/unwinnable states" rule."""
    game_env.click("Moon")
    game_env.click("Moon")
    snapshot = game_env.module.serialize_state()
    del snapshot["planet_state"]["Moon"]

    game_env.module.deserialize_state(snapshot)

    assert "Moon" in game_env.module.planet_state
    assert game_env.module.planet_state["Moon"]["resource_count"] == 2
    game_env.module.tick()  # must not raise KeyError


def test_deserialize_state_tolerates_a_save_missing_a_newer_planet_field(game_env):
    """Same bug class one level down: deserialize_state() used to
    `.update()` a present planet's saved sub-dict straight onto
    planet_state[planet], swapping in the whole dict rather than merging
    key-by-key. A save made before a later milestone added a new
    per-planet field (e.g. "terraform_progress", added in Milestone 8)
    would then wipe that field's freshly-initialized default for any
    planet the save DOES include, and the very next tick() (which reads
    "terraform_progress" for every planet unconditionally) would KeyError
    and crash the whole game."""
    game_env.click("Moon")
    game_env.click("Moon")
    snapshot = game_env.module.serialize_state()
    del snapshot["planet_state"]["Moon"]["terraform_progress"]

    game_env.module.deserialize_state(snapshot)

    assert "terraform_progress" in game_env.module.planet_state["Moon"]
    assert game_env.module.planet_state["Moon"]["resource_count"] == 2
    game_env.module.tick()  # must not raise KeyError


def test_deserialize_state_tolerates_a_save_missing_a_top_level_scalar(game_env):
    """Same bug class one level further OUT: the planet_state merge fix
    (and its per-planet-field follow-up) only protects the nested
    dictionaries. deserialize_state() still read every top-level scalar
    (research_progress, completed_tiers, unlocked_bodies, current_planet,
    governor_priority, governor_budget_pct, governor_tick_count) via bare
    `data["key"]` indexing, so a save missing any single one of these --
    a corrupted payload, or a hand-edited/truncated save code -- would
    KeyError immediately inside deserialize_state() itself, before the
    game even got as far as the next tick(). Missing a top-level scalar
    must fall back to whatever is already live instead of crashing, same
    "never let a partial save nuke the game" principle as the nested
    fixes."""
    game_env.click("Earth")
    game_env.module.unlocked_bodies.add("Mars")
    game_env.travel_to_mars()
    game_env.module.governor_priority = "ecology"
    game_env.module.governor_budget_pct = 75.0
    game_env.module.governor_tick_count = 3
    game_env.module.on_fund_research(None)  # nudge research_progress off zero
    full_snapshot = game_env.module.serialize_state()

    top_level_scalar_keys = [
        "research_progress",
        "completed_tiers",
        "unlocked_bodies",
        "visited_bodies",
        "current_planet",
        "governor_priority",
        "governor_budget_pct",
        "governor_tick_count",
        "governor_purchase_count",
    ]
    for key in top_level_scalar_keys:
        partial_save = dict(full_snapshot)
        del partial_save[key]

        game_env.module.deserialize_state(partial_save)  # must not raise KeyError
        game_env.module.tick()  # must not raise KeyError either
        game_env.module._full_render()


def test_deserialize_state_tolerates_a_save_missing_planet_state_entirely(game_env):
    """Defense-in-depth companion to the scalar test above: even the
    top-level "planet_state" key itself must not be assumed present."""
    game_env.click("Earth")
    full_snapshot = game_env.module.serialize_state()
    partial_save = dict(full_snapshot)
    del partial_save["planet_state"]

    game_env.module.deserialize_state(partial_save)  # must not raise KeyError
    game_env.module.tick()  # must not raise KeyError


def test_deserialize_state_restores_scalar_globals(game_env):
    game_env.module.unlocked_bodies.add("Mars")
    game_env.travel_to_mars()
    game_env.module.governor_priority = "ecology"
    game_env.module.governor_budget_pct = 75.0
    game_env.module.governor_purchase_count = 4
    snapshot = game_env.module.serialize_state()

    game_env.module.governor_priority = "growth"
    game_env.module.governor_budget_pct = 10.0
    game_env.module.governor_purchase_count = 0

    game_env.module.deserialize_state(snapshot)
    assert game_env.module.current_planet == "Mars"
    assert game_env.module.governor_priority == "ecology"
    assert game_env.module.governor_budget_pct == 75.0
    assert game_env.module.governor_purchase_count == 4


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


def test_get_state_matches_serialize_state(game_env):
    """SAVE-BUTTON-INTEGRATION.md contract: get_state() is the shared
    widget's entry point, distinct from get_save_state_json() (which the
    old bespoke bridge used) only in that it returns the dict directly
    rather than a JSON string — the widget does its own JS<->Pyodide
    conversion instead of a string handoff."""
    game_env.click("Earth")
    assert game_env.module.get_state() == game_env.module.serialize_state()


def test_load_state_full_round_trip(game_env):
    game_env.click("Earth")
    game_env.click("Earth")
    game_env.click("Earth")
    snapshot = game_env.module.get_state()

    game_env.click("Earth")  # diverge
    assert game_env.earth["resource_count"] == 4

    result = game_env.module.load_state(snapshot)
    assert result is True
    assert game_env.earth["resource_count"] == 3


def test_load_state_is_the_exact_inverse_of_get_state(game_env):
    """A save taken via the new contract must restore correctly even
    though it never crosses a JSON string boundary — get_state()/
    load_state() hand the dict straight across, same as the shared
    widget's own JS<->Pyodide dict conversion would."""
    game_env.module.unlocked_bodies.add("Mars")
    game_env.travel_to_mars()
    game_env.module.governor_priority = "ecology"
    snapshot = game_env.module.get_state()

    game_env.module.governor_priority = "growth"
    game_env.module.deserialize_state(
        {**game_env.module.serialize_state(), "current_planet": "Earth"}
    )

    game_env.module.load_state(snapshot)
    assert game_env.module.current_planet == "Mars"
    assert game_env.module.governor_priority == "ecology"
