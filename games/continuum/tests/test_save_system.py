"""Milestone 4 — save system schema.

The design doc asks for "one continuous save spanning the whole arc, with
the ability to revisit/replay completed eras without losing forward
progress", planned early because retrofitting it after several eras were
built linearly would be painful.

Per SAVE-BUTTON-INTEGRATION.md this is *not* a bespoke save UI: the shared
`shared/save-widget.js` drives every game in the hub through the same
two-function contract, `get_state()` / `load_state(data)`. Continuum's
extra structure lives entirely *inside* the single dict `get_state()`
returns — the widget never looks in there — so Continuum gets its
era-snapshot save with zero widget changes.

So this file tests two things at once: the schema's own behaviour
(snapshots, revisits, forward progress) and the widget contract (one
JSON-safe dict, an exact inverse, no aliasing between saved and live data).
"""

import copy
import json

import pytest

import research
import sim
import sustainability
import save


EXPECTED_KEYS = {
    "save_version",
    "game",
    "era_order",
    "current_era",
    "furthest_era",
    "revisiting",
    "current_state",
    "parked_state",
    "era_snapshots",
    "ui",
}


def played(game_env, seasons=3):
    """Puts the settlement somewhere non-trivial before saving it."""
    state = game_env.state
    state.resources["knowledge"] = 100.0
    game_env.module.render()
    game_env.elements["research-fire_keeping"].dispatch("click", None)
    game_env.elements["research-foraging_lore"].dispatch("click", None)
    game_env.assign("keepers")
    game_env.state.resources["materials"] = 200.0
    game_env.build("shelter")
    game_env.advance_season(seasons)
    return state


# --- the widget contract -----------------------------------------------
def test_get_state_returns_the_documented_schema(game_env):
    data = game_env.module.get_state()

    assert set(data.keys()) == EXPECTED_KEYS
    assert data["game"] == save.GAME_ID
    assert data["save_version"] == save.SAVE_VERSION
    assert data["era_order"] == sim.ERA_ORDER
    assert data["current_era"] == "tribal"
    assert data["furthest_era"] == "tribal"
    assert data["revisiting"] is None
    assert set(data["current_state"]) == {"city", "research"}


def test_get_state_round_trips_cleanly_through_json(game_env):
    """Everything the widget POSTs has to be JSON-native — json.dumps would
    raise on a set, a tuple key, or any custom object."""
    played(game_env)

    data = game_env.module.get_state()
    restored = json.loads(json.dumps(data))

    assert restored == data
    assert game_env.module.load_state(restored) is True


def test_get_state_does_not_alias_live_containers(game_env):
    played(game_env)
    snapshot = game_env.module.get_state()

    game_env.advance_season()
    game_env.build("granary")

    assert snapshot["current_state"]["city"]["buildings"]["granary"] == 0
    assert snapshot["current_state"]["city"]["season"] != game_env.state.season


def test_load_state_does_not_alias_the_dict_it_is_given(game_env):
    played(game_env)
    data = game_env.module.get_state()

    game_env.module.load_state(data)
    data["current_state"]["city"]["resources"]["food"] = 999.0
    data["current_state"]["research"].append("fabricated")

    assert game_env.state.resources["food"] != 999.0
    assert "fabricated" not in game_env.module.tree.researched


def test_full_round_trip_restores_every_field(game_env):
    state = played(game_env)
    snapshot = game_env.module.get_state()

    # Diverge in every direction before loading the snapshot back.
    game_env.assign("crafters")
    game_env.build("hearth")
    game_env.advance_season(2)
    state.resources["knowledge"] = 12.34
    assert game_env.module.get_state() != snapshot

    assert game_env.module.load_state(snapshot) is True

    assert game_env.module.get_state() == snapshot
    city = snapshot["current_state"]["city"]
    assert state.season == city["season"]
    assert state.population == city["population"]
    assert state.resources == city["resources"]
    assert state.allocation == city["allocation"]
    assert state.buildings == city["buildings"]
    assert state.land_health == city["land_health"]
    assert state.score_history == city["score_history"]
    assert game_env.module.tree.researched == snapshot["current_state"]["research"]


