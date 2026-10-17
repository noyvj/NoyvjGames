"""The community plot (shared growth pool) and its note."""

import json
import time

import canopy_runstate as runstate
from canopy_helpers import _el, _read_local_storage_item, _write_local_storage_item, ui_pref
from canopy_rules import ACCRUING_STATES, lab_active


# GB-19 (2026-10-09): the daily community forest. With "Water the community plot" ticked in Settings, a small share of every
# tick (standing plots as a fraction of the grid, times COMMUNITY_PER_TICK) is added to one anonymous shared pool, so
# preserving your forest waters everyone's plot. The pool line shows the world's total, today's total and the best day.
# Your own contribution today is also offered to the opt-in daily board (sign in and tick the board's box). Nothing is
# sent unless the setting is on, and a failed request never touches the game.
COMMUNITY_GAME, COMMUNITY_POOL, COMMUNITY_BOARD = "canopy", "community_plot", "community_investment"
COMMUNITY_PER_TICK = 0.1
COMMUNITY_REPORT_EVERY = 30  # ticks between board reports
COMMUNITY_STORAGE_KEY = "canopy_community_today_v1"
UI_PREF_COMMUNITY = "canopy-community-plot"


def _utc_day():
    return time.strftime("%Y-%m-%d", time.gmtime())


def community_enabled():
    return ui_pref(UI_PREF_COMMUNITY) == "true"


def community_share_this_tick():
    """How much this forest waters the plot this tick: more when more of it is standing."""
    if not runstate.plots:
        return 0.0
    return COMMUNITY_PER_TICK * sum(1 for p in runstate.plots if p.state in ACCRUING_STATES) / len(runstate.plots)


def community_today_total(day=None):
    """What this device has contributed so far on the UTC day (0 on a new day or with bad stored data)."""
    day = _utc_day() if day is None else day
    try:
        data = json.loads(_read_local_storage_item(COMMUNITY_STORAGE_KEY) or "{}")
    except (ValueError, TypeError):
        return 0.0
    if not isinstance(data, dict) or data.get("day") != day:
        return 0.0
    value = data.get("amount")
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value < 1e9 else 0.0


def _community_js():
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        return window
    except ImportError:
        return None


def _community_tick():
    if not community_enabled() or lab_active():  # a sandbox forest never waters the shared plot
        return 0.0
    amount = community_share_this_tick()
    if amount <= 0:
        return 0.0
    day = _utc_day()
    total = community_today_total(day) + amount
    _write_local_storage_item(COMMUNITY_STORAGE_KEY, json.dumps({"day": day, "amount": round(total, 3)}))
    window = _community_js()
    pool = getattr(window, "NoyvjPool", None) if window is not None else None
    if pool is not None:
        try:
            pool.add(COMMUNITY_GAME, COMMUNITY_POOL, amount)
        except Exception:  # noqa: BLE001 -- a shared counter must never break a tick
            pass
    runstate._community_ticks += 1
    if runstate._community_ticks % COMMUNITY_REPORT_EVERY == 0:
        board = getattr(window, "NoyvjLeaderboard", None) if window is not None else None
        if board is not None and total >= 0.1:
            try:
                board.report(COMMUNITY_GAME, COMMUNITY_BOARD, round(total, 2), "")
            except Exception:  # noqa: BLE001
                pass
    return amount


def render_community_note():
    note = _el("community-plot-note")
    if note is not None:
        note.innerText = (f"You have watered the community plot with {community_today_total():.1f} today (UTC day)."
                          if community_enabled() else
                          "Off. Tick \"Water the community plot\" in Settings to add a small share of your forest's growth to the shared daily total.")


def community_field_value(field):
    """The player's own number for one field of the community comparison. The page asks for it by name
    (pyodide.globals.get("community_field_value")) because these live variables are held in canopy_runstate."""
    return getattr(runstate, field)
