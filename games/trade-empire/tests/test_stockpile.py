"""J9 -- market speculation: a small per-good warehouse. Buy while a price
is crashed, sell after it recovers; buying and selling move the price, the
warehouse is small and selling pays a fee."""


def test_buying_a_lot_spends_credits_and_fills_the_stockpile(game_env):
    game = game_env.module
    game.total_profit = 1000
    price = game.current_sell_price(game.ORE)
    assert game.buy_stockpile(game.ORE)
    assert game.stockpile[game.ORE] == game.STOCKPILE_LOT
    assert game.total_profit == 1000 - game.STOCKPILE_LOT * price


def test_buying_pushes_the_price_up(game_env):
    game = game_env.module
    game.total_profit = 1000
    game.market_multiplier[game.ORE] = 0.5
    game.buy_stockpile(game.ORE)
    assert game.market_multiplier[game.ORE] > 0.5


def test_capacity_and_credits_limit_buying(game_env):
    game = game_env.module
    game.total_profit = 100_000
    for _ in range(10):
        game.buy_stockpile(game.ORE)
    assert game.stockpile[game.ORE] == game.STOCKPILE_CAPACITY
    assert game.can_stockpile_buy(game.ORE) is False
    game.stockpile[game.GRAIN] = 0
    game.total_profit = 0
    assert game.can_stockpile_buy(game.GRAIN) is False


def test_locked_system_goods_cannot_be_stockpiled(game_env):
    game = game_env.module
    game.total_profit = 100_000
    assert game.can_stockpile_buy(game.RARE_METALS) is False
    assert game.buy_stockpile(game.RARE_METALS) is False


def test_selling_pays_the_price_less_the_fee_and_pushes_the_price_down(game_env):
    game = game_env.module
    game.stockpile[game.ORE] = 10
    game.total_profit = 0
    game.market_multiplier[game.ORE] = 1.0
    expected = int(round(10 * game.current_sell_price(game.ORE) * (1 - game.STOCKPILE_SELL_FEE)))
    assert game.sell_stockpile(game.ORE)
    assert game.total_profit == expected
    assert game.stockpile[game.ORE] == 0
    assert game.market_multiplier[game.ORE] < 1.0
    assert game.sell_stockpile(game.ORE) is False  # nothing left


def test_stockpile_sales_do_not_count_as_trade_sales(game_env):
    game = game_env.module
    game.stockpile[game.ORE] = 10
    before = (game.total_sales_count, set(game.goods_sold_ever))
    game.sell_stockpile(game.ORE)
    assert (game.total_sales_count, set(game.goods_sold_ever)) == before


def test_buy_low_sell_after_recovery_can_profit_but_a_flat_market_loses_to_the_fee(game_env):
    game = game_env.module
    game.total_profit = 1000
    game.market_multiplier[game.ORE] = 0.3
    game.buy_stockpile(game.ORE)
    spent = 1000 - game.total_profit
    for _ in range(200):
        game.recover_market()
    game.total_profit = 0
    game.sell_stockpile(game.ORE)
    assert game.total_profit > spent  # crashed-then-recovered: a real profit
    # a flat market: buy and sell straight back at the same price loses money
    game.market_multiplier[game.ORE] = 1.0
    game.total_profit = 1000
    game.buy_stockpile(game.ORE)
    cost = 1000 - game.total_profit
    game.market_multiplier[game.ORE] = 1.0
    game.total_profit = 0
    game.sell_stockpile(game.ORE)
    assert game.total_profit < cost


def test_buttons_work_and_status_reads_the_stock(game_env):
    game = game_env.module
    game.total_profit = 1000
    game.render()
    buy = game_env.elements["stockpile-ore-buy-button"]
    assert buy.disabled is False
    buy.dispatch("click", None)
    assert game.stockpile[game.ORE] == game.STOCKPILE_LOT
    status = game_env.elements["stockpile-ore-status"].innerText
    assert f"Stockpile {game.STOCKPILE_LOT}/{game.STOCKPILE_CAPACITY}" in status and "sells for" in status
    game_env.elements["stockpile-ore-sell-button"].dispatch("click", None)
    assert game.stockpile[game.ORE] == 0


def test_state_round_trip_and_bad_saved_values(game_env):
    game = game_env.module
    game.stockpile[game.ORE] = 7
    saved = game.get_state()
    assert saved["stockpile"] == {game.ORE: 7}
    game.stockpile[game.ORE] = 0
    game.load_state(saved)
    assert game.stockpile[game.ORE] == 7
    for bad in ({game.ORE: -1}, {game.ORE: 10**9}, {game.ORE: True}, {game.ORE: "5"}, "junk", None, [1]):
        saved["stockpile"] = bad
        game.load_state(saved)
        assert all(units == 0 for units in game.stockpile.values())
    del saved["stockpile"]
    game.stockpile[game.ORE] = 3
    game.load_state(saved)
    assert game.stockpile[game.ORE] == 0