def test_load_state_re_renders_the_page(game_env):
    played(game_env)
    snapshot = game_env.module.get_state()
    saved_population = game_env.state.population

    game_env.advance_season(2)  # diverge, and re-render with the new numbers

    game_env.module.load_state(snapshot)

    assert game_env.elements["population-display"].innerText == f"People: {saved_population}"
    assert game_env.elements["season-display"].innerText == (
        f"Season {snapshot['current_state']['city']['season']}"
    )
    assert game_env.elements["research-fire_keeping"].innerText == "Known"


def test_load_state_refuses_a_save_from_another_game(game_env):
    data = game_env.module.get_state()
    data["game"] = "sol"

    assert game_env.module.load_state(data) is False


def test_load_state_refuses_a_save_from_a_future_version(game_env):
    data = game_env.module.get_state()
    data["save_version"] = save.SAVE_VERSION + 5

    assert game_env.module.load_state(data) is False


def test_load_state_tolerates_a_minimal_save(game_env):
    """Forward compatibility in the other direction: a save written before
    a field existed must still load, with the field defaulted."""
    minimal = {
        "game": save.GAME_ID,
        "save_version": save.SAVE_VERSION,
        "current_state": {"city": {"population": 9, "season": 4}, "research": []},
    }

    assert game_env.module.load_state(minimal) is True
    assert game_env.state.population == 9
    assert game_env.state.season == 4
    assert game_env.state.era == "tribal"
    assert game_env.module.get_state()["era_snapshots"] == {}


def test_load_state_tolerates_a_save_whose_keyed_dicts_are_short(game_env):
    """The Phase 3 scenario: a save written today, loaded by a build that has
    since added a role, a building or a resource.

    Its `resources`/`allocation`/`buildings` dicts are missing the new keys.
    Replacing the live dicts wholesale left the settlement without them, and
    the next season (or the next render) died on a KeyError *after* the widget
    had already reported a successful load. The shape of those dicts belongs
    to sim.py; a save only carries their values.
    """
    stale = {
        "game": save.GAME_ID,
        "save_version": save.SAVE_VERSION,
        "current_state": {
            "city": {
                "population": 6,
                "resources": {"food": 10.0, "materials": 5.0},  # no tools/knowledge
                "buildings": {"shelter": 2, "hearth": 1},  # no granary/toolworks
                "allocation": {"foragers": 3, "gatherers": 2},  # no crafters/keepers
            },
            "research": [],
        },
    }

    assert game_env.module.load_state(stale) is True

    state = game_env.state
    assert set(state.resources) == {"food", "materials", "tools", "knowledge"}
    assert set(state.buildings) == set(sim.BUILDINGS)
    assert set(state.allocation) == set(sim.ROLES)
    assert state.resources["food"] == 10.0
    assert state.buildings["shelter"] == 2
    assert state.allocation["foragers"] == 3
    # The values the save didn't carry keep whatever the fresh state had.
    assert state.allocation["keepers"] == 0

    game_env.advance_season()  # would have raised KeyError
    assert state.season == 2


def test_load_state_survives_a_malformed_current_state(game_env):
    """`parked_state`/`era_snapshots`/`ui` were already type-guarded; the
    live half of the save wasn't, so a truncated or hand-edited code took the
    page down with a TypeError instead of loading what it could."""
    for broken in (
        {"game": save.GAME_ID, "current_state": None},
        {"game": save.GAME_ID, "current_state": {"city": None, "research": None}},
        {"game": save.GAME_ID, "current_state": {"research": "fire_keeping"}},
    ):
        assert game_env.module.load_state(broken) is True
        assert game_env.module.tree.researched == []
        game_env.advance_season()


