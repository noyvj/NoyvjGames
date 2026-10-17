"""Click handlers for the core game (load, depart, invest, buy, rename, automate, research, fleet priority, renewal) and the confirm dialog."""

import copy
import json

from js import document
from pyodide.ffi import create_proxy

import trade_runstate as runstate
from trade_achievements import ACHIEVEMENTS, _earned_snapshot, achievement_ids_earned
from trade_charter import (
    CAREER_MAX_ENTRIES, CHARTER_COUNT_MAX, automation_cost, charter_points_for_next_renewal,
    guild_first_offer_ticks, hard_charter_unlocked,
)
from trade_effects import LEGACY_SALE_BONUS
from trade_founding import (
    LEGACY_MAX_LEVEL, apply_founding_conditions, can_found_new_corporation, legacy_starting_credits,
)
from trade_ghost import _ghost_bank, ghost_best
from trade_guild import _guild_clear
from trade_loading import load_state
from trade_market import buy_stockpile, sell_stockpile
from trade_records import records
from trade_renderer import render
from trade_research import RESEARCH_NODES, set_fleet_priority, unlock_research
from trade_ships import (
    DEFAULT_ARCHETYPE, automate_ship, grant_concession, invest_in_colony, purchase_ship, rename_ship,
    reset_ship_name, ships,
)


def found_new_corporation():
    """Renew the charter: reset to a fresh corporation, raise the legacy (to
    its cap), earn charter points, keep the perk tree, the ledger and the
    achievements, and roll new founding conditions. Returns False when the
    endgame hasn't been reached."""
    if not can_found_new_corporation():
        return False
    order = {entry["id"]: i for i, entry in enumerate(ACHIEVEMENTS)}
    carried = sorted(set(runstate.legacy_achievements) | set(achievement_ids_earned()), key=lambda a: order.get(a, 10**6))
    new_level = min(LEGACY_MAX_LEVEL, runstate.legacy_level + 1)
    _ghost_bank()  # Z-3e5: before the charter's path is cleared below
    keep = {
        "ghost_best": copy.deepcopy(ghost_best),
        "completed": runstate.charters_completed,
        "points": runstate.charter_points_earned + charter_points_for_next_renewal(),
        "perks": set(runstate.charter_perks),
        "hard_done": runstate.ledger_hard_completed,
        "units": runstate.ledger_units_moved,
        "routes": runstate.ledger_routes_established,
        "career": list(runstate.charter_career) + [{
            "n": min(CHARTER_COUNT_MAX, runstate.charters_completed + 1),
            "hard": bool(runstate.hard_charter_active),
            "units": runstate.ledger_charter_units,
            "routes": len(runstate.ledger_routes_seen),
            "peak": int(runstate.max_profit_ever),
            "perks": len(runstate.charter_perks),
            **({"dark": True} if runstate.blackout_done else {}),  # J-30
        }],
        "met": set(runstate.captains_met),
        "records": copy.deepcopy(records),
        "seed": (runstate.run_seed, runstate.run_seed_pinned, runstate.hazard_rolls, runstate.guild_offers),
    }
    finishing_hard = runstate.hard_charter_active
    begin_hard = runstate.hard_charter_next and hard_charter_unlocked()
    load_state(json.loads(json.dumps(runstate._fresh_state)))
    runstate.legacy_achievements = carried
    runstate.charter_perks = keep["perks"]
    runstate.charter_points_earned = keep["points"]
    runstate.charters_completed = keep["completed"]
    runstate.ledger_hard_completed = keep["hard_done"]
    runstate.ledger_units_moved, runstate.ledger_routes_established = keep["units"], keep["routes"]
    runstate.ledger_routes_seen = set()
    runstate.ledger_charter_units = 0
    runstate.charter_career = keep["career"][-CAREER_MAX_ENTRIES:]
    runstate.run_seed, runstate.run_seed_pinned, runstate.hazard_rolls, runstate.guild_offers = keep["seed"]  # the seed and its stream positions outlive a renewal
    runstate.captains_met = keep["met"]
    records.clear()
    records.update(keep["records"])
    ghost_best.clear()
    ghost_best.update(keep["ghost_best"])  # Z-3e5: the best path outlives a renewal; the new charter's own path starts empty
    _guild_clear(guild_first_offer_ticks())  # Guild Standing shortens the first wait
    # Baseline BEFORE the renewal is counted: the carried achievements must
    # not all toast again, but the ones this renewal earns should.
    runstate._previously_earned_ids = _earned_snapshot()
    runstate.legacy_level = new_level
    runstate.charters_completed = min(CHARTER_COUNT_MAX, keep["completed"] + 1)
    if finishing_hard:
        runstate.ledger_hard_completed = min(CHARTER_COUNT_MAX, keep["hard_done"] + 1)
    runstate.hard_charter_active = begin_hard
    runstate.hard_charter_next = False
    runstate.total_profit += legacy_starting_credits()
    runstate.max_profit_ever = max(runstate.max_profit_ever, runstate.total_profit)
    apply_founding_conditions()
    render()
    return True


def _make_load_handler(ship_id):
    def handler(event=None):
        ships[ship_id].load()
        render()
    return handler


def _make_stockpile_buy_handler(good):
    def handler(event=None):
        buy_stockpile(good)
        render()
    return handler


def _make_stockpile_sell_handler(good):
    def handler(event=None):
        sell_stockpile(good)
        render()
    return handler


