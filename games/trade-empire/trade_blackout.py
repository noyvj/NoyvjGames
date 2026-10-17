"""Blackout mode: the dark price feed and star chart, buying intel, status and panel."""

import math

from js import document

import trade_runstate as runstate
from trade_records import RECORDS_COUNT_MAX, records
from trade_research import RESEARCH_NODES


# ---------------------------------------------------------------------------
# J-29 / J-30 -- Blackout: an opt-in hard mode. The map is dark, sparklines are
# hidden and prices show as ranges, until the player buys the information back:
# the "price feed" (exact prices and the sparklines) comes with Market Insight
# research or a one-time purchase, the "star chart" (the map and the ships on
# it) comes with Galaxy Expansion research or a one-time purchase. Nothing about
# the economy changes -- only what the player is told. Switching it on before the
# first sale of a charter and never switching it off makes a "dark run"; reaching
# the endgame on one earns the Dark Run achievement, a ledger stamp and a mark
# beside the title. Plain-language warning, always optional, refused in the sandbox.
# ---------------------------------------------------------------------------
BLACKOUT_FEED_COST = 250
BLACKOUT_CHART_COST = 200
BLACKOUT_PRICE_BAND = 0.15
BLACKOUT_INTEL = {
    "feed": {
        "label": "Price feed", "cost": BLACKOUT_FEED_COST, "research": "market_insight",
        "gives": "exact prices and the price and need sparklines",
    },
    "chart": {
        "label": "Star chart", "cost": BLACKOUT_CHART_COST, "research": "galaxy_expansion",
        "gives": "the trade-routes map and the ships on it",
    },
}
BLACKOUT_WARNING = (
    "Blackout is a harder way to play and entirely optional. The map goes dark, the sparklines are hidden and "
    "prices show only as ranges until you buy the information back (a price feed and a star chart, or the research "
    "that gives them). The economy itself does not change. Turn it on before your first sale and keep it on to the "
    "endgame for a Dark Run."
)

blackout_bought = set()


def blackout_has(kind):
    """True when the player can see what `kind` ('feed' or 'chart') shows -- always, outside Blackout."""
    if not runstate.blackout_enabled:
        return True
    return kind in blackout_bought or BLACKOUT_INTEL[kind]["research"] in runstate.unlocked_research


def blackout_price_range(price):
    """(low, high) credits shown instead of an exact price while the price feed is dark."""
    low = max(1, int(price * (1 - BLACKOUT_PRICE_BAND)))
    high = max(low + 1, int(math.ceil(price * (1 + BLACKOUT_PRICE_BAND))))
    return low, high


def blackout_bar_percent(pct):
    """A coarse (25% steps) bar width, so a dark price feed still hints at a crash without giving the number."""
    return min(100, int(round(pct / 25.0)) * 25)


def set_blackout(enabled):
    """Switch Blackout on or off. Returns True when it is now as asked."""
    if runstate.sandbox_active:
        return False
    enabled = bool(enabled)
    if enabled == runstate.blackout_enabled:
        return True
    runstate.blackout_enabled = enabled
    runstate.blackout_clean = enabled and runstate.total_sales_count == 0
    return True


def can_buy_blackout_intel(kind):
    if kind not in BLACKOUT_INTEL or not runstate.blackout_enabled or runstate.sandbox_active:
        return False
    return not blackout_has(kind) and runstate.total_profit >= BLACKOUT_INTEL[kind]["cost"]


def buy_blackout_intel(kind):
    if not can_buy_blackout_intel(kind):
        return False
    runstate.total_profit -= BLACKOUT_INTEL[kind]["cost"]
    blackout_bought.add(kind)
    return True


def blackout_note_endgame():
    """Called the tick the endgame is first reached: an unbroken Blackout makes it a dark run."""
    if runstate.blackout_enabled and runstate.blackout_clean and not runstate.sandbox_active and not runstate.blackout_done:
        runstate.blackout_done = True
        records["dark_runs"] = min(RECORDS_COUNT_MAX, records["dark_runs"] + 1)


def blackout_status_text():
    if not runstate.blackout_enabled:
        extra = f" You have finished {records['dark_runs']} dark run(s)." if records["dark_runs"] else ""
        return "Optional hard mode, off." + extra
    parts = []
    for kind, info in BLACKOUT_INTEL.items():
        if blackout_has(kind):
            parts.append(f"{info['label']}: bought" if kind in blackout_bought else f"{info['label']}: open (research)")
        else:
            parts.append(f"{info['label']}: dark ({info['cost']} credits, or research {RESEARCH_NODES[info['research']]['label']})")
    run = "Dark run in progress." if runstate.blackout_clean else "This is not a dark run (it was not on from the first sale)."
    if runstate.blackout_done:
        run = "Dark run done: stamped in the ledger."
    return run + " " + "; ".join(parts) + "."


def blackout_stamp_text():
    """The ledger stamp: a shape plus words (never colour only)."""
    return f"◐ Dark run stamp x{records['dark_runs']}" if records["dark_runs"] else ""


def render_blackout():
    button = document.getElementById("blackout-toggle-button")
    status = document.getElementById("blackout-status")
    if button is None or status is None:
        return
    button.innerText = f"Blackout: {'on' if runstate.blackout_enabled else 'off'}"
    button.setAttribute("aria-pressed", "true" if runstate.blackout_enabled else "false")
    button.disabled = runstate.sandbox_active
    status.innerText = blackout_status_text()
    for kind, info in BLACKOUT_INTEL.items():
        buy = document.getElementById(f"blackout-buy-{kind}-button")
        if buy is None:
            continue
        buy.hidden = not runstate.blackout_enabled or blackout_has(kind)
        buy.disabled = not can_buy_blackout_intel(kind)
        buy.innerText = f"Buy the {info['label'].lower()} ({info['cost']})"
        buy.title = f"One-time purchase for this charter: {info['gives']}."
    stamp = document.getElementById("ledger-dark-display")
    if stamp is not None:
        stamp.innerText = blackout_stamp_text() or "Dark runs: none yet (Blackout is optional)."
