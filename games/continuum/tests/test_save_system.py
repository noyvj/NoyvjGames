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
    "log",
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
    assert set(state.resources) == {"food", "materials", "tools", "knowledge", "surplus"}
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


def _push_full_arc_to_space(game_env):
    """Drives a real settlement through all six real era transitions via the
    actual shipped UI (the `advance-era-button`), the same sequence
    `tests/test_space_age_era.py`'s own `push_to_space()` helper exercises,
    condensed here so this file's revisit-staleness test below doesn't
    depend on another test module -- the same "each era test file keeps its
    own copy" convention every push-to-X helper from Milestone 8 on has
    already followed rather than cross-importing between test files."""
    state = game_env.state
    tree = game_env.module.tree

    def _advance():
        game_env.module.render()
        game_env.elements["advance-era-button"].dispatch("click", None)

    state.resources["knowledge"] = 100.0
    tree.research("fire_keeping", state.resources)
    tree.research("foraging_lore", state.resources)
    state.population = 15
    _advance()  # -> agrarian

    state.resources["knowledge"] = 1000.0
    tree.research("stone_knapping", state.resources)
    tree.research("seasonal_rounds", state.resources)
    tree.research("plow_and_furrow", state.resources)
    tree.research("seed_selection", state.resources)
    state.population = 25
    _advance()  # -> classical

    state.resources["knowledge"] = 10_000.0
    tree.research("irrigation_channels", state.resources)
    tree.research("crop_rotation", state.resources)
    tree.research("canal_engineering", state.resources)
    tree.research("managed_irrigation", state.resources)
    state.buildings["shelter"] = 10
    state.buildings["hearth"] = 5
    state.population = 40
    _advance()  # -> medieval

    state.resources["knowledge"] = 100_000.0
    tree.research("monumental_masonry", state.resources)
    tree.research("trade_networks", state.resources)
    tree.research("guild_workshops", state.resources)
    tree.research("trade_zoning", state.resources)
    state.buildings["shelter"] = 16
    state.buildings["hearth"] = 8
    state.population = 60
    _advance()  # -> industrial

    state.resources["knowledge"] = 1_000_000.0
    tree.research("master_guilds", state.resources)
    tree.research("public_sanitation", state.resources)
    tree.research("smoke_abatement", state.resources)
    tree.research("steam_power", state.resources)
    state.buildings["shelter"] = 27
    state.buildings["hearth"] = 14
    state.population = 100
    _advance()  # -> digital

    state.resources["knowledge"] = 10_000_000.0
    tree.research("sanitation_engineering", state.resources)
    tree.research("assembly_lines", state.resources)
    tree.research("data_driven_zoning", state.resources)
    tree.research("smart_utilities", state.resources)
    state.buildings["shelter"] = 40
    state.buildings["hearth"] = 20
    state.population = 150
    _advance()  # -> space


def test_an_early_snapshot_restores_correctly_after_all_six_real_transitions(game_env):
    """The concrete scenario CLAUDE.md's Phase 4 task asks this pass to
    confirm: does a snapshot taken at Tribal's own transition (the very
    first of six) still read correctly after Classical/Medieval/Industrial/
    Digital/Space Age have all since added their own roles, buildings and
    global constants? Verified against a real settlement that actually
    played through all six transitions via the shipped UI, not a
    hand-constructed snapshot -- the staleness this pass is checking for
    would only show up against snapshots this old and this real."""
    campaign = game_env.module.campaign
    _push_full_arc_to_space(game_env)
    assert set(campaign.era_snapshots) == {
        "tribal", "agrarian", "classical", "medieval", "industrial", "digital",
    }
    tribal_snapshot = campaign.era_snapshots["tribal"]
    assert tribal_snapshot["city"]["population"] == 15
    # The Tribal snapshot's own keyed dicts already carry every role/
    # building this build knows about (cumulative allocation/buildings
    # dicts, per Milestone 8's design) -- including Space Age's, at 0.
    assert tribal_snapshot["city"]["allocation"]["architects"] == 0
    assert tribal_snapshot["city"]["buildings"]["habitat_rings"] == 0

    # Build up real Space Age state that must NOT leak into the Tribal
    # revisit, and must survive the revisit round trip untouched.
    game_env.build("habitat_rings")
    game_env.assign("architects", 3)
    space_population = game_env.state.population
    space_habitat_rings = game_env.state.buildings["habitat_rings"]
    space_architects = game_env.state.allocation["architects"]

    assert campaign.enter_revisit("tribal") is True
    state = game_env.state
    assert state.era == "tribal"
    assert state.population == 15
    assert state.allocation["architects"] == 0  # not the parked Space Age value
    assert state.buildings["habitat_rings"] == 0
    assert game_env.module.tree.current_era == "tribal"
    game_env.advance_season()  # exercises sim.era_index() etc against every global table
    # Sanity: the sustainability score is well-formed (not NaN, not out of
    # its documented 0..100 range) even revisiting the earliest era after
    # every later era's global constants/effects keys have been defined.
    score = sustainability.score(state, game_env.module.tree.effects())
    assert score == score  # not NaN
    assert 0.0 <= score <= 100.0

    assert campaign.exit_revisit() is True
    assert state.era == "space"
    assert state.population == space_population  # forward progress untouched
    assert state.buildings["habitat_rings"] == space_habitat_rings
    assert state.allocation["architects"] == space_architects
    # The Tribal snapshot itself is still exactly what it was — a revisit
    # is a look back, never a rewrite, per Phase 1's own build note.
    assert campaign.era_snapshots["tribal"] == tribal_snapshot


