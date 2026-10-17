"""get_state() / load_state() for the shared save widget, and entering and leaving the practice sandbox."""

import copy

from js import document

import sandbox
import sim

import continuum_runstate as runstate
from continuum_achievements import _seed_achievement_toast_baseline, achievement_ids_earned
from continuum_archive import _compare_picks
from continuum_base import _js_window, _rewind_clear
from continuum_dynasty import _adopt_local_dynasty
from continuum_founders import sync_name_input

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# --- the shared save widget's contract ---------------------------------
# SAVE-BUTTON-INTEGRATION.md: shared/save-widget.js drives every game in the
# hub through exactly these two functions and never looks inside the dict,
# so Continuum's era-snapshot/revisit structure needs no widget changes —
# see save.py for the schema itself.
def get_state():
    if runstate.sandbox_active:  # Z-18: a save, an autosave or a board read while the sandbox is on is the REAL game
        return copy.deepcopy(runstate._sandbox_real["snapshot"])
    runstate.campaign.ui["info_page_open"] = runstate.info_page_open
    data = runstate.campaign.to_dict()
    # Milestone 15 (ACHIEVEMENTS-SYSTEM-DESIGN.md): a write-only projection,
    # not part of Campaign's own save schema — always recomputed fresh here,
    # never read back in load_state() below.
    data["achievements_earned"] = achievement_ids_earned()
    return data


def load_state(data):
    if runstate.sandbox_active:  # Z-18: loading a save always lands in the real game
        _sandbox_restore_real()
    if not runstate.campaign.load_dict(data):
        _sandbox_notify_page()
        return False
    runstate.info_page_open = bool(runstate.campaign.ui.get("info_page_open", False))
    _rewind_clear()
    _adopt_local_dynasty()
    sync_name_input()
    render()
    _seed_achievement_toast_baseline()
    _sandbox_notify_page()
    return True


# --- Z-18: entering and leaving the practice sandbox ---------------------------------------------
_SANDBOX_STASHED = (
    "info_page_open", "sim_speed", "season_progress", "_rewind_snapshot", "found_status",
    "_archive_confirm_clear", "orders_status", "beyond_status", "neighbours_status", "heritage_confirm",
)
_SANDBOX_RESET_SIGNATURES = (
    "_orders_signature", "_beyond_signature", "_advisors_signature_seen", "_hamlet_built_key", "_hamlet_town_key",
)


def _sandbox_notify_page():
    """Tells shared/sandbox-mode.js to re-read sandbox_is_active() (the banner and button follow it)."""
    window = _js_window()
    shared = getattr(window, "NoyvjSandbox", None) if window is not None else None
    if shared is not None:
        shared.sync()


def sandbox_is_active():
    return runstate.sandbox_active


def _sandbox_era_choice():
    """The era picked in Settings, or the real settlement's own era."""
    element = document.getElementById("sandbox-era-select")
    value = getattr(element, "value", "") if element is not None else ""
    return value if value in sim.ERA_ORDER else runstate.state.era


def _sandbox_swap_in(new_campaign):
    runstate.campaign = new_campaign
    runstate.state = runstate.campaign.state
    runstate.tree = runstate.campaign.tree
    runstate.chronicle = runstate.campaign.log
    for name in _SANDBOX_RESET_SIGNATURES:
        vars(runstate)[name] = None


def sandbox_enter():
    """Sets the real settlement aside and starts a practice one. True when the sandbox is on."""
    if runstate.sandbox_active:
        return True
    era = _sandbox_era_choice()
    snapshot = get_state()
    runstate._sandbox_real = {
        "campaign": runstate.campaign,
        "snapshot": snapshot,
        "earned": list(snapshot["achievements_earned"]),
        "globals": {name: vars(runstate)[name] for name in _SANDBOX_STASHED},
        "compare": list(_compare_picks),
    }
    runstate.sandbox_active = True
    _sandbox_swap_in(sandbox.new_campaign(era))
    runstate.sim_speed = 0
    runstate.season_progress = 0.0
    runstate._rewind_snapshot = None
    runstate.found_status = ""
    sync_name_input()
    render()
    return True


def _sandbox_restore_real():
    """Puts the real settlement back exactly as it was (no render; callers do that)."""
    real = runstate._sandbox_real
    runstate.sandbox_active = False
    runstate._sandbox_real = None
    if real is None:
        return
    _sandbox_swap_in(real["campaign"])
    vars(runstate).update(real["globals"])
    _compare_picks[:] = real["compare"]
    runstate.sim_speed = 0  # back paused: nothing moved while the real game was away
    sync_name_input()
    _seed_achievement_toast_baseline()


def sandbox_leave():
    """Leaves the sandbox; the real settlement is back and untouched. True when it is."""
    if not runstate.sandbox_active:
        return True
    _sandbox_restore_real()
    render()
    return True
