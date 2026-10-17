"""The Meridian Cartel contest: contest cycle, undercut, intel, ledger line and panel."""

from js import document

import trade_runstate as runstate
from trade_effects import MERIDIAN_PRESSURE, meridian_active_contest, meridian_exclusive_good
from trade_expedition import _mix
from trade_market import seasonal_reachable_goods
from trade_records import RECORDS_COUNT_MAX, records
from trade_rules import GOOD_LABEL


# ---------------------------------------------------------------------------
# J-11 / J-12 -- Meridian Freight (Market Desk window, opt-in, off by default): a non-violent shadow firm
# that contests the same routes. Every MERIDIAN_CYCLE ticks it contests one good for MERIDIAN_CONTEST_TICKS
# ticks and your price for that good softens by MERIDIAN_PRESSURE; there is no combat and no piracy, it is
# only ever seen through a price move you did not cause. Three honest answers: undercut it (a small fee ends
# the contest and shields that good for MERIDIAN_SHIELD_TICKS), sign an exclusive Trade Guild contract for the
# contested good (Meridian stays away while it is active), or ignore it (it costs only the dip). The rival
# ledger line says how many units Meridian moved this cycle: a rumoured, unverified number until you have
# Market Intel (Market Insight research, or a one-time Intel desk purchase for the other research path), then
# the real figure and the good and dip behind it. Everything is derived from the founding seed and the cycle
# number, so it is deterministic.
# ---------------------------------------------------------------------------
MERIDIAN_CYCLE = 50
MERIDIAN_CONTEST_TICKS = 25

MERIDIAN_SHIELD_TICKS = 40
MERIDIAN_UNDERCUT_COST = 60
MERIDIAN_UNITS_CONTESTING = 14
MERIDIAN_UNITS_QUIET = 4
MERIDIAN_INTEL_COST = 200
MERIDIAN_ANSWER_ACHIEVEMENT = 1


def meridian_has_intel():
    return "market_insight" in runstate.unlocked_research or runstate.meridian_intel_bought


def _meridian_pick(cycle):
    goods = seasonal_reachable_goods()
    if not goods:
        return None
    return goods[_mix(runstate.founding_seed, cycle, 31) % len(goods)]


def meridian_tick():
    if not runstate.meridian_enabled:
        return
    runstate.meridian_ticks += 1
    if runstate.meridian_shield is not None:
        runstate.meridian_shield["left"] -= 1
        if runstate.meridian_shield["left"] <= 0:
            runstate.meridian_shield = None
    if runstate.meridian_contest is not None:
        runstate.meridian_contest["left"] -= 1
        if runstate.meridian_contest["left"] <= 0:
            runstate.meridian_contest = None
    runstate.meridian_units += MERIDIAN_UNITS_CONTESTING if runstate.meridian_contest is not None else MERIDIAN_UNITS_QUIET
    if runstate.meridian_ticks % MERIDIAN_CYCLE == 0:
        runstate.meridian_units = 0
        good = _meridian_pick(runstate.meridian_ticks // MERIDIAN_CYCLE)
        if good is not None and not (runstate.meridian_shield is not None and runstate.meridian_shield["good"] == good):
            runstate.meridian_contest = {"good": good, "left": MERIDIAN_CONTEST_TICKS}
            if good == meridian_exclusive_good() and not runstate.sandbox_active:
                records["meridian_answers"] = min(RECORDS_COUNT_MAX, records["meridian_answers"] + 1)
            if not runstate.sandbox_active:
                records["meridian_contests"] = min(RECORDS_COUNT_MAX, records["meridian_contests"] + 1)


def can_undercut_meridian():
    return meridian_active_contest() is not None and runstate.total_profit >= MERIDIAN_UNDERCUT_COST


def undercut_meridian():
    if not can_undercut_meridian():
        return False
    good = runstate.meridian_contest["good"]
    runstate.total_profit -= MERIDIAN_UNDERCUT_COST
    runstate.meridian_contest = None
    runstate.meridian_shield = {"good": good, "left": MERIDIAN_SHIELD_TICKS}
    if not runstate.sandbox_active:
        records["meridian_answers"] = min(RECORDS_COUNT_MAX, records["meridian_answers"] + 1)
    return True


def meridian_ledger_line():
    """J-12: 'Meridian moved N units this cycle', rumoured until Market Intel, real afterwards."""
    cycle = runstate.meridian_ticks // MERIDIAN_CYCLE
    if not meridian_has_intel():
        guess = 150 + _mix(runstate.founding_seed, cycle, 53) % 300
        return f"Rumour: Meridian moved about {guess} units this cycle (unverified; Market Intel would show the real figure)."
    contest = runstate.meridian_contest
    detail = ""
    if contest is not None:
        shown = "dormant (your exclusive contract)" if meridian_active_contest() is None else f"your price {-MERIDIAN_PRESSURE * 100:.0f}%"
        detail = f" Contesting {GOOD_LABEL[contest['good']]}, {contest['left']} tick(s) left, {shown}."
    elif runstate.meridian_shield is not None:
        detail = f" Held off from {GOOD_LABEL[runstate.meridian_shield['good']]} for {runstate.meridian_shield['left']} more tick(s)."
    return f"Intel: Meridian moved {runstate.meridian_units} units this cycle.{detail}"


def meridian_status_text():
    if not runstate.meridian_enabled:
        return (
            f"Optional rival firm: every {MERIDIAN_CYCLE} ticks Meridian Freight contests one good for "
            f"{MERIDIAN_CONTEST_TICKS} ticks and your price for it softens {MERIDIAN_PRESSURE * 100:.0f}%. No combat, no piracy. "
            "Answer by undercutting it, signing an exclusive Trade Guild contract for that good, or ignore it."
        )
    return (
        f"Meridian contests so far: {records['meridian_contests']}, answered: {records['meridian_answers']}. "
        + meridian_ledger_line()
    )


def render_meridian():
    status = document.getElementById("meridian-status")
    if status is None:
        return
    toggle = document.getElementById("meridian-toggle-button")
    toggle.innerText = f"Meridian Freight: {'on' if runstate.meridian_enabled else 'off'}"
    toggle.setAttribute("aria-pressed", "true" if runstate.meridian_enabled else "false")
    status.innerText = meridian_status_text()
    undercut = document.getElementById("meridian-undercut-button")
    undercut.hidden = meridian_active_contest() is None
    undercut.disabled = not can_undercut_meridian()
    undercut.innerText = f"Undercut Meridian ({MERIDIAN_UNDERCUT_COST})"
    undercut.title = f"Ends the contest now and keeps Meridian off that good for {MERIDIAN_SHIELD_TICKS} ticks."
    intel = document.getElementById("meridian-intel-button")
    intel.hidden = not runstate.meridian_enabled or meridian_has_intel()
    intel.disabled = runstate.total_profit < MERIDIAN_INTEL_COST
    intel.innerText = f"Open an intel desk ({MERIDIAN_INTEL_COST})"
