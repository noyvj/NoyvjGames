"""Practice sandbox helpers: the stash of real-game values, the balance slider text and the page notification.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document

import grid_runstate as runstate
from grid_sandbox_state import SANDBOX_BALANCE, SANDBOX_BALANCE_DEFAULTS
from grid_announce import _seed_achievement_toast_baseline


# --- Z-18: entering and leaving the practice sandbox ---------------------------------------------
# shared/sandbox-mode.js calls sandbox_enter() / sandbox_leave() / sandbox_is_active() through Pyodide and
# draws the "Sandbox: nothing here is saved" banner. The real game is set aside, never edited: the
# module-level `state` is simply pointed at a SandboxGridState, and every other piece of module state a
# save reads (career, the shadow twin, the real-grid compare, the info page flag) is stashed and put back.
_SANDBOX_STASHED = (
    "info_page_open", "shadow_scenario", "shadow_actions", "real_grid_choice", "last_finish_records",
    "auto_advance_message", "run_setup_message", "difficulty_note", "career_data_message",
    "renewable_milestone_visible", "retire_callout_visible", "maintain_callout_visible", "career",
)


def _sandbox_fresh_globals():
    return {
        "shadow_scenario": None, "shadow_actions": [], "real_grid_choice": None, "last_finish_records": [],
        "auto_advance_message": "", "run_setup_message": "", "difficulty_note": "", "career_data_message": "",
        "renewable_milestone_visible": False, "retire_callout_visible": False, "maintain_callout_visible": False,
    }


def _sandbox_notify_page():
    """Tells shared/sandbox-mode.js to re-read sandbox_active() (the banner and button follow it)."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    shared = getattr(window, "NoyvjSandbox", None)
    if shared is not None:
        shared.sync()


def sandbox_is_active():
    return runstate.sandbox_active


def sandbox_balance_text():
    """One plain line saying what the sliders are set to and that none of it counts."""
    if not runstate.sandbox_active:
        return ""
    moved = [
        f"{spec['label'].lower()} {spec['format'].format(runstate.state.balance[key])}"
        for key, spec in SANDBOX_BALANCE.items() if abs(runstate.state.balance[key] - SANDBOX_BALANCE_DEFAULTS[key]) > 1e-9
    ]
    base = "Sandbox balance: nothing here counts for career points, achievements or community stats."
    return base + (" Changed: " + "; ".join(moved) + "." if moved else " All sliders at their usual values.")


def render_sandbox_balance():
    panel = document.getElementById("sandbox-balance")
    panel.hidden = not runstate.sandbox_active
    if not runstate.sandbox_active:
        return
    for key, spec in SANDBOX_BALANCE.items():
        slug = key.replace("_", "-")
        document.getElementById(f"sandbox-bal-{slug}").value = str(runstate.state.balance[key])
        document.getElementById(f"sandbox-bal-{slug}-out").innerText = spec["format"].format(runstate.state.balance[key])
    document.getElementById("sandbox-bal-note").innerText = sandbox_balance_text()


def _sandbox_restore_real():
    """Puts the real game back exactly as it was (no render; callers do that)."""
    real = runstate._sandbox_real
    runstate.sandbox_active = False
    runstate._sandbox_real = None
    if real is None:
        return
    runstate.state = real["state"]
    vars(runstate).update(real["globals"])
    _seed_achievement_toast_baseline()
