"""J27 — the trade almanac reference."""


def test_home_system_goods_only_at_start(game_env):
    game = game_env.module
    goods = [row["good"] for row in game.almanac_rows()]
    assert goods == ["Ore", "Grain", "Machinery", "Water", "Energy"]


def test_rows_report_price_range_and_producer_and_consumer(game_env):
    game = game_env.module
    ore = next(r for r in game.almanac_rows() if r["good"] == "Ore")
    assert ore["base"] == game.SELL_PRICE[game.ORE]
    assert ore["low"] == round(ore["base"] * game.MIN_PRICE_MULTIPLIER, 1)
    assert ore["high"] == round(ore["base"] * game.MAX_PRICE_MULTIPLIER, 1)
    assert ore["made_by"] == "Aurum Station"
    assert ore["needed_by"] == "Ferrum Forge"


def test_expansion_goods_appear_only_after_galaxy_expansion(game_env):
    game = game_env.module
    assert "Rare Metals" not in [r["good"] for r in game.almanac_rows()]
    game.unlocked_research.add("galaxy_expansion")
    rows = game.almanac_rows()
    assert "Rare Metals" in [r["good"] for r in rows]
    assert next(r for r in rows if r["good"] == "Rare Metals")["system"] == "Kepler Cluster"
    assert "Crystal" not in [r["good"] for r in rows]


def test_render_puts_a_table_in_the_almanac_body(game_env):
    game = game_env.module
    game.render_market()
    html = game_env.elements["almanac-body"].innerHTML
    assert "<table" in html and "Aurum Station" in html
