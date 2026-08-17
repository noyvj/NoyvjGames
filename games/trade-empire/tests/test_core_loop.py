def test_ship_starts_docked_at_aurum_empty(game_env):
    assert game_env.ship().location == "aurum"
    assert not game_env.ship().loaded
    assert not game_env.ship().in_transit


def test_load_button_disabled_when_already_loaded(game_env):
    game_env.load()
    assert game_env.elements["ship-1-load-button"].disabled is True


def test_depart_buttons_hidden_until_loaded(game_env):
    assert game_env.elements["ship-1-depart-verdant-button"].hidden is True
    game_env.load()
    assert game_env.elements["ship-1-depart-verdant-button"].hidden is False


def test_load_fills_cargo_with_colonys_produced_good(game_env):
    game_env.load()
    assert game_env.ship().cargo_good == "ore"
    assert game_env.ship().cargo_qty == game_env.module.CARGO_CAPACITY


def test_load_is_a_noop_without_a_docked_empty_ship(game_env):
    game_env.load()
    game_env.load()  # already loaded, second click should do nothing
    assert game_env.ship().cargo_qty == game_env.module.CARGO_CAPACITY


def test_depart_without_cargo_does_nothing(game_env):
    game_env.ship().depart("verdant")  # bypasses the hidden button directly
    assert game_env.ship().location == "aurum"
    assert not game_env.ship().in_transit


def test_depart_starts_transit_to_chosen_colony(game_env):
    game_env.load()
    game_env.depart("verdant")
    assert game_env.ship().in_transit
    assert game_env.ship().destination == "verdant"
    assert game_env.ship().transit_ticks_remaining == game_env.module.TRAVEL_TICKS


def test_depart_can_choose_any_other_colony(game_env):
    game_env.load()
    game_env.depart("ferrum")
    assert game_env.ship().destination == "ferrum"


def test_depart_to_own_colony_is_rejected(game_env):
    game_env.load()
    result = game_env.ship().depart("aurum")
    assert result is False
    assert not game_env.ship().in_transit


def test_ticking_before_transit_completes_keeps_ship_in_transit(game_env):
    game_env.load()
    game_env.depart("verdant")
    game_env.tick(game_env.module.TRAVEL_TICKS - 1)
    assert game_env.ship().in_transit
    assert game_env.total_profit == 0


def test_arrival_sells_cargo_and_docks_at_destination(game_env):
    game_env.load()
    game_env.depart("verdant")
    game_env.tick(game_env.module.TRAVEL_TICKS)

    assert not game_env.ship().in_transit
    assert game_env.ship().location == "verdant"
    assert not game_env.ship().loaded
    expected_profit = game_env.module.CARGO_CAPACITY * game_env.module.SELL_PRICE["ore"]
    assert game_env.total_profit == expected_profit


def test_full_round_trip_accumulates_profit_from_both_legs(game_env):
    game_env.load()
    game_env.depart("verdant")
    game_env.tick(game_env.module.TRAVEL_TICKS)

    game_env.load()  # now loads grain, since ship is docked at verdant
    assert game_env.ship().cargo_good == "grain"
    game_env.depart("aurum")
    game_env.tick(game_env.module.TRAVEL_TICKS)

    assert game_env.ship().location == "aurum"
    expected_profit = (
        game_env.module.CARGO_CAPACITY * game_env.module.SELL_PRICE["ore"]
        + game_env.module.CARGO_CAPACITY * game_env.module.SELL_PRICE["grain"]
    )
    assert game_env.total_profit == expected_profit


def test_sale_log_records_the_most_recent_sale(game_env):
    game_env.load()
    game_env.depart("verdant")
    game_env.tick(game_env.module.TRAVEL_TICKS)
    assert "Verdant Reach" in game_env.module.sale_log[-1]
    assert "Ore" in game_env.module.sale_log[-1]


def test_render_reflects_transit_status_text(game_env):
    game_env.load()
    game_env.depart("verdant")
    assert "In transit" in game_env.elements["ship-1-status"].innerText
    game_env.tick(game_env.module.TRAVEL_TICKS)
    assert "Docked at Verdant Reach" in game_env.elements["ship-1-status"].innerText


def test_profit_display_updates_on_render(game_env):
    game_env.load()
    game_env.depart("verdant")
    game_env.tick(game_env.module.TRAVEL_TICKS)
    assert str(game_env.total_profit) in game_env.elements["profit-display"].innerText
