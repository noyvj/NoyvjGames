"""J-27 / J-28 -- the commodities exchange: standing orders on the stockpiles that fill on their own, a five-row
order book, slots tied to trade posts, and the same limits as trading by hand."""

import json

import pytest


def _open(m):
    m.unlocked_research.update({"galaxy_expansion", "outer_reaches", "deep_survey", "umbral_reach"})
    for cid in list(m.EXPANSION_COLONIES) + list(m.RIFT_COLONIES) + list(m.DEEP_COLONIES):
        m.colony_states.setdefault(cid, m.ColonyState(cid))
    m.total_profit = m.max_profit_ever = 10_000
    return m


def test_locked_until_the_umbral_deep_is_reachable(game_env):
    m = game_env.module
    assert not m.exchange_open()
    assert m.add_exchange_order("buy", m.ORE, 60) is False
    game_env.elements["desk-toggle-button"].dispatch("click", None)
    assert "Locked" in game_env.elements["exchange-status"].innerText
    assert game_env.elements["exchange-controls"].hidden is True


def test_slots_are_one_plus_one_per_trade_post_up_to_five(game_env):
    m = _open(game_env.module)
    assert m.exchange_slots() == 1
    m.trade_posts[:] = ["Home system", "Kepler Cluster"]
    assert m.exchange_slots() == 3
    m.trade_posts[:] = list(m.TRADE_POST_SYSTEMS)
    assert m.exchange_slots() == 5


def test_adding_checks_everything(game_env):
    m = _open(game_env.module)
    m.trade_posts[:] = list(m.TRADE_POST_SYSTEMS)
    assert m.add_exchange_order("buy", m.ORE, 60) is True
    assert m.add_exchange_order("buy", m.ORE, 50) is False  # one order per side and good
    assert m.add_exchange_order("sell", m.ORE, 90) is True
    assert m.add_exchange_order("hold", m.GRAIN, 60) is False
    assert m.add_exchange_order("buy", "nope", 60) is False
    assert m.add_exchange_order("buy", m.GRAIN, 55) is False  # not an allowed step
    assert m.add_exchange_order("buy", m.GRAIN, True) is False
    assert m.add_exchange_order("buy", m.GRAIN, 60) is True
    assert m.add_exchange_order("buy", m.WATER, 60) is True
    assert m.add_exchange_order("buy", m.ENERGY, 60) is True
    assert m.add_exchange_order("buy", m.MACHINERY, 60) is False  # slots full (5)


def test_removing_an_order(game_env):
    m = _open(game_env.module)
    m.add_exchange_order("buy", m.ORE, 60)
    assert m.remove_exchange_order(3) is False and m.remove_exchange_order(True) is False
    assert m.remove_exchange_order(0) is True and m.exchange_orders == []


def test_a_buy_order_fills_when_the_price_is_low_enough(game_env):
    m = _open(game_env.module)
    m.add_exchange_order("buy", m.ORE, 60)
    m.market_multiplier[m.ORE] = 0.9
    m.exchange_tick()
    assert m.stockpile[m.ORE] == 0 and m.exchange_fills == []
    m.market_multiplier[m.ORE] = 0.5
    before = m.total_profit
    m.exchange_tick()
    assert m.stockpile[m.ORE] == m.STOCKPILE_LOT and m.total_profit < before
    assert m.exchange_fills[-1]["kind"] == "buy" and m.exchange_fills[-1]["qty"] == m.STOCKPILE_LOT
    assert m.records["exchange_fills"] == 1


def test_a_sell_order_sells_the_whole_stockpile_at_the_price_less_the_fee(game_env):
    m = _open(game_env.module)
    m.stockpile[m.ORE] = 10
    m.add_exchange_order("sell", m.ORE, 90)
    m.market_multiplier[m.ORE] = 0.6
    m.exchange_tick()
    assert m.stockpile[m.ORE] == 10
    m.market_multiplier[m.ORE] = 1.0
    expected = m.stockpile_sale_value(m.ORE)
    before = m.total_profit
    m.exchange_tick()
    assert m.stockpile[m.ORE] == 0 and m.total_profit == before + expected
    assert m.exchange_fills[-1]["kind"] == "sell" and m.exchange_fills[-1]["qty"] == 10