# --- Phase 4 audit: adversarial / hand-edited saves ----------------------
# Everything below pins a specific failure mode this audit pass actually
# found by hand-loading adversarial payloads into a real Campaign, per
# CLAUDE.md's Phase 4 build notes -- not hypothetical "load_state doesn't
# crash" smoke tests, but assertions on the *specific* restored value each
# bad input used to corrupt or crash on. This game has no auth/PII at stake,
# but the shared FastAPI backend stores whatever JSON blob a client POSTs,
# so a save loaded back in a different browser session is exactly as
# untrusted as an old or a from-a-newer-build one.
def test_load_state_refuses_an_unrecognised_era_in_the_city_snapshot(game_env):
    """Before this pass, `restore_city()` wrote `current_state.city.era`
    straight into `state.era` with no validation at all -- `load_dict()`
    only re-validated `era` against `current_era` at the top level, and did
    nothing if that key was simply absent. A save (or an attacker) that set
    only the nested `city.era` to a string this build doesn't recognise
    loaded "successfully" and then raised ValueError the moment anything
    (the very next season, or a revisit) called `sim.era_index()` on it."""
    bad = {
        "game": save.GAME_ID,
        "save_version": save.SAVE_VERSION,
        "current_state": {"city": {"era": "made_up_era", "population": 10}, "research": []},
    }

    assert game_env.module.load_state(bad) is True
    assert game_env.state.era == "tribal"  # kept its prior, valid value
    game_env.advance_season()  # would have raised ValueError
    assert game_env.state.population >= 1


def test_load_state_ignores_non_numeric_values_in_keyed_dicts(game_env):
    """`null`/a string in place of a resources/allocation/buildings value
    used to be copied verbatim (CITY_KEYED_DICTS only guarded the *key set*,
    never each value's type) and crash on the very next season with a
    TypeError -- again, after the widget had already reported success."""
    played_food = game_env.state.resources["food"]
    bad = {
        "game": save.GAME_ID,
        "save_version": save.SAVE_VERSION,
        "current_state": {
            "city": {
                "resources": {"food": None, "materials": "lots"},
                "allocation": {"foragers": None},
                "buildings": {"shelter": "two"},
            },
            "research": [],
        },
    }

    assert game_env.module.load_state(bad) is True
    assert game_env.state.resources["food"] == played_food  # unaffected key kept
    assert isinstance(game_env.state.resources["materials"], float)
    assert isinstance(game_env.state.allocation["foragers"], int)
    assert isinstance(game_env.state.buildings["shelter"], int)
    game_env.advance_season()  # would have raised TypeError on any of the three


def test_load_state_clamps_negative_and_out_of_range_scalars(game_env):
    """Negative population, land_health/pollution/sprawl/fed_fraction
    outside their valid 0..1 (or era-specific) ranges all loaded verbatim
    before this pass -- not a crash, but a settlement that silently reads
    as -50 people or 3.0 fed_fraction, corrupting the sustainability score
    and the season narration without ever raising anything."""
    bad = {
        "game": save.GAME_ID,
        "save_version": save.SAVE_VERSION,
        "current_state": {
            "city": {
                "population": -50,
                "land_health": -12.0,
                "pollution": 99.0,
                "sprawl": -4.0,
                "fed_fraction": 7.5,
            },
            "research": [],
        },
    }

    assert game_env.module.load_state(bad) is True
    state = game_env.state
    assert state.population == sim.MIN_POPULATION
    assert state.land_health == sim.MIN_LAND_HEALTH
    assert state.pollution == 1.0
    assert state.sprawl == 0.0
    assert state.fed_fraction == 1.0


