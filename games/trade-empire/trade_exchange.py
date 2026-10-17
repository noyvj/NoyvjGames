"""The Market Desk's exchange: standing buy and sell orders, fills, the order book and panel."""

from js import document

import trade_runstate as runstate
from trade_colony import active_colony_ids, colony_producing, umbral_reach_unlocked
from trade_market import (
    buy_stockpile, can_stockpile_buy, current_sell_price, market_multiplier, sell_stockpile, stockpile,
    stockpile_sale_value,
)
from trade_records import RECORDS_COUNT_MAX, records
from trade_rules import GOOD_LABEL, SELL_PRICE
from trade_ships import trade_posts


# ---------------------------------------------------------------------------
# J-27 / J-28 -- the Second Economy: an interstellar commodities exchange, open once the Umbral Deep
# is reachable. It ties trade posts, speculation and automation together: you set standing buy and
# sell orders on the stockpiles (J9) and they fill on their own each tick, using exactly the same
# rules, limits, fee and price impact as buying or selling by hand (so it is no money loop). A buy
# order buys a lot when the price falls to its percentage of baseline or below, a sell order sells
# the whole stockpile when the price rises to its percentage or above. Slots: one, plus one per
# trade post (up to five). The mini order book lists the last five fills in words, and every fill
# counts in Exchange fills (a visible stat that feeds two achievements).
# ---------------------------------------------------------------------------
EXCHANGE_MAX_SLOTS = 5
EXCHANGE_BOOK_ROWS = 5
EXCHANGE_PERCENTS = (40, 50, 60, 70, 80, 90, 100)
EXCHANGE_MARKET_MAKER_FILLS = 25
exchange_orders = []  # [{"kind": "buy" | "sell", "good": id, "pct": int}]
exchange_fills = []  # newest last: [{"kind", "good", "qty", "price"}] (price = credits per unit paid or received)


def exchange_open():
    return umbral_reach_unlocked()


def exchange_slots():
    return min(EXCHANGE_MAX_SLOTS, 1 + len(trade_posts))


def can_add_exchange_order(kind, good, pct):
    return (
        exchange_open() and kind in ("buy", "sell") and good in SELL_PRICE and pct in EXCHANGE_PERCENTS
        and colony_producing(good) in active_colony_ids() and len(exchange_orders) < exchange_slots()
        and not any(o["kind"] == kind and o["good"] == good for o in exchange_orders)
    )


def add_exchange_order(kind, good, pct):
    if not can_add_exchange_order(kind, good, pct):
        return False
    exchange_orders.append({"kind": kind, "good": good, "pct": pct})
    return True


def remove_exchange_order(index):
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(exchange_orders):
        return False
    del exchange_orders[index]
    return True


def _exchange_note_fill(kind, good, qty, unit_price):
    exchange_fills.append({"kind": kind, "good": good, "qty": qty, "price": unit_price})
    del exchange_fills[:-EXCHANGE_BOOK_ROWS]
    if not runstate.sandbox_active:
        records["exchange_fills"] = min(RECORDS_COUNT_MAX, records["exchange_fills"] + 1)


def exchange_tick():
    """Fills what the standing orders ask for this tick: at most one fill per order."""
    if not exchange_open():
        return
    for order in exchange_orders:
        good = order["good"]
        pct = market_multiplier[good] * 100
        if order["kind"] == "buy":
            if pct <= order["pct"] and can_stockpile_buy(good):
                before, price = stockpile[good], current_sell_price(good)
                if buy_stockpile(good):
                    _exchange_note_fill("buy", good, stockpile[good] - before, price)
        elif stockpile.get(good, 0) > 0 and pct >= order["pct"]:
            qty, value = stockpile[good], stockpile_sale_value(good)
            if sell_stockpile(good):
                _exchange_note_fill("sell", good, qty, int(round(value / qty)))


def exchange_order_text(order):
    verb = "Buy a lot when" if order["kind"] == "buy" else "Sell the stockpile when"
    side = "falls to" if order["kind"] == "buy" else "rises to"
    return f"{verb} {GOOD_LABEL[order['good']]} {side} {order['pct']}% of baseline"


def exchange_book_html():
    if not exchange_fills:
        return "<p class=\"map-caption\">No fills yet.</p>"
    rows = ["<table class=\"exchange-book-table\"><thead><tr><th>Side</th><th>Good</th><th>Units</th><th>Credits each</th></tr></thead><tbody>"]
    for fill in reversed(exchange_fills):
        side = "Bought" if fill["kind"] == "buy" else "Sold"
        rows.append(
            f"<tr><td>{side}</td><td>{GOOD_LABEL[fill['good']]}</td><td>{fill['qty']}</td><td>{fill['price']}</td></tr>"
        )
    rows.append("</tbody></table>")
    return "".join(rows)


def exchange_status_text():
    if not exchange_open():
        return "Locked: the exchange opens once the Umbral Deep is reachable (research Umbral Reach)."
    return (
        f"Standing orders: {len(exchange_orders)}/{exchange_slots()} slots (one slot, plus one per trade post). "
        f"Exchange fills: {records['exchange_fills']}. Orders trade your stockpiles by the same rules and fee as "
        "doing it by hand, so a careless pair of orders can lose credits."
    )


def render_exchange():
    status = document.getElementById("exchange-status")
    if status is None:
        return
    status.innerText = exchange_status_text()
    controls = document.getElementById("exchange-controls")
    if controls is not None:
        controls.hidden = not exchange_open()
    add = document.getElementById("exchange-add-button")
    if add is not None:
        add.disabled = not (exchange_open() and len(exchange_orders) < exchange_slots())
    for i in range(EXCHANGE_MAX_SLOTS):
        row = document.getElementById(f"exchange-order-{i}-row")
        text = document.getElementById(f"exchange-order-{i}-text")
        if row is None or text is None:
            continue
        shown = exchange_open() and i < len(exchange_orders)
        row.hidden = not shown
        if shown:
            text.innerText = exchange_order_text(exchange_orders[i])
    book = document.getElementById("exchange-book")
    if book is not None:
        book.innerHTML = exchange_book_html() if exchange_open() else ""