def test_the_season_narration_survives_a_report_from_an_older_build(game_env):
    """`last_report` is saved, so a loaded report can predate whatever keys
    the current season loop writes. Narrating it must not take the render
    down — the same forward-compatibility rule the rest of the schema has."""
    played(game_env)
    data = game_env.module.get_state()
    data["current_state"]["city"]["last_report"] = {"season": 2, "fed_fraction": 1.0}

    assert game_env.module.load_state(data) is True
    assert game_env.elements["season-report-display"].innerText != ""


# --- era snapshots ------------------------------------------------------
def test_completing_an_era_records_a_snapshot(game_env):
    campaign = game_env.module.campaign
    played(game_env)

    snapshot = campaign.record_era_snapshot()

    assert set(snapshot) == {"era", "season", "score", "city", "research"}
    assert snapshot["era"] == "tribal"
    assert campaign.era_snapshots["tribal"] == snapshot
    assert snapshot["score"] == pytest.approx(
        sustainability.score(game_env.state, game_env.module.tree.effects())
    )


def test_an_era_snapshot_is_frozen_against_later_play(game_env):
    campaign = game_env.module.campaign
    played(game_env)
    campaign.record_era_snapshot()
    frozen = copy.deepcopy(campaign.era_snapshots["tribal"])

    game_env.build("granary")
    game_env.advance_season(3)

    assert campaign.era_snapshots["tribal"] == frozen


def test_era_snapshots_survive_a_save_load_round_trip(game_env):
    campaign = game_env.module.campaign
    played(game_env)
    campaign.record_era_snapshot()

    data = json.loads(json.dumps(game_env.module.get_state()))
    game_env.advance_season(2)
    game_env.module.load_state(data)

    assert set(campaign.era_snapshots) == {"tribal"}
    assert campaign.era_snapshots["tribal"] == data["era_snapshots"]["tribal"]


def test_advancing_an_era_snapshots_the_one_being_left(game_env):
    """Only the Tribal era exists yet, but the bookkeeping the era-transition
    framework (Phase 2) will drive is built and tested now — which is the
    whole reason the doc wants the schema designed this early."""
    campaign = game_env.module.campaign
    played(game_env)

    assert campaign.advance_to_era("agrarian") is True

    assert campaign.state.era == "agrarian"
    assert campaign.furthest_era == "agrarian"
    assert "tribal" in campaign.era_snapshots
    assert game_env.module.tree.current_era == "agrarian"
    assert game_env.module.get_state()["current_era"] == "agrarian"


def test_advancing_backwards_is_refused(game_env):
    campaign = game_env.module.campaign
    campaign.advance_to_era("agrarian")

    assert campaign.advance_to_era("tribal") is False
    assert campaign.state.era == "agrarian"


# --- revisiting a completed era ----------------------------------------
def test_revisiting_a_completed_era_restores_that_era_and_keeps_progress(game_env):
    campaign = game_env.module.campaign
    state = played(game_env)
    tribal_population = state.population
    tribal_season = state.season

    campaign.advance_to_era("agrarian")
    game_env.advance_season(2)  # forward progress, in the newer era
    forward_season = state.season

    assert campaign.enter_revisit("tribal") is True

    assert campaign.revisiting == "tribal"
    assert state.era == "tribal"
    assert state.season == tribal_season
    assert state.population == tribal_population
    # Forward progress is parked, not lost — that's the doc's requirement.
    assert campaign.furthest_era == "agrarian"
    assert campaign.parked_state["city"]["season"] == forward_season


def test_leaving_a_revisit_restores_the_parked_forward_progress(game_env):
    campaign = game_env.module.campaign
    state = played(game_env)
    campaign.advance_to_era("agrarian")
    game_env.advance_season(2)
    forward = copy.deepcopy(game_env.module.get_state()["current_state"])

    campaign.enter_revisit("tribal")
    game_env.advance_season(3)  # play around in the past

    assert campaign.exit_revisit() is True

    assert campaign.revisiting is None
    assert campaign.parked_state is None
    assert state.era == "agrarian"
    assert game_env.module.get_state()["current_state"] == forward


