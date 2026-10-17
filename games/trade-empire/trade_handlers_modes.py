"""Click handlers and starters for the modes: Trade Crises, the Chain Builder, the Modes screen."""

import copy

import trade_runstate as runstate
from trade_chain_logic import _chain_new_board, _chain_real_best
from trade_chain_rules import CHAIN_BY_ID, CHAIN_PUZZLES
from trade_chain_ui import _chain_sync_levels, _level_select_create, chain_levels_list, chain_levels_state
from trade_crises import CRISES, _crisis_state
from trade_loading import _apply_state, sandbox_enter, sandbox_leave
from trade_modes import (
    MODE_IDS, _call_after_menu_closes, _modes_sync_screen, modes_done_ids, modes_levels_list,
)
from trade_renderer import render
from trade_sandbox import _reset_running_tables, _sandbox_notify_page, _sandbox_set_real_aside
from trade_uikit import show_notice_toast


def crisis_enter(crisis_id):
    """Starts (or restarts) a crisis. The real corporation is set aside exactly as the practice sandbox does it."""
    if crisis_id not in CRISES:
        return False
    if not runstate.sandbox_active:
        _sandbox_set_real_aside()
    elif runstate.crisis_active is None:  # leave a practice sandbox first, then start from the real game
        sandbox_leave()
        return crisis_enter(crisis_id)
    runstate.crisis_active, runstate.crisis_ticks, runstate.crisis_done = crisis_id, 0, None  # before the load: a crisis has its own purse
    _reset_running_tables()
    _apply_state(_crisis_state(crisis_id))
    render()
    _sandbox_notify_page()
    return True


def crisis_restart():
    return crisis_enter(runstate.crisis_active) if runstate.crisis_active is not None else False


def _make_crisis_start_handler(crisis_id):
    def handler(event=None):
        crisis_enter(crisis_id)
    return handler


def on_crisis_restart(event=None):
    crisis_restart()


def on_crisis_leave(event=None):
    if runstate.crisis_active is not None:
        sandbox_leave()


def chain_enter(puzzle_id):
    """Starts (or restarts) a puzzle. The real corporation is set aside exactly as the practice sandbox does it,
    and a blank corporation (which does not tick while a puzzle is open) stands in for it."""
    if puzzle_id not in CHAIN_BY_ID:
        return False
    if runstate.sandbox_active and runstate.chain_active is None:  # a crisis or the practice sandbox: back to the real game first
        sandbox_leave()
    _chain_new_board(puzzle_id)  # before the load: _apply_state() renders, and a puzzle has no sandbox purse
    if not runstate.sandbox_active:
        _sandbox_set_real_aside()
        _reset_running_tables()
        _apply_state(copy.deepcopy(runstate._fresh_state))
    runstate.chain_open = True
    render()
    _sandbox_notify_page()
    return True


def chain_leave():
    if runstate.chain_active is not None:
        sandbox_leave()
        _sandbox_notify_page()  # the banner and the sandbox button follow sandbox_is_active()


def on_chain_leave(event=None):
    chain_leave()


def on_chain_pick(event=None):
    if runstate._chain_levels is None:
        runstate._chain_levels = _level_select_create(
            "chain-select", "Chain Builder puzzles", chain_levels_list(), chain_levels_state(), chain_enter)
    if runstate._chain_levels is None:
        chain_enter(next((p["id"] for p in CHAIN_PUZZLES if p["id"] not in _chain_real_best()), CHAIN_PUZZLES[0]["id"]))
        return
    _chain_sync_levels()
    runstate._chain_levels.open()


def modes_start(mode_id):
    """Takes the player to a rung. Nothing is switched on without the mode's own button (Blackout asks first)."""
    if mode_id not in MODE_IDS:
        return False
    if mode_id == "core":
        show_notice_toast("The core game: load a ship, pick a destination, sell, research, automate. Everything else can wait until you want it.")
    elif mode_id in ("expeditions", "crises"):
        runstate.lab_open = True
        show_notice_toast("Fleet Lab: " + ("Expeditions are at the bottom." if mode_id == "expeditions" else "Trade Crises are near the top."))
    elif mode_id == "chain":
        runstate.chain_open = True
    elif mode_id == "blackout":
        show_notice_toast("Blackout is switched on from the Market panel. It asks first and you can switch it off again.")
    elif mode_id == "sandbox":
        sandbox_enter()
        _sandbox_notify_page()
    render()
    return True


def on_modes_open(event=None):
    if runstate._modes_screen is None:
        runstate._modes_screen = _level_select_create(
            "modes-select", "Game modes", modes_levels_list(), {"done": modes_done_ids(), "best": {}}, modes_start)
    if runstate._modes_screen is None:
        return
    _modes_sync_screen()
    _call_after_menu_closes(runstate._modes_screen.open)
