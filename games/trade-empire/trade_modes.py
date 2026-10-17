"""The Modes screen (GN-17): the ladder of game modes and its render."""

from js import document, setTimeout
from pyodide.ffi import create_proxy

import trade_runstate as runstate
from trade_achievements import achievement_ids_earned
from trade_blackout import blackout_bought
from trade_chain_ui import _chain_to_js
from trade_records import _fresh_records, records


# ---------------------------------------------------------------------------
# GN-17 -- the Modes screen, the pilot for "modes as levels" (see CLAUDE.md, "Modes as levels"). The game modes are
# an ordered ladder on the shared level select (shared/level-select.js): the core game first, then the modes from
# gentlest to hardest, each with a one-line description of what it adds. EVERY rung is open from the start (there
# is no gating and no locked card); the order is only a suggested path, and the first rung you have not tried yet
# carries a "Next suggested mode" marker. A rung counts as tried from what the real game already records, so
# nothing new is saved. Reachable from the toolbar (Classic) and the Menu (Desktop).
# ---------------------------------------------------------------------------
MODES = (
    {"id": "core", "title": "The core game", "kind": "level",
     "blurb": "Load a ship, pick a destination, sell, research and automate: the few controls everything else is built on."},
    {"id": "expeditions", "title": "Expeditions", "kind": "mode",
     "blurb": "Adds: send one idle ship far off the routes for a reward or a collectable curio. It costs only that ship's income."},
    {"id": "chain", "title": "Chain Builder", "kind": "mode",
     "blurb": "Adds: 24 short puzzles where you plan multi-step production chains and spend as few ships as you can."},
    {"id": "crises", "title": "Trade Crises", "kind": "mode",
     "blurb": "Adds: three handcrafted emergencies, each with a goal and gold, silver and bronze par times."},
    {"id": "blackout", "title": "Blackout", "kind": "mode",
     "blurb": "Adds: an optional hard mode where the map and charts go dark and prices show as ranges until you buy the information back."},
    {"id": "sandbox", "title": "Practice sandbox", "kind": "mode",
     "blurb": "Adds: a throwaway corporation with every system open and unlimited credits, for trying anything. Nothing in it is saved."},
)
MODE_IDS = tuple(m["id"] for m in MODES)
MODES_OPEN_DELAY_MS = 80


def _modes_real_view():
    """(records, blackout used, achievements earned) of the real game, even while a puzzle or the sandbox is on."""
    if runstate.sandbox_active:
        snapshot = runstate._sandbox_real["snapshot"]
        saved = _fresh_records()
        saved.update(snapshot.get("records") or {})
        return saved, "blackout" in snapshot, set(runstate._sandbox_real["earned"])
    return records, bool(runstate.blackout_enabled or runstate.blackout_done or blackout_bought), set(achievement_ids_earned())


def modes_done_ids():
    """The rungs already tried, read from what the real game records (the sandbox is never marked: it is free play)."""
    saved, blackout_used, earned = _modes_real_view()
    done = []
    if "first_automation" in earned:
        done.append("core")
    if saved["expeditions"] >= 1:
        done.append("expeditions")
    if saved["chain_best"]:
        done.append("chain")
    if saved["crisis_best"]:
        done.append("crises")
    if blackout_used or saved["dark_runs"]:
        done.append("blackout")
    return done


def modes_next_suggested():
    """The first rung of the ladder not tried yet (the last rung when everything else has been)."""
    done = modes_done_ids()
    return next((m["id"] for m in MODES if m["id"] not in done), MODES[-1]["id"])


def modes_levels_list():
    suggested = modes_next_suggested()
    return [
        dict(m, blurb=("Next suggested mode. " if m["id"] == suggested else "") + m["blurb"])
        for m in MODES
    ]


def modes_title(mode_id):
    return next((m["title"] for m in MODES if m["id"] == mode_id), mode_id)


def _modes_sync_screen():
    if runstate._modes_screen is None:
        return
    levels = _chain_to_js(modes_levels_list())
    state = _chain_to_js({"done": modes_done_ids(), "best": {}})
    try:
        if levels is not None:
            runstate._modes_screen.setLevels(levels)
        if state is not None:
            runstate._modes_screen.setState(state)
    except Exception:  # noqa: BLE001 -- a JS-side failure must never break the game
        pass


def _call_after_menu_closes(callback):
    """The Desktop Menu closes itself, and hands focus back to its button, right after one of its entries is clicked;
    opening a dialog a moment later keeps the dialog's own focus (and its focus return to the Menu button on close)."""
    holder = []

    def run():
        try:
            callback()
        finally:
            for proxy in holder:
                proxy.destroy()

    proxy = create_proxy(run)
    holder.append(proxy)
    setTimeout(proxy, MODES_OPEN_DELAY_MS)


def render_modes():
    """Keeps the toolbar button's tooltip (and the screen, once built) pointing at the next suggested mode."""
    button = document.getElementById("modes-open-button")
    if button is None:
        return
    signature = (tuple(modes_done_ids()), modes_next_suggested())
    if signature == runstate._modes_rendered_sig:
        return
    runstate._modes_rendered_sig = signature
    button.title = f"The game modes, from gentlest to hardest. Every one is open. Next suggested mode: {modes_title(signature[1])}."
    _modes_sync_screen()