def test_a_revisit_can_itself_be_saved_and_resumed(game_env):
    campaign = game_env.module.campaign
    played(game_env)
    campaign.advance_to_era("agrarian")
    game_env.advance_season()
    campaign.enter_revisit("tribal")

    data = json.loads(json.dumps(game_env.module.get_state()))
    assert data["revisiting"] == "tribal"
    assert data["current_era"] == "tribal"
    assert data["furthest_era"] == "agrarian"

    game_env.advance_season(2)  # diverge
    assert game_env.module.load_state(data) is True

    assert campaign.revisiting == "tribal"
    assert campaign.furthest_era == "agrarian"
    assert campaign.exit_revisit() is True
    assert game_env.state.era == "agrarian"


def test_revisiting_an_era_that_was_never_completed_is_refused(game_env):
    campaign = game_env.module.campaign

    assert campaign.enter_revisit("medieval") is False
    assert campaign.revisiting is None


def test_leaving_a_revisit_that_never_started_is_refused(game_env):
    assert game_env.module.campaign.exit_revisit() is False


def test_load_state_refuses_revisiting_an_era_with_no_snapshot(game_env):
    """`revisiting` only ever gets set by `enter_revisit()`, which already
    checked the era has a snapshot to load. A hand-edited or corrupted save
    could claim `revisiting` for an era `era_snapshots` has no entry for at
    all — non-exploitable today because the `parked_state`-is-missing guard
    already catches the one way that reaches the live game, but that guard
    doesn't fire when `parked_state` *is* present (as here) alongside a
    `revisiting` era with no matching snapshot. Belt-and-suspenders: the
    schema shouldn't trust the save file's word for something it can check
    against its own `era_snapshots` dict."""
    campaign = game_env.module.campaign
    played(game_env)

    bogus = {
        "game": save.GAME_ID,
        "save_version": save.SAVE_VERSION,
        "current_era": "tribal",
        "revisiting": "agrarian",  # a valid era, but never completed/snapshotted
        "current_state": {"city": {"population": 6}, "research": []},
        "parked_state": {"city": {"population": 6}, "research": []},
        "era_snapshots": {},  # no "agrarian" entry
    }

    assert game_env.module.load_state(bogus) is True
    assert campaign.revisiting is None
    # Consistent with the existing "no parked_state" guard: revisiting is
    # None should keep meaning there's no forward progress parked either.
    assert campaign.parked_state is None


def test_a_revisit_does_not_overwrite_the_era_snapshot(game_env):
    """Replaying the Tribal era shouldn't silently rewrite the record of how
    the Tribal era actually went the first time."""
    campaign = game_env.module.campaign
    played(game_env)
    campaign.advance_to_era("agrarian")
    original = copy.deepcopy(campaign.era_snapshots["tribal"])

    campaign.enter_revisit("tribal")
    game_env.advance_season(4)
    campaign.exit_revisit()

    assert campaign.era_snapshots["tribal"] == original


# --- the schema in isolation -------------------------------------------
def test_a_campaign_round_trips_without_any_dom(game_env):
    """save.py must not depend on the browser layer — the schema is engine
    code, testable on its own."""
    campaign = save.Campaign(sim.CityState(), research.build_tree())
    campaign.state.advance_season()
    campaign.tree.research("fire_keeping", {"knowledge": 100.0})
    campaign.record_era_snapshot()

    data = json.loads(json.dumps(campaign.to_dict()))

    fresh = save.Campaign(sim.CityState(), research.build_tree())
    assert fresh.load_dict(data) is True
    assert fresh.to_dict() == data
    assert fresh.tree.researched == ["fire_keeping"]
    assert fresh.state.season == campaign.state.season
