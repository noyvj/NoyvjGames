"""The practice sandbox's helpers (top-up, state swap, reset tables) that do not redraw the page."""

import copy

import trade_runstate as runstate
from trade_market import (
    good_profit_recent, good_profit_total, good_trip_count, market_crash_ever, market_multiplier,
    need_history, price_history,
)
from trade_research import RESEARCH_NODES
from trade_savestate import get_state


# --- Z-18: entering and leaving the practice sandbox ---------------------------------------------
# shared/sandbox-mode.js calls sandbox_enter() / sandbox_leave() / sandbox_is_active() through Pyodide and
# draws the "Sandbox: nothing here is saved" banner. The rules: a large credit balance that never runs out
# (no bankruptcy), every research node known (so every system and route is open), every ship bought, no
# route hazards, no corporation renewal, nothing earned. The real game is set aside as a get_state()
# snapshot and loaded back through the same load_state() a save uses; the sandbox is a fresh corporation
# loaded the same way, so it can never write into the real one.
SANDBOX_CREDITS = 1_000_000


def _sandbox_notify_page():
    """Tells shared/sandbox-mode.js to re-read sandbox_is_active() (the banner and button follow it)."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    shared = getattr(window, "NoyvjSandbox", None)
    if shared is not None:
        shared.sync()


def sandbox_is_active():
    return runstate.sandbox_active


def _sandbox_top_up():
    """The balance never drops below SANDBOX_CREDITS (called from every render, so also after each purchase)."""
    if runstate.sandbox_active and runstate.crisis_active is None and runstate.chain_active is None and runstate.total_profit < SANDBOX_CREDITS:  # a crisis has its own purse
        runstate.total_profit = SANDBOX_CREDITS
        runstate.max_profit_ever = max(runstate.max_profit_ever, runstate.total_profit)


def _reset_running_tables():
    """load_state() only updates these tables key by key, so a load would keep whatever the game running before
    it had put there; put them back to a brand-new game's values first."""
    fresh = runstate._fresh_state
    good_profit_recent.clear()
    need_history.clear()
    price_history.clear()
    price_history.update({good: list(values) for good, values in fresh["price_history"].items()})
    market_multiplier.update(fresh["market_multiplier"])
    good_profit_total.update(fresh["good_profit_total"])
    good_trip_count.update(fresh["good_trip_count"])
    market_crash_ever.update(fresh["market_crash_ever"])


def _sandbox_state():
    """The brand-new corporation the sandbox starts from, as a save dict."""
    data = copy.deepcopy(runstate._fresh_state)
    data["unlocked_research"] = sorted(RESEARCH_NODES)
    data["research_points"] = runstate._fresh_state["research_points"]
    data["total_profit"] = SANDBOX_CREDITS
    data["max_profit_ever"] = SANDBOX_CREDITS
    for ship in data["ships"].values():
        ship["purchased"] = True
    data["route_hazards"] = {"hazards": False, "insurance": False, "disruptions": 0, "payouts": 0, "premiums": 0}
    return data


def _sandbox_set_real_aside():
    """Takes the real corporation's snapshot (what get_state() answers while the sandbox, a crisis or a chain puzzle is on)."""
    snapshot = get_state()
    runstate._sandbox_real = {
        "snapshot": snapshot,
        "earned": list(snapshot["achievements_earned"]),
        "guild_cooldown": runstate.guild_cooldown,
        "seed": (runstate.run_seed, runstate.run_seed_pinned),  # the practice corporation rolls its own seed; the real one comes back after
    }
    runstate.sandbox_active = True
