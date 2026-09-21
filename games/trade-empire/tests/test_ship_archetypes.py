"""J5 -- ship archetypes chosen when buying ship 5 or 6."""


def _rich(game):
    game.total_profit = 10_000


def _dock_and_load(game, ship):
    ship.location = "aurum"
    ship.cargo_good = None
    ship.cargo_qty = 0
    assert ship.load()
    return ship.cargo_qty


def test_the_starting_ships_are_balanced(game_env):
    game = game_env.module
    assert all(s.archetype == "balanced" for s in game.ships.values())
    assert game.archetype_for(game.ships["1"]) == game.SHIP_ARCHETYPES["balanced"]


def test_purchase_records_the_chosen_archetype(game_env):
    game = game_env.module
    _rich(game)
    assert game.purchase_ship("5", "fast")
    assert game.ships["5"].archetype == "fast"
    assert game.purchase_ship("6", "cargo")
    assert game.ships["6"].archetype == "cargo"


def test_an_unknown_archetype_falls_back_to_balanced(game_env):
    game = game_env.module
    _rich(game)
    assert game.purchase_ship("5", "warp-drive")
    assert game.ships["5"].archetype == "balanced"


def test_the_buy_button_reads_the_select(game_env):
    game = game_env.module
    _rich(game)
    game_env.elements["ship-5-archetype-select"].value = "cargo"
    game_env.elements["ship-5-purchase-button"].dispatch("click", None)
    assert game.ships["5"].purchased and game.ships["5"].archetype == "cargo"


def test_cargo_heavy_carries_more_and_fast_carries_less(game_env):
    game = game_env.module
    _rich(game)
    game.purchase_ship("5", "cargo")
    game.purchase_ship("6", "fast")
    balanced = _dock_and_load(game, game.ships["1"])
    heavy = _dock_and_load(game, game.ships["5"])
    fast = _dock_and_load(game, game.ships["6"])
    assert heavy > balanced > fast >= 1


def test_travel_time_follows_the_archetype_and_never_drops_below_one_tick(game_env):
    game = game_env.module
    _rich(game)
    game.purchase_ship("5", "cargo")
    game.purchase_ship("6", "fast")
    base = game.travel_ticks()
    for ship_id, delta in (("1", 0), ("5", 1), ("6", -1)):
        ship = game.ships[ship_id]
        ship.location = "aurum"
        ship._begin_transit("ferrum")
        assert ship.transit_total_ticks == max(1, base + delta)
    game.TRAVEL_TICKS = 1
    fast = game.ships["6"]
    fast.location = "aurum"
    fast._begin_transit("ferrum")
    assert fast.transit_total_ticks == 1


def test_label_names_a_non_balanced_archetype(game_env):
    game = game_env.module
    _rich(game)
    game.purchase_ship("5", "fast")
    game.render()
    assert "(Fast)" in game_env.elements["ship-5-label"].innerText
    assert "(" not in game_env.elements["ship-1-label"].innerText


def test_archetype_round_trips_and_bad_values_fall_back(game_env):
    game = game_env.module
    _rich(game)
    game.purchase_ship("5", "fast")
    saved = game.get_state()
    assert saved["ships"]["5"]["archetype"] == "fast"
    game.ships["5"].archetype = "balanced"
    game.load_state(saved)
    assert game.ships["5"].archetype == "fast"
    for bad in ("nope", 5, None, ["fast"]):
        saved["ships"]["5"]["archetype"] = bad
        game.load_state(saved)
        assert game.ships["5"].archetype == "balanced"
    del saved["ships"]["5"]["archetype"]
    game.load_state(saved)
    assert game.ships["5"].archetype == "balanced"
