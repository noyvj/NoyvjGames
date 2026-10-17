"""Balance and domino readouts, the rescue burst, the season report card, rewind and the speedrun record."""

import html
import json
import time

import js as _js
from js import document, setTimeout
from pyodide.ffi import create_proxy

import tide_runstate as runstate
from tide_bridge import _read_local_storage_item, _write_local_storage_item
from tide_chrome import announce
from tide_coasts import heritage_sites
from tide_rules import (
    BALANCE_MULTIPLIERS, CATEGORIES, DOMINO_DISCOUNT, IDLE_CAP_SECONDS, INVEST_LABELS, IRONMAN_SEASONS,
    SPEEDRUN_KEY,
)


# GD-14 balanced seasons, GD-28 domino comeback, GD-27 rescue burst, GD-30 season report card -----------------------

def balance_text():
    streak = runstate.state.balance_streak
    invested = runstate.state.season_invested
    missing = [INVEST_LABELS[c] for c in CATEGORIES if c not in invested]
    next_mult = runstate.state.balance_multiplier()
    if not missing:
        return f"Balanced: all three invested this season, so the next advance pays x{next_mult:.1f} income (streak {streak})."
    if streak:
        return f"Balanced streak {streak} (x{BALANCE_MULTIPLIERS[min(streak, 3)]:.1f}). Invest in {', '.join(missing)} this season to keep it."
    if invested:
        return f"Add {', '.join(missing)} this season for a balanced income bonus (x{BALANCE_MULTIPLIERS[1]:.1f}, rising to x{BALANCE_MULTIPLIERS[-1]:.1f})."
    return f"Invest in all three categories in one season for a balanced income bonus (x{BALANCE_MULTIPLIERS[1]:.1f}, rising to x{BALANCE_MULTIPLIERS[-1]:.1f})."


def domino_text():
    if runstate.state.domino_seasons_left > 0:
        return (f"Domino comeback: adaptation costs {round(DOMINO_DISCOUNT * 100)}% less for {runstate.state.domino_seasons_left} more "
                f"season{'s' if runstate.state.domino_seasons_left != 1 else ''}.")
    return ""


def _reduced_motion():
    root = getattr(document, "documentElement", None)
    if root is not None and hasattr(root, "getAttribute") and root.getAttribute("data-reduced-motion") == "true":
        return True
    try:
        return bool(_js.window.matchMedia("(prefers-reduced-motion: reduce)").matches)
    except Exception:  # noqa: BLE001 -- outside a browser there is no media query
        return False


def _hide_later(element_id, delay_ms):
    holder = []

    def hide():
        el = document.getElementById(element_id)
        if el is not None:
            el.hidden = True
        if holder:
            holder[0].destroy()

    holder.append(create_proxy(hide))
    setTimeout(holder[0], delay_ms)


def render_rescue_burst():
    """GD-27: the lifeboat burst, shown once for a last-second heritage rescue."""
    el = document.getElementById("rescue-burst")
    if el is None or runstate.state.last_rescue is None:
        return
    site = next((x for x in heritage_sites() if x["id"] == runstate.state.last_rescue), None)
    runstate.state.last_rescue = None
    if site is None:
        return
    el.innerText = f"\U0001F6DF SAVED! {site['emoji']} {site['name']}"
    el.hidden = False
    announce(f"Saved at the last second: {site['name']}.")
    _hide_later("rescue-burst", 3500)


def season_report_chips(before, after):
    """Three chips (funds, acidity, fish yield) as (text, good) with a shape arrow, so good and bad never rely on colour."""
    def chip(label, delta, higher_is_good, fmt):
        if abs(delta) < 1e-9:
            return (f"\u25ac {label} unchanged", True)
        arrow = "\u25b2" if delta > 0 else "\u25bc"
        good = (delta > 0) == higher_is_good
        return (f"{arrow} {label} {fmt(delta)} ({'good' if good else 'watch'})", good)
    return [
        chip("Funds", after["funds"] - before["funds"], True, lambda d: f"{d:+.0f}"),
        chip("Acidity", after["acidity"] - before["acidity"], False, lambda d: f"{d:+.1f}"),
        chip("Fish", (after["fish"] - before["fish"]) * 100, True, lambda d: f"{d:+.0f}%"),
    ]