def _make_concession_handler(colony_id):
    def handler(event=None):
        grant_concession(colony_id)
        render()
    return handler


def _make_invest_handler(colony_id):
    def handler(event=None):
        invest_in_colony(colony_id)
        render()
    return handler


def _make_purchase_ship_handler(ship_id):
    def handler(event=None):
        select = document.getElementById(f"ship-{ship_id}-archetype-select")
        purchase_ship(ship_id, str(select.value) if select is not None else DEFAULT_ARCHETYPE)
        render()
    return handler


def _make_rename_handler(ship_id):
    def handler(event=None):
        input_el = document.getElementById(f"ship-{ship_id}-name-input")
        rename_ship(ship_id, input_el.value)
        render()
    return handler


def _make_reset_name_handler(ship_id):
    def handler(event=None):
        reset_ship_name(ship_id)
        input_el = document.getElementById(f"ship-{ship_id}-name-input")
        if input_el is not None:
            input_el.value = ""
        render()
    return handler


def _make_depart_handler(ship_id, destination):
    def handler(event=None):
        ships[ship_id].depart(destination)
        render()
    return handler


def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm, allow_skip=True):
    """Routes a guarded action through the shared shared/confirm-dialog.js
    widget when it's available, or runs the action immediately when it
    isn't -- same lazy `from js import window`/getattr-default shape as
    every other optional-JS-hook call in this hub (Grid's C14, Herd's
    F16). The pytest fake-DOM harness's `js` module only ever fakes
    `document`/`setTimeout`/`setInterval` (see conftest.py's
    `_install_pyodide_fakes`), never `window`, so `from js import window`
    raises ImportError there and this falls straight through to calling
    on_confirm() synchronously -- which is exactly what every existing
    automate/research test in this suite already expects."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        on_confirm()
        return
    confirm_dialog = getattr(window, "ConfirmDialog", None)
    if confirm_dialog is None:
        on_confirm()
        return
    options = {
        "id": action_id,
        "message": message,
        "confirmLabel": confirm_label,
        "onConfirm": create_proxy(on_confirm),
    }
    if not allow_skip:
        options["allowSkip"] = False  # only sent when needed (see shared/confirm-dialog.js)
    confirm_dialog.ask(**options)


def on_found_new_corporation(event=None):
    if not can_found_new_corporation():
        return
    next_level = min(LEGACY_MAX_LEVEL, runstate.legacy_level + 1)
    legacy_line = (
        f"You gain permanent Legacy level {next_level}: "
        f"+{legacy_starting_credits(next_level):,} starting credits and "
        f"+{round(LEGACY_SALE_BONUS * next_level * 100)}% on every sale. "
        if runstate.legacy_level < LEGACY_MAX_LEVEL
        else "Your Legacy bonus is already at its maximum. "
    )
    hard_line = " The next charter will be a harder one." if runstate.hard_charter_next else ""
    _confirm_dialog_ask(
        "found-new-corporation",
        "Renew the Charter? Your fleet, colonies, research and credits reset to a fresh start with new founding "
        f"conditions. You keep your achievements, charter perks and lifetime ledger, and earn "
        f"{charter_points_for_next_renewal()} charter points. " + legacy_line.rstrip() + hard_line,
        "Renew the Charter",
        found_new_corporation,
        allow_skip=False,
    )


def _make_automate_handler(ship_id):
    # J19 (planning/TODO.md's shared confirmation-dialog goal) -- checked
    # frequency before wiring this in: automating a ship is capped at
    # max_automated_ships() (2, +1 per automation-slot research node, up
    # to the 4-ship roster) and is a one-time, irreversible purchase per
    # ship (no de-automate toggle exists), so across an entire
    # playthrough this button is clicked at most 4 times, ever -- a rare,
    # deliberate milestone action, not part of the repeated Load/Depart
    # core loop. Worth the confirm; see CLAUDE.md for the full reasoning.
    def do_automate():
        automate_ship(ship_id)
        render()

    def handler(event=None):
        _confirm_dialog_ask(
            action_id=f"trade-empire-automate-ship-{ship_id}",
            message=(
                f"Automate this ship for {automation_cost()} credits? "
                "This is permanent -- there's no way to de-automate it "
                "afterward."
            ),
            confirm_label="Automate it",
            on_confirm=do_automate,
        )
    return handler


def _make_research_handler(node_id):
    # J19 -- same frequency reasoning as automation above: RESEARCH_NODES
    # has exactly 6 entries total, each unlockable exactly once ever (the
    # button hides on unlock, no re-lock/refund path), so this button is
    # clicked at most 6 times across an entire playthrough. Also
    # genuinely irreversible spend of a slowly-accrued currency -- the
    # priciest nodes (Galaxy Expansion 80, Outer Reaches 200) represent a
    # long stretch of passive accrual, not pocket change.
    def do_unlock():
        unlock_research(node_id)
        render()

    def handler(event=None):
        node = RESEARCH_NODES[node_id]
        _confirm_dialog_ask(
            action_id=f"trade-empire-research-{node_id}",
            message=(
                f"Unlock {node['label']} for {node['cost']} research "
                f"points? {node['description']}."
            ),
            confirm_label="Unlock it",
            on_confirm=do_unlock,
        )
    return handler


def _fleet_priority_toggle_handler(event=None):
    set_fleet_priority(not runstate.fleet_priority_enabled)
    render()