def test_same_limits_as_by_hand_capacity_and_credits(game_env):
    m = _open(game_env.module)
    m.add_exchange_order("buy", m.ORE, 100)
    m.stockpile[m.ORE] = m.STOCKPILE_CAPACITY
    m.exchange_tick()
    assert m.exchange_fills == []  # full
    m.stockpile[m.ORE] = 0
    m.total_profit = 0
    m.exchange_tick()
    assert m.exchange_fills == [] and m.stockpile[m.ORE] == 0  # cannot afford


def test_at_most_one_fill_per_order_per_tick(game_env):
    m = _open(game_env.module)
    m.add_exchange_order("buy", m.ORE, 100)
    m.exchange_tick()
    assert len(m.exchange_fills) == 1


def test_orders_run_from_the_normal_tick_and_fill_on_their_own(game_env):
    m = _open(game_env.module)
    m.add_exchange_order("buy", m.ORE, 100)
    game_env.tick(3)
    assert m.records["exchange_fills"] >= 1 and m.stockpile[m.ORE] > 0


def test_a_buy_then_sell_pair_cannot_print_money(game_env):
    m = _open(game_env.module)
    m.trade_posts[:] = ["Home system"]
    m.add_exchange_order("buy", m.ORE, 100)
    m.add_exchange_order("sell", m.ORE, 40)  # careless: sells right after buying
    start = m.total_profit
    game_env.tick(40)
    assert m.total_profit <= start + 40 * m.trade_post_income_per_tick() + 1  # only the fee losses show up


def test_no_exchange_activity_when_locked_even_with_orders_in_memory(game_env):
    m = game_env.module
    m.exchange_orders.append({"kind": "buy", "good": m.ORE, "pct": 100})
    game_env.tick(3)
    assert m.exchange_fills == []


def test_order_book_keeps_five_rows_newest_first(game_env):
    m = _open(game_env.module)
    for i in range(8):
        m._exchange_note_fill("buy", m.ORE, 5, 7 + i)
    assert len(m.exchange_fills) == 5
    html = m.exchange_book_html()
    assert html.index(">14<") < html.index(">10<") and ">9<" not in html
    assert "<th>Side</th>" in html and "Bought" in html


def test_empty_order_book_says_so(game_env):
    assert "No fills yet" in _open(game_env.module).exchange_book_html()


def test_fills_count_toward_achievements(game_env):
    m = _open(game_env.module)
    assert "first_fill" not in m.achievement_ids_earned()
    m._exchange_note_fill("buy", m.ORE, 5, 8)
    assert "first_fill" in m.achievement_ids_earned() and "market_maker" not in m.achievement_ids_earned()
    m.records["exchange_fills"] = m.EXCHANGE_MARKET_MAKER_FILLS
    assert "market_maker" in m.achievement_ids_earned()
    assert {a["id"]: a["progress"] for a in m.achievements_summary()}["market_maker"] == (25, 25)


# --------------------------------------------------------------------- UI

def test_the_desk_toggle_and_form_add_and_remove_an_order(game_env):
    m = _open(game_env.module)
    el = game_env.elements
    el["desk-toggle-button"].dispatch("click", None)
    assert el["desk-panel"].hidden is False and el["exchange-controls"].hidden is False
    el["exchange-kind-select"].value, el["exchange-good-select"].value, el["exchange-pct-select"].value = "buy", "grain", "70"
    el["exchange-add-button"].dispatch("click", None)
    assert m.exchange_orders == [{"kind": "buy", "good": "grain", "pct": 70}]
    assert el["exchange-order-0-row"].hidden is False and "Grain" in el["exchange-order-0-text"].innerText
    assert el["exchange-order-1-row"].hidden is True
    assert el["exchange-add-button"].disabled is True  # one slot, used
    el["exchange-order-0-remove-button"].dispatch("click", None)
    assert m.exchange_orders == [] and el["exchange-order-0-row"].hidden is True


