"""H-26: per-node spending sparklines (hover a ring node)."""

from pathlib import Path
from .pagefiles import game_css, page_text

HERE = Path(__file__).resolve().parent.parent
INDEX = page_text()
CSS = game_css()


def test_purchases_are_filed_per_cycle(game_env):
    chain = game_env.chain
    chain.funds = 1000.0
    game_env.invest_circularity("repair")
    game_env.invest_circularity("repair")
    game_env.invest_circularity("recycle")
    assert chain.buys_now == [2, 0, 1, 0, 0, 0]
    game_env.advance_cycle()
    assert chain.buy_log == [[2, 0, 1, 0, 0, 0]] and chain.buys_now == [0] * 6
    game_env.invest_trade_link()
    game_env.invest_regional_trade()
    game_env.invest_overseas_trade()
    game_env.advance_cycle()
    assert chain.buy_log[1] == [0, 0, 0, 1, 1, 1]


def test_a_refused_purchase_is_not_counted(game_env):
    chain = game_env.chain
    chain.funds = 5.0
    assert chain.invest_circularity("repair") is False
    assert chain.buys_now == [0] * 6


def test_buying_several_at_once_counts_each(game_env):
    chain = game_env.chain
    chain.funds = 500.0
    chain.invest_many("reuse", 4)
    assert chain.buys_now[1] == 4


def test_the_series_is_spending_with_the_current_cycle_last(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 1000.0
    game_env.invest_circularity("repair")
    game_env.advance_cycle()
    game_env.invest_circularity("repair")
    game_env.invest_circularity("repair")
    cost = module.CIRCULARITY_INVESTMENTS["repair"]["cost"]
    assert module.node_spend_series("repair") == [cost, 2 * cost]
    assert module.node_spend_series("reuse") == [0, 0]


def test_the_series_is_capped_at_twelve_points(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 100_000.0
    for _ in range(20):
        game_env.advance_cycle()
    assert len(module.node_spend_series("repair")) == module.SPARK_CYCLES


def test_the_sparkline_svg_is_a_closed_chart_even_when_flat(game_env):
    module = game_env.module
    flat = module.sparkline_svg([0, 0, 0])
    assert flat.startswith("<svg") and flat.endswith("</svg>") and "polyline" in flat
    one = module.sparkline_svg([5])
    assert "polyline" in one and "circle" in one
    rising = module.sparkline_svg([0, 10, 20])
    assert rising.count(",") >= 3


def test_each_node_gets_its_tooltip_content_with_real_numbers(game_env):
    chain = game_env.chain
    chain.funds = 1000.0
    game_env.invest_circularity("recycle")
    html = game_env.elements["spark-recycle"].innerHTML
    assert "Recycling Loops" in html and "30 funds this cycle" in html and "<svg" in html
    assert "0 funds this cycle" in game_env.elements["spark-repair"].innerHTML


def test_the_list_view_carries_the_same_numbers_as_text(game_env):
    chain = game_env.chain
    chain.funds = 1000.0
    game_env.invest_circularity("repair")
    html = game_env.elements["a11y-chain-list"].innerHTML
    assert "Repair Networks spending per cycle, latest last: 20." in html


def test_the_purchase_log_is_saved_and_loaded(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 1000.0
    game_env.invest_circularity("repair")
    game_env.advance_cycle()
    game_env.invest_circularity("reuse")
    state = module.get_state()
    assert state["buy_log"] == [[1, 0, 0, 0, 0, 0]] and state["buys_now"] == [0, 1, 0, 0, 0, 0]
    module.load_state(state)
    assert chain is not None and module.chain.buy_log == [[1, 0, 0, 0, 0, 0]]
    assert module.chain.buys_now == [0, 1, 0, 0, 0, 0]


def test_a_fresh_chain_writes_no_purchase_keys(game_env):
    state = game_env.module.get_state()
    assert "buy_log" not in state and "buys_now" not in state


def test_an_old_save_without_the_log_loads_with_an_empty_one(game_env):
    module = game_env.module
    state = module.get_state()
    for key in ("buy_log", "buys_now"):
        state.pop(key, None)
    module.load_state(state)
    assert module.chain.buy_log == [] and module.chain.buys_now == [0] * 6
    assert module.load_report == []


def test_a_bad_log_is_dropped_whole_and_reported(game_env):
    module = game_env.module
    state = module.get_state()
    state["buy_log"] = [[1, 0, 0, 0, 0, 0], [1, 2, "x", 0, 0, 0]]
    state["buys_now"] = [1, 2, 3]
    module.load_state(state)
    assert module.chain.buy_log == [] and module.chain.buys_now == [0] * 6
    names = [name for name, _kind in module.load_report]
    assert "Purchases per cycle" in names and "Purchases this cycle" in names


def test_rewind_takes_the_purchase_log_back_too(game_env):
    chain = game_env.chain
    chain.funds = 1000.0
    game_env.invest_circularity("repair")
    game_env.advance_cycle()
    game_env.invest_circularity("repair")
    assert chain.rewind()
    assert chain.buy_log == [] and chain.buys_now == [1, 0, 0, 0, 0, 0]


def test_a_new_chain_starts_with_an_empty_log(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 1000.0
    game_env.invest_circularity("repair")
    game_env.advance_cycle()
    game_env.reset_chain()
    assert module.chain.buy_log == [] and module.chain.buys_now == [0] * 6


def test_the_page_has_the_tooltip_holders_and_css():
    for measure in ("repair", "reuse", "recycle"):
        assert f'id="spark-{measure}" class="loop-ring-spark"' in INDEX
    assert ".loop-ring-node:hover .loop-ring-spark" in CSS
