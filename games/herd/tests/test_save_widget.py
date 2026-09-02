"""Shared save widget integration (SAVE-BUTTON-INTEGRATION.md): get_state()
packages every module-level mutable game-state field into one plain,
JSON-safe dict, and load_state() is its exact inverse. SOL is the reference
integration for this contract; Herd's game.py has no pre-existing bespoke
save system, so get_state()/load_state() are the whole implementation here.
"""

import json


def test_get_state_includes_every_expected_key(game_env):
    data = game_env.module.get_state()
    assert set(data.keys()) == {
        "round_number",
        "funds",
        "herd_size",
        "methane",
        "decoupling_investment",
        "plant_pivot_investment",
    }


def test_get_state_matches_initial_farm_state(game_env):
    data = game_env.module.get_state()
    assert data["round_number"] == 1
    assert data["funds"] == 300
    assert data["herd_size"] == 0
    assert data["methane"] == 0
    assert data["decoupling_investment"] == {"feed": 0, "caps": 0, "capture": 0}
    assert data["plant_pivot_investment"] == 0


def test_get_state_is_json_serialisable(game_env):
    game_env.grow_herd()
    game_env.invest_decoupling("capture")
    game_env.invest_plant_pivot()
    game_env.advance_round()

    data = game_env.module.get_state()
    round_tripped = json.loads(json.dumps(data))
    assert round_tripped == data


def test_get_state_deep_copies_decoupling_investment(game_env):
    """A dict handed back by reference would let further play silently
    mutate an already-taken snapshot — same reasoning as SOL's
    serialize_state() docstring for planet_state."""
    data = game_env.module.get_state()
    data["decoupling_investment"]["feed"] = 99
    assert game_env.farm.decoupling_investment["feed"] == 0


def test_load_state_full_round_trip_restores_every_field(game_env):
    # Build up a distinctive, non-default state across every tracked field.
    game_env.grow_herd()
    game_env.grow_herd()
    game_env.grow_herd()
    game_env.invest_decoupling("feed")
    game_env.invest_decoupling("caps")
    game_env.invest_decoupling("caps")
    game_env.invest_decoupling("capture")
    game_env.invest_plant_pivot()
    game_env.invest_plant_pivot()
    game_env.advance_round()
    game_env.advance_round()

    snapshot = game_env.module.get_state()
    assert snapshot["round_number"] == 3
    assert snapshot["herd_size"] == 3
    assert snapshot["decoupling_investment"] == {"feed": 1, "caps": 2, "capture": 1}
    assert snapshot["plant_pivot_investment"] == 2

    # Diverge significantly from the snapshot.
    game_env.grow_herd()
    game_env.grow_herd()
    game_env.invest_decoupling("feed")
    game_env.invest_plant_pivot()
    game_env.advance_round()
    game_env.advance_round()
    game_env.advance_round()
    assert game_env.farm.herd_size == 5
    assert game_env.farm.round_number == 6
    assert game_env.farm.decoupling_investment["feed"] == 2
    assert game_env.farm.plant_pivot_investment == 3

    result = game_env.module.load_state(snapshot)

    assert result is True
    assert game_env.farm.round_number == 3
    assert game_env.farm.funds == snapshot["funds"]
    assert game_env.farm.herd_size == 3
    assert game_env.farm.methane == snapshot["methane"]
    assert game_env.farm.decoupling_investment == {"feed": 1, "caps": 2, "capture": 1}
    assert game_env.farm.plant_pivot_investment == 2


def test_load_state_re_renders_the_ui(game_env):
    game_env.grow_herd()
    game_env.grow_herd()
    game_env.advance_round()
    snapshot = game_env.module.get_state()

    game_env.grow_herd()  # diverge
    assert game_env.elements["herd-display"].innerText == "Herd size: 3"

    game_env.module.load_state(snapshot)
    assert game_env.elements["herd-display"].innerText == "Herd size: 2"
    assert game_env.elements["round-display"].innerText == "Round 2"


def test_load_state_restores_a_json_round_tripped_snapshot(game_env):
    """The shared widget hands the dict straight across the Pyodide
    boundary (no JSON string involved), but a save loaded back from the
    backend on a later visit has been through JSON at least once — confirm
    that round trip doesn't lose anything load_state() needs."""
    game_env.grow_herd()
    game_env.invest_decoupling("caps")
    game_env.invest_plant_pivot()
    game_env.advance_round()
    snapshot = json.loads(json.dumps(game_env.module.get_state()))

    game_env.grow_herd()  # diverge
    game_env.invest_decoupling("feed")

    game_env.module.load_state(snapshot)
    assert game_env.farm.herd_size == 1
    assert game_env.farm.decoupling_investment == {"feed": 0, "caps": 1, "capture": 0}
    assert game_env.farm.plant_pivot_investment == 1


def test_load_state_backfills_a_decoupling_measure_missing_from_an_older_save(game_env):
    """load_state() must merge decoupling_investment key-by-key against the
    live DECOUPLING_MEASURES set rather than wholesale-replacing the dict
    with whatever the save happened to contain. A save missing a measure
    (an older save format from before that measure existed, or a
    hand-edited/corrupted payload) must not wipe that measure's key out of
    the live dict entirely -- render() and _efficiency_coupling_ratio()
    both do `decoupling_investment[measure]` for every measure in
    DECOUPLING_MEASURES unconditionally, so a missing key would crash the
    game on the very next render/round rather than just resuming with 0
    invested in that measure."""
    game_env.grow_herd()
    game_env.invest_decoupling("caps")
    snapshot = game_env.module.get_state()
    del snapshot["decoupling_investment"]["capture"]  # simulate an older/short save

    result = game_env.module.load_state(snapshot)

    assert result is True
    assert game_env.farm.decoupling_investment == {"feed": 0, "caps": 1, "capture": 0}
    # A subsequent render (as happens every real interaction) must not
    # raise KeyError for the backfilled measure.
    game_env.invest_decoupling("capture")
    assert game_env.farm.decoupling_investment["capture"] == 1