def test_a_junk_form_value_adds_nothing(game_env):
    m = _open(game_env.module)
    el = game_env.elements
    el["exchange-kind-select"].value, el["exchange-good-select"].value, el["exchange-pct-select"].value = "buy", "ore", "abc"
    el["exchange-add-button"].dispatch("click", None)
    assert m.exchange_orders == []


# ------------------------------------------------------------------- saves

def test_nothing_saved_until_used(game_env):
    assert "exchange" not in game_env.module.get_state()


def test_orders_and_book_round_trip(game_env):
    m = _open(game_env.module)
    m.trade_posts[:] = ["Home system"]
    m.add_exchange_order("buy", m.ORE, 60)
    m.add_exchange_order("sell", m.GRAIN, 90)
    m._exchange_note_fill("buy", m.ORE, 5, 7)
    state = json.loads(json.dumps(m.get_state()))
    m.exchange_orders.clear()
    m.exchange_fills.clear()
    m.load_state(state)
    assert [o["kind"] for o in m.exchange_orders] == ["buy", "sell"] and len(m.exchange_fills) == 1


@pytest.mark.parametrize("raw", [
    "x", 3, [], {"orders": "x"}, {"orders": [3, None, "a"]},
    {"orders": [{"kind": "hold", "good": "ore", "pct": 60}]},
    {"orders": [{"kind": "buy", "good": "nope", "pct": 60}]},
    {"orders": [{"kind": "buy", "good": ["ore"], "pct": 60}]},
    {"orders": [{"kind": "buy", "good": "ore", "pct": 55}]},
    {"orders": [{"kind": "buy", "good": "ore", "pct": True}]},
    {"orders": [{"kind": "buy", "good": "ore", "pct": "60"}]},
    {"fills": [{"kind": "buy", "good": "ore", "qty": 0, "price": 3}]},
    {"fills": [{"kind": "buy", "good": "ore", "qty": 99, "price": 3}]},
    {"fills": [{"kind": "buy", "good": "ore", "qty": 5, "price": -1}]},
    {"fills": [{"kind": "buy", "good": "ore", "qty": 5.5, "price": 3}]},
    {"fills": "x"},
])
def test_tampered_exchange_values_are_dropped(game_env, raw):
    m = _open(game_env.module)
    state = json.loads(json.dumps(m.get_state()))
    state["exchange"] = raw
    assert m.load_state(state) is True
    assert m.exchange_orders == [] and m.exchange_fills == []


def test_more_orders_than_slots_are_trimmed_and_duplicates_dropped(game_env):
    m = _open(game_env.module)
    state = json.loads(json.dumps(m.get_state()))
    order = {"kind": "buy", "good": "ore", "pct": 60}
    state["exchange"] = {"orders": [order, order, {"kind": "sell", "good": "ore", "pct": 90},
                                    {"kind": "buy", "good": "grain", "pct": 60}]}
    m.load_state(state)
    assert len(m.exchange_orders) == 1  # one slot (no trade posts) and the duplicate is dropped


def test_a_save_that_cannot_reach_the_deep_drops_its_orders(game_env):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["exchange"] = {"orders": [{"kind": "buy", "good": "ore", "pct": 60}], "fills": []}
    m.load_state(state)
    assert m.exchange_orders == []


def test_a_renewal_clears_orders_but_keeps_the_fill_count(game_env):
    m = _open(game_env.module)
    m.add_exchange_order("buy", m.ORE, 60)
    m.records["exchange_fills"] = 9
    m.endgame_reached = True
    m.found_new_corporation()
    assert m.exchange_orders == [] and m.records["exchange_fills"] == 9


def test_sandbox_round_trip_restores_the_real_orders(game_env):
    m = _open(game_env.module)
    m.add_exchange_order("buy", m.ORE, 60)
    before = json.dumps(m.get_state(), sort_keys=True)
    m.sandbox_enter()
    assert m.exchange_orders == []
    m.sandbox_leave()
    assert json.dumps(m.get_state(), sort_keys=True) == before