def _season_numbers():
    return {"funds": runstate.state.funds, "acidity": runstate.state.acidity, "fish": runstate.state.fish_yield_multiplier()}


def show_season_report(before, after):
    """GD-30: a short overlay after Advance Season. Skipped with reduced motion (the live-region announcement still says it all)."""
    el = document.getElementById("season-report-card")
    if el is None or _reduced_motion():
        return False
    el.innerHTML = "".join(
        f'<span class="report-chip report-chip--{"good" if good else "watch"}">{html.escape(text)}</span>' for text, good in season_report_chips(before, after)
    )
    el.hidden = False
    _hide_later("season-report-card", 2200)
    return True


def render_balance():
    el = document.getElementById("balance-display")
    if el is not None:
        el.innerText = balance_text()
    dom = document.getElementById("domino-display")
    if dom is not None:
        text = domino_text()
        dom.innerText = text
        dom.hidden = not text
    render_rescue_burst()


# GD-20 Rewind, GD-23 speedrun trackers, GD-24 ironman -----------------------------------------------------------
_rewind_snapshot = [None]
_last_action_at = [None]


def note_action():
    """Counts one real player click (invest, advance, x5) and the active seconds between clicks."""
    now = time.time()
    last = _last_action_at[0]
    _last_action_at[0] = now
    if last is not None:
        runstate.state.active_seconds += min(IDLE_CAP_SECONDS, max(0.0, now - last))
    runstate.state.actions_count += 1


def can_rewind():
    snap = _rewind_snapshot[0]
    return (not runstate.state.rewind_used) and snap is not None and snap.get("season", 10**9) < runstate.state.season


def load_speedrun_best():
    raw = _read_local_storage_item(SPEEDRUN_KEY)
    try:
        data = json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        return {}
    out = {}
    if isinstance(data, dict):
        for key in ("actions", "seconds"):
            value = data.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 < value < 1e9:
                out[key] = float(value)
    return out


def record_speedrun():
    """Stores a new personal best (fewest clicks, fewest seconds) once this run has reached the top tier."""
    if runstate.state.maxtier_actions is None:
        return False
    best = load_speedrun_best()
    changed = False
    if "actions" not in best or runstate.state.maxtier_actions < best["actions"]:
        best["actions"], changed = float(runstate.state.maxtier_actions), True
    if "seconds" not in best or runstate.state.maxtier_seconds < best["seconds"]:
        best["seconds"], changed = float(runstate.state.maxtier_seconds), True
    if changed:
        _write_local_storage_item(SPEEDRUN_KEY, json.dumps(best))
    return changed


def speedrun_text():
    best = load_speedrun_best()
    now = (f"This run: top tier in {runstate.state.maxtier_actions} clicks, about {runstate.state.maxtier_seconds:.0f} s."
           if runstate.state.maxtier_actions is not None else
           f"This run: {runstate.state.actions_count} clicks and about {runstate.state.active_seconds:.0f} s so far; the top tier is not reached yet.")
    if not best:
        return now + " No speedrun best yet."
    return now + f" Best: {best.get('actions', 0):.0f} clicks, {best.get('seconds', 0):.0f} s."


def render_run_extras():
    badge = document.getElementById("ironman-badge")
    if badge is not None:
        badge.hidden = not runstate.state.ironman_earned
        badge.innerText = "\u2693" if runstate.state.ironman_earned else ""
        badge.title = f"Hard-lag ironman: {IRONMAN_SEASONS} seasons with no Rewind and no checkpoint replay"
    tin = document.getElementById("tin-hat-badge")
    if tin is not None:
        tin.hidden = not runstate.state.rewind_used
        tin.innerText = "\U0001FA96" if runstate.state.rewind_used else ""
        tin.title = "This run used its Rewind"
    button = document.getElementById("rewind-button")
    if button is not None:
        button.disabled = not can_rewind()
        button.title = ("Retract the last Advance click once per run; the run is marked with a tin hat"
                        if not runstate.state.rewind_used else "This run has already used its Rewind")
    sr = document.getElementById("speedrun-display")
    if sr is not None:
        sr.innerText = speedrun_text()
