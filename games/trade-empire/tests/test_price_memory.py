"""J-4 -- the price-memory ghost line on each price sparkline: where the price
was before the player's last stockpile buy or sell, dashed and named in text."""

import pytest


def _seed_history(game, good, n=6):
    game.price_history[good] = [game.market_multiplier[good]] * n


def test_no_memory_until_the_player_trades_the_stockpile(game_env):
    m = game_env.module
    assert m.price_memory == {} and m.price_memory_text(m.ORE) == ""
    assert "price_memory" not in m.get_state()


def test_buying_remembers_the_price_before_the_buy(game_env):
    m = game_env.module
    m.total_profit = 1000
    m.market_multiplier[m.ORE] = 0.6
    assert m.buy_stockpile(m.ORE)
    assert m.price_memory[m.ORE] == pytest.approx(0.6)
    assert m.market_multiplier[m.ORE] > 0.6


def test_selling_remembers_the_price_before_the_sell(game_env):
    m = game_env.module
    m.stockpile[m.GRAIN] = 10
    m.market_multiplier[m.GRAIN] = 0.9
    assert m.sell_stockpile(m.GRAIN)
    assert m.price_memory[m.GRAIN] == pytest.approx(0.9)
    assert m.market_multiplier[m.GRAIN] < 0.9


def test_ship_sales_and_failed_trades_do_not_set_it(game_env):
    m = game_env.module
    m.total_profit = 0
    assert m.buy_stockpile(m.ORE) is False
    assert m.sell_stockpile(m.ORE) is False
    game_env.load()
    game_env.depart("ferrum")
    game_env.tick(m.TRAVEL_TICKS)
    assert m.price_memory == {}


def test_the_last_trade_overwrites_the_memory(game_env):
    m = game_env.module
    m.total_profit = 10_000
    m.market_multiplier[m.ORE] = 0.5
    m.buy_stockpile(m.ORE)
    m.market_multiplier[m.ORE] = 0.8
    m.buy_stockpile(m.ORE)
    assert m.price_memory[m.ORE] == pytest.approx(0.8)


def test_the_sparkline_draws_a_dashed_ghost_line_at_the_remembered_level(game_env):
    m = game_env.module
    m.total_profit = 1000
    m.market_multiplier[m.ORE] = 0.5
    m.buy_stockpile(m.ORE)
    _seed_history(m, m.ORE)
    m.render()
    html = game_env.elements["market-ore-sparkline"].innerHTML
    assert 'class="sparkline-ghost"' in html and 'stroke-dasharray="3 2"' in html
    expected_y = m.SPARKLINE_HEIGHT - 0.5 * m.SPARKLINE_HEIGHT
    assert f'y1="{expected_y:.1f}"' in html


def test_the_ghost_line_is_never_colour_only(game_env):
    m = game_env.module
    m.total_profit = 1000
    m.market_multiplier[m.ORE] = 0.5
    m.buy_stockpile(m.ORE)
    _seed_history(m, m.ORE)
    m.render()
    html = game_env.elements["market-ore-sparkline"].innerHTML
    assert "dashed line: 50% of baseline before your last stockpile trade" in html
    assert "<title>dashed line" in html  # also the hover text


def test_goods_without_a_memory_get_a_plain_sparkline(game_env):
    m = game_env.module
    _seed_history(m, m.WATER)
    m.render()
    assert "sparkline-ghost" not in game_env.elements["market-water-sparkline"].innerHTML


def test_the_svg_helper_ignores_a_ghost_when_there_is_too_little_history(game_env):
    m = game_env.module
    assert m._trend_sparkline_svg([0.5], "price-sparkline", ghost=0.4) == ""
    assert "sparkline-ghost" in m._trend_sparkline_svg([0.5, 0.6], "price-sparkline", ghost=0.4)


def test_memory_round_trips_and_survives_tampering(game_env):
    m = game_env.module
    m.total_profit = 1000
    m.market_multiplier[m.ORE] = 0.7
    m.buy_stockpile(m.ORE)
    saved = m.get_state()
    assert saved["price_memory"] == {m.ORE: pytest.approx(0.7)}
    m.price_memory.clear()
    m.load_state(saved)
    assert m.price_memory[m.ORE] == pytest.approx(0.7)
    for bad in ({m.ORE: True}, {m.ORE: 9}, {m.ORE: "x"}, {"bogus": 0.5}, {m.ORE: float("nan")}, [1], "x", None):
        saved["price_memory"] = bad
        m.load_state(saved)
        assert m.price_memory == {}, bad
