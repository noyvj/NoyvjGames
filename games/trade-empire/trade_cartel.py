"""Cartel moves (squeeze and dump) and their backlash, the Market Desk panel that shows exchange, Meridian and Cartel together."""

from js import document

import trade_runstate as runstate
from trade_colony import active_colony_ids, colony_producing
from trade_effects import CARTEL_SLUMP, CARTEL_SPIKE, cartel_effects, cartel_multiplier
from trade_exchange import exchange_open, render_exchange
from trade_market import (
    MIN_PRICE_MULTIPLIER, current_sell_price, market_multiplier, price_memory, sell_stockpile, stockpile,
)
from trade_meridian import MERIDIAN_SHIELD_TICKS, render_meridian
from trade_records import RECORDS_COUNT_MAX, records
from trade_rules import GOOD_LABEL, SELL_PRICE


def on_toggle_desk(event=None):
    runstate.desk_open = not runstate.desk_open
    render_desk()


def render_desk():
    toggle = document.getElementById("desk-toggle-button")
    panel = document.getElementById("desk-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Market Desk" if runstate.desk_open else "\U0001F3DB\ufe0f Market Desk"
    toggle.setAttribute("aria-expanded", "true" if runstate.desk_open else "false")
    panel.hidden = not runstate.desk_open
    if not runstate.desk_open:
        return
    render_meridian()
    render_cartel()
    render_exchange()


# ---------------------------------------------------------------------------
# J-3 -- the Cartel Board (Market Desk window): deliberate market moves for the late game, open once the
# commodities exchange is (the Umbral Deep) or the endgame has been reached. A SQUEEZE buys up CARTEL_SQUEEZE_UNITS
# units' worth of a good (credits) and its price premium is +30% for 20 ticks. A DUMP sells your whole stockpile of
# a good at once: the price crashes (the ordinary sale impact) and, if Meridian is contesting that good, the dump
# ends it and shields the good. The backlash rule, shown plainly: moving the same good twice (squeeze or dump)
# within CARTEL_BACKLASH_WINDOW ticks backfires: a repeat squeeze turns into a -25% slump for 30 ticks (the credits
# are still spent) and a repeat dump shields nothing and knocks a further 10 points off the price. The J-4 ghost line
# remembers the price from before each move. Moves are counted (Cartel moves) toward an achievement.
# ---------------------------------------------------------------------------
CARTEL_SQUEEZE_UNITS = 8

CARTEL_SPIKE_TICKS = 20

CARTEL_SLUMP_TICKS = 30
CARTEL_BACKLASH_WINDOW = 80
CARTEL_DUMP_EXTRA_DROP = 0.10
CARTEL_ACHIEVEMENT_MOVES = 5

cartel_last = {}  # good -> ticks since the last cartel move on it (only while inside the window)


def cartel_open():
    return exchange_open() or runstate.endgame_reached


def cartel_backlash_left(good):
    """Ticks of backlash window left for `good` (0 = a move now is safe)."""
    if good not in cartel_last:
        return 0
    return max(0, CARTEL_BACKLASH_WINDOW - cartel_last[good])


def cartel_squeeze_cost(good):
    return CARTEL_SQUEEZE_UNITS * current_sell_price(good)


def _cartel_good_ok(good):
    return isinstance(good, str) and good in SELL_PRICE and colony_producing(good) in active_colony_ids()


def can_squeeze(good):
    return cartel_open() and _cartel_good_ok(good) and runstate.total_profit >= cartel_squeeze_cost(good)


def can_dump(good):
    return cartel_open() and _cartel_good_ok(good) and stockpile.get(good, 0) > 0


def _cartel_note_move(good):
    cartel_last[good] = 0
    if not runstate.sandbox_active:
        records["cartel_moves"] = min(RECORDS_COUNT_MAX, records["cartel_moves"] + 1)


def squeeze(good):
    """Returns 'spike' or 'backlash' (what the move turned into), or None when it could not be done."""
    if not can_squeeze(good):
        return None
    backfires = cartel_backlash_left(good) > 0
    runstate.total_profit -= cartel_squeeze_cost(good)
    price_memory[good] = market_multiplier[good]
    cartel_effects[good] = {"kind": "slump" if backfires else "spike", "left": CARTEL_SLUMP_TICKS if backfires else CARTEL_SPIKE_TICKS}
    _cartel_note_move(good)
    return "backlash" if backfires else "spike"


def dump(good):
    """Returns 'shielded', 'sold' (nothing to shield) or 'backlash', or None when it could not be done."""
    if not can_dump(good):
        return None
    backfires = cartel_backlash_left(good) > 0
    sell_stockpile(good)  # price_memory is set there
    if backfires:
        market_multiplier[good] = max(MIN_PRICE_MULTIPLIER, market_multiplier[good] - CARTEL_DUMP_EXTRA_DROP)
    _cartel_note_move(good)
    result = "backlash" if backfires else "sold"
    if not backfires and runstate.meridian_enabled and runstate.meridian_contest is not None and runstate.meridian_contest["good"] == good:
        runstate.meridian_contest = None
        runstate.meridian_shield = {"good": good, "left": MERIDIAN_SHIELD_TICKS}
        result = "shielded"
        if not runstate.sandbox_active:
            records["meridian_answers"] = min(RECORDS_COUNT_MAX, records["meridian_answers"] + 1)
    return result


def cartel_tick():
    for good in list(cartel_effects):
        cartel_effects[good]["left"] -= 1
        if cartel_effects[good]["left"] <= 0:
            del cartel_effects[good]
    for good in list(cartel_last):
        cartel_last[good] += 1
        if cartel_last[good] >= CARTEL_BACKLASH_WINDOW:
            del cartel_last[good]


def cartel_row_text(good):
    parts = [f"{GOOD_LABEL[good]}: {current_sell_price(good)} credits/unit"]
    effect = cartel_effects.get(good)
    if effect is not None:
        word = "squeeze premium" if effect["kind"] == "spike" else "BACKLASH slump"
        parts.append(f"{word} {(cartel_multiplier(good) - 1) * 100:+.0f}% for {effect['left']} more tick(s)")
    left = cartel_backlash_left(good)
    parts.append(f"backlash window: {left} tick(s), a move now backfires" if left else "no backlash window, safe to move")
    return "; ".join(parts) + "."


def cartel_status_text():
    if not cartel_open():
        return "Locked: the Cartel Board opens with the commodities exchange (the Umbral Deep) or after the endgame."
    return (
        f"Cartel moves made: {records['cartel_moves']}. A squeeze costs {CARTEL_SQUEEZE_UNITS} units' worth and gives "
        f"{CARTEL_SPIKE * 100:+.0f}% for {CARTEL_SPIKE_TICKS} ticks. A dump sells your whole stockpile of the good. "
        f"Moving the same good twice within {CARTEL_BACKLASH_WINDOW} ticks backfires: a squeeze becomes a "
        f"{CARTEL_SLUMP * 100:+.0f}% slump for {CARTEL_SLUMP_TICKS} ticks and a dump knocks the price down a further "
        f"{CARTEL_DUMP_EXTRA_DROP * 100:.0f} points."
    )


def render_cartel():
    status = document.getElementById("cartel-status")
    if status is None:
        return
    status.innerText = cartel_status_text()
    controls = document.getElementById("cartel-controls")
    if controls is not None:
        controls.hidden = not cartel_open()
    for good in SELL_PRICE:
        row = document.getElementById(f"cartel-{good}-row")
        if row is None:
            continue
        shown = cartel_open() and _cartel_good_ok(good)
        row.hidden = not shown
        if not shown:
            continue
        document.getElementById(f"cartel-{good}-text").innerText = cartel_row_text(good)
        document.getElementById(f"cartel-{good}-squeeze-button").disabled = not can_squeeze(good)
        dump_button = document.getElementById(f"cartel-{good}-dump-button")
        dump_button.disabled = not can_dump(good)
        dump_button.innerText = f"Dump {stockpile.get(good, 0)}"
        document.getElementById(f"cartel-{good}-squeeze-button").innerText = f"Squeeze ({cartel_squeeze_cost(good)})"