def test_load_state_rejects_nan_and_infinite_numbers(game_env):
    """Python's own `json.loads` accepts the non-standard `NaN`/`Infinity`
    tokens some other JSON implementations reject outright, and a bare
    `max(low, min(high, value))` clamp silently returns 1.0 or 0.0 for a
    NaN input depending on argument order rather than rejecting it -- easy
    to trust by accident. A NaN resource used to propagate forever (`x +
    nan` is always `nan`), permanently corrupting the settlement and, once
    saved again, writing back a non-standard token a stricter JSON parser
    elsewhere in the hub's stack would refuse to read at all."""
    raw = (
        '{"game": "continuum", "save_version": 1, "current_state": '
        '{"city": {"resources": {"food": NaN}, "growth_progress": Infinity}, '
        '"research": []}}'
    )
    data = json.loads(raw)
    assert data["current_state"]["city"]["resources"]["food"] != data["current_state"]["city"]["resources"]["food"]

    original_food = game_env.state.resources["food"]
    assert game_env.module.load_state(data) is True
    assert game_env.state.resources["food"] == original_food  # untouched, not NaN
    assert game_env.state.growth_progress == 0.0  # untouched, not inf
    game_env.advance_season()
    assert game_env.state.resources["food"] == game_env.state.resources["food"]  # not NaN


def test_load_state_caps_growth_progress_against_a_runaway_season_loop(game_env):
    """`advance_season()`'s own population-growth step is a `while
    growth_progress >= 1.0: ...` loop that consumes exactly 1.0 per
    iteration. A hand-edited save that sets `growth_progress` to something
    enormous used to turn that loop into an effectively unbounded iteration
    the moment a season was advanced -- a real, reproducible page-freeze,
    not merely a bad number. `GROWTH_PROGRESS_MAX` caps it to something
    legitimate play can never approach (the loop always drains it below 1.0
    before a season report is generated) while still being a no-op for
    every real save."""
    bad = {
        "game": save.GAME_ID,
        "save_version": save.SAVE_VERSION,
        "current_state": {
            "city": {"growth_progress": 10 ** 9, "buildings": {"shelter": 10 ** 6}},
            "research": [],
        },
    }

    assert game_env.module.load_state(bad) is True
    assert game_env.state.growth_progress == save.GROWTH_PROGRESS_MAX
    game_env.advance_season()  # would have hung for a very long time otherwise
    # At most GROWTH_PROGRESS_MAX whole people can have been produced by the
    # capped progress in a single season, so this stays small regardless of
    # the (also huge, but otherwise harmless) housing capacity available.
    assert game_env.state.population <= 6 + int(save.GROWTH_PROGRESS_MAX) + 1


def test_enter_revisit_refuses_an_era_snapshot_key_that_is_not_a_real_era(game_env):
    """`era_snapshots` rides in the save payload -- `load_dict()` only
    checks it's a dict, not that its keys are real eras. `enter_revisit()`
    used to trust its argument was a real era purely because it matched an
    `era_snapshots` key; a save with a bogus key let a caller "revisit" an
    era that doesn't exist at all."""
    campaign = game_env.module.campaign
    bad = {
        "game": save.GAME_ID,
        "save_version": save.SAVE_VERSION,
        "current_state": {"city": {}, "research": []},
        "era_snapshots": {"not_a_real_era": {"city": {}, "research": []}},
    }
    game_env.module.load_state(bad)

    assert campaign.enter_revisit("not_a_real_era") is False
    assert campaign.revisiting is None


