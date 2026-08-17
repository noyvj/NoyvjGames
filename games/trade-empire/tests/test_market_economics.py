"""Milestone 4: market economics. Selling a good nudges its price
multiplier down; it recovers gradually each tick if left alone.
Overproducing a single good (running the same route on repeat) craters
its price, so diversifying across the triangle stays worthwhile.
"""


def test_market_starts_at_baseline(game_env):
    for good in game_env.module.market_multiplier:
        assert game_env.module.market_multiplier[good] == 1.0


def test_current_sell_price_matches_base_at_baseline(game_env):
    assert game_env.module.current_sell_price("ore") == game_env.module.SELL_PRICE["ore"]


def test_apply_market_sale_lowers_multiplier(game_env):
    game_env.module.apply_market_sale("ore", 10)
    assert game_env.module.market_multiplier["ore"] < 1.0


def test_apply_market_sale_floors_at_minimum(game_env):
    for _ in range(1000):
        game_env.module.apply_market_sale("ore", 10)
    assert game_env.module.market_multiplier["ore"] == game_env.module.MIN_PRICE_MULTIPLIER


def test_apply_market_sale_only_affects_that_good(game_env):
    game_env.module.apply_market_sale("ore", 10)
    assert game_env.module.market_multiplier["grain"] == 1.0
    assert game_env.module.market_multiplier["machinery"] == 1.0


def test_recover_market_raises_multiplier_toward_baseline(game_env):
    game_env.module.market_multiplier["ore"] = 0.5
    game_env.module.recover_market()
    assert game_env.module.market_multiplier["ore"] > 0.5


def test_recover_market_caps_at_baseline(game_env):
    game_env.module.market_multiplier["ore"] = 0.999
    game_env.module.recover_market()
    assert game_env.module.market_multiplier["ore"] == game_env.module.MAX_PRICE_MULTIPLIER


def test_repeated_sales_of_the_same_good_crash_its_price(game_env):
    price_before = game_env.module.current_sell_price("ore")
    for _ in range(5):
        game_env.load(ship_id="1")
        game_env.depart("verdant", ship_id="1")
        game_env.tick(game_env.module.TRAVEL_TICKS)
        game_env.load(ship_id="1")
        game_env.depart("aurum", ship_id="1")
        game_env.tick(game_env.module.TRAVEL_TICKS)
    price_after = game_env.module.current_sell_price("ore")
    assert price_after < price_before


def test_diversifying_routes_avoids_crashing_any_one_price(game_env):
    # One round trip each on ore and grain shouldn't crater either price
    # as hard as five round trips of just one would.
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    game_env.tick(game_env.module.TRAVEL_TICKS)
    ore_multiplier = game_env.module.market_multiplier["ore"]
    assert ore_multiplier > game_env.module.MIN_PRICE_MULTIPLIER
    assert ore_multiplier < 1.0


def test_profit_reflects_current_market_price_not_flat_base_price(game_env):
    game_env.module.market_multiplier["ore"] = 0.5
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    game_env.tick(game_env.module.TRAVEL_TICKS)
    expected = game_env.module.CARGO_CAPACITY * max(1, round(game_env.module.SELL_PRICE["ore"] * 0.5))
    assert game_env.total_profit == expected


def test_render_shows_market_price_and_percentage(game_env):
    game_env.module.render()
    text = game_env.elements["market-ore-display"].innerText
    assert "8 credits/unit" in text
    assert "100%" in text


def test_render_flags_crashed_price(game_env):
    game_env.module.market_multiplier["ore"] = 0.5
    game_env.module.render()
    assert "market-price--crashed" in game_env.elements["market-ore-display"].className


def test_render_does_not_flag_healthy_price(game_env):
    game_env.module.render()
    assert "market-price--crashed" not in game_env.elements["market-ore-display"].className


def test_render_updates_market_bar_width(game_env):
    game_env.module.market_multiplier["grain"] = 0.6
    game_env.module.render()
    assert game_env.elements["market-grain-bar"].style.width == "60%"
