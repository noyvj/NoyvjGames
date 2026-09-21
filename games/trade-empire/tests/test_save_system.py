"""Shared save widget integration (SAVE-BUTTON-INTEGRATION.md): get_state()
packages every module-level mutable global into one plain, JSON-safe dict,
and load_state() is its exact inverse. Trade Empire is not the reference
integration (SOL is) — this just adopts the same contract, following the
pattern already used by every other hub-linked game (see e.g. Canopy's
tests/test_save_system.py)."""

import json


def test_get_state_includes_every_expected_key(game_env):
    data = game_env.module.get_state()
    assert set(data.keys()) == {
        "ships",
        "total_profit",
        "sale_log",
        "market_multiplier",
        "colony_states",
        "research_points",
        "unlocked_research",
        "fleet_priority_enabled",
        "endgame_reached",
        "ticks_since_endgame",
        "total_sales_count",
        "max_profit_ever",
        "goods_sold_ever",
        "ever_repositioned",
        "market_crash_ever",
        "good_profit_total",
        "good_trip_count",
        "good_profit_recent",
        "price_history",
        "need_history",
        "seen_first_automation_callout",
        "seasonal_demand",
        "cross_system_units",
        "route_hazards",
        "stockpile",
        "trade_posts",
        "achievements_earned",
    }


def test_get_state_expands_every_ship_into_a_plain_dict(game_env):
    data = game_env.module.get_state()
    assert set(data["ships"].keys()) == {"1", "2", "3", "4", "5", "6"}
    for ship_data in data["ships"].values():
        assert set(ship_data.keys()) == {
            "location",
            "origin",
            "destination",
            "cargo_good",
            "cargo_qty",
            "transit_ticks_remaining",
            "transit_total_ticks",
            "automated",
            "purchased",
            "archetype",
            "name",
            "idle_ticks",
            "route_key",
            "route_legs",
            "total_earned",
        }


def test_get_state_only_includes_currently_existing_colony_states(game_env):
    data = game_env.module.get_state()
    # Kepler Cluster colony_states don't exist yet -- galaxy_expansion isn't
    # unlocked in a fresh session.
    assert set(data["colony_states"].keys()) == {"aurum", "verdant", "ferrum", "cryo", "helion"}


def test_get_state_is_json_serialisable(game_env):
    data = game_env.module.get_state()
    json.dumps(data)  # raises if anything isn't a plain JSON-safe type


def test_load_state_full_round_trip_restores_every_tracked_field(game_env):
    module = game_env.module
    game_env.load("1")
    game_env.depart("verdant", "1")
    game_env.automate("2")
    module.research_points = 100
    module.unlock_research("fast_ships")
    module.set_fleet_priority(True)
    game_env.tick(3)

    saved = module.get_state()

    # Mutate live state so the round trip is actually meaningful.
    module.total_profit = 99999
    module.ships["1"].cargo_qty = 0
    module.set_fleet_priority(False)

    result = module.load_state(saved)
    assert result is True

    restored = module.get_state()
    assert restored["total_profit"] == saved["total_profit"]
    assert restored["ships"] == saved["ships"]
    assert restored["fleet_priority_enabled"] is True
    assert restored["unlocked_research"] == ["fast_ships"]


def test_load_state_recreates_kepler_colony_states_when_save_has_expansion_unlocked(game_env):
    module = game_env.module
    saved = module.get_state()
    saved["unlocked_research"] = ["galaxy_expansion"]

    module.load_state(saved)

    assert "kepler_a" in module.colony_states
    assert "kepler_b" in module.colony_states
    assert "kepler_c" in module.colony_states
    assert module.galaxy_expansion_unlocked() is True


def test_load_state_re_renders_the_ui(game_env):
    module = game_env.module
    saved = module.get_state()
    saved["total_profit"] = 4242
    module.load_state(saved)
    assert "4242" in game_env.elements["profit-display-text"].innerText


def test_load_state_on_an_empty_dict_does_not_raise_and_leaves_state_untouched(game_env):
    module = game_env.module
    before = module.get_state()
    result = module.load_state({})
    assert result is True
    after = module.get_state()
    assert after == before


def test_load_state_survives_a_ship_dict_missing_a_field(game_env):
    module = game_env.module
    saved = module.get_state()
    del saved["ships"]["1"]["cargo_qty"]

    module.load_state(saved)

    # Falls back to whatever's already live rather than crashing.
    assert module.ships["1"].cargo_qty == 0


def test_load_state_survives_a_top_level_key_missing_from_an_older_save(game_env):
    module = game_env.module
    saved = module.get_state()
    del saved["research_points"]

    result = module.load_state(saved)

    assert result is True