def test_enter_revisit_forces_the_correct_era_despite_a_tampered_snapshot(game_env):
    """A completed era's snapshot carries its own `city.era` field, written
    by `city_snapshot()` in ordinary play. `enter_revisit()` used to trust
    that field via `restore_city()` rather than the era it was actually
    asked to load -- so a hand-edited `era_snapshots["tribal"]` snapshot
    whose own `city.era` field read something else (or something invalid,
    which `restore_city()` now refuses and leaves untouched) left
    `state.era` and `campaign.revisiting` disagreeing about what era the
    player was actually looking at."""
    campaign = game_env.module.campaign
    bad = {
        "game": save.GAME_ID,
        "save_version": save.SAVE_VERSION,
        "current_era": "agrarian",
        "furthest_era": "agrarian",
        "current_state": {"city": {"era": "agrarian", "population": 10}, "research": []},
        "era_snapshots": {"tribal": {"city": {"era": "not_a_real_era"}, "research": []}},
    }
    game_env.module.load_state(bad)

    assert campaign.enter_revisit("tribal") is True
    assert campaign.revisiting == "tribal"
    assert game_env.state.era == "tribal"
    assert game_env.module.tree.current_era == "tribal"
    game_env.advance_season()  # would have raised ValueError on the bogus era


def test_load_state_drops_keys_from_a_hypothetical_later_build(game_env):
    """The other forward-compatibility direction the task asks this audit to
    confirm: a save written by a LATER build than the one loading it, e.g.
    containing a role/building/resource/research-node key this build
    doesn't know about yet. Already correctly handled by construction --
    CITY_KEYED_DICTS' restore only ever iterates the *live* dict's own keys
    (never the save's), and ResearchTree.restore() already filters to
    `self.nodes` -- but there was no test pinning it, and it's exactly the
    scenario CLAUDE.md's own Phase 4 task description calls out by name."""
    bad = {
        "game": save.GAME_ID,
        "save_version": save.SAVE_VERSION,
        "current_state": {
            "city": {
                "allocation": {"foragers": 2, "space_marines": 999},
                "buildings": {"shelter": 1, "quantum_forge": 42},
                "resources": {"food": 5.0, "antimatter": 100.0},
            },
            "research": ["not_a_real_node_from_a_future_build"],
        },
    }

    assert game_env.module.load_state(bad) is True
    state = game_env.state
    assert "space_marines" not in state.allocation
    assert "quantum_forge" not in state.buildings
    assert "antimatter" not in state.resources
    assert state.allocation["foragers"] == 2
    assert state.buildings["shelter"] == 1
    assert state.resources["food"] == 5.0
    assert game_env.module.tree.researched == []
    game_env.advance_season()  # would have raised KeyError on any dropped key


def test_load_state_survives_unhashable_entries_in_the_logs_researched_seen(game_env):
    """`log.Chronicle.restore()` used to hand `researched_seen` straight to
    `set(...)` -- a hand-edited save putting a dict or a list in that list
    (instead of the plain node-id strings it always holds in real play)
    crashed with an unhashable-type TypeError before the entry was ever
    inspected, taking the whole `load_state()` call down with it even
    though every other part of the save was perfectly fine."""
    bad = {
        "game": save.GAME_ID,
        "save_version": save.SAVE_VERSION,
        "current_state": {"city": {}, "research": []},
        "log": {"researched_seen": [{"nested": "dict"}, "fire_keeping", ["also", "bad"]], "entries": []},
    }

    assert game_env.module.load_state(bad) is True
    assert game_env.module.campaign.log._researched_seen == {"fire_keeping"}


def test_exit_revisit_forces_furthest_era_despite_a_tampered_parked_state(game_env):
    """The same tampering risk as the snapshot case above, but for
    `parked_state` on the way back out: a hand-edited `parked_state.city.era`
    used to leave `state.era` reading whatever that field said instead of
    the era the player was actually playing before the revisit.
    `furthest_era` is the schema's own source of truth for that and can't
    be redirected by tampering with `parked_state`'s own copy of `era`."""
    campaign = game_env.module.campaign
    bad = {
        "game": save.GAME_ID,
        "save_version": save.SAVE_VERSION,
        "current_era": "tribal",
        "furthest_era": "agrarian",
        "revisiting": "tribal",
        "current_state": {"city": {"era": "tribal", "population": 6}, "research": []},
        "parked_state": {"city": {"era": "not_a_real_era", "population": 12}, "research": []},
        "era_snapshots": {"tribal": {"city": {"era": "tribal"}, "research": []}},
    }
    game_env.module.load_state(bad)
    assert campaign.revisiting == "tribal"

    assert campaign.exit_revisit() is True
    assert campaign.revisiting is None
    assert game_env.state.era == "agrarian"
    assert game_env.module.tree.current_era == "agrarian"
    game_env.advance_season()  # would have raised ValueError on the bogus era
