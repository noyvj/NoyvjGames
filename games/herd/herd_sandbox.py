"""Practice sandbox core (GF-24): the sandbox farm, the stash that sets the real game aside, the sliders. Entering and leaving
the sandbox needs render() and get_state(), so those two functions live in herd_handlers_panels.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

from js import document

import herd_runstate as runstate
from herd_util import _is_finite_number
from herd_model import FarmState
from herd_achievements import _seed_achievement_toast_baseline


# ---- GF-24 practice sandbox --------------------------------------------------------------------
# A place to set the herd, the methane and the levers freely and watch the gauge, the pressure and the
# income react, with unlimited funds. shared/sandbox-mode.js draws the button, banner and frame and calls
# sandbox_enter() / sandbox_leave() / sandbox_is_active(); everything else stays here. The rules:
#   - the real farm is set aside whole (never edited) and put back as the very same object on leaving, so
#     get_state() is byte-identical before and after;
#   - get_state() answers with the REAL game while the sandbox is on, so Save, the autosave and the
#     leaderboard hooks can never write the sandbox;
#   - nothing in the sandbox earns an achievement, a breed, combo, barn or loadout, sets a record, files a
#     ledger line or writes browser storage (_write_local_storage_item is a no-op), and it is never
#     compared with other farms (rules_unranked() is true);
#   - loading a save leaves the sandbox first. It lives in memory only: a reload is the real game.
SANDBOX_FUNDS = 1_000_000
SANDBOX_CONTROLS = {
    # name: (minimum, maximum, step)
    "herd": (0, 80, 1), "methane": (0, 300, 5), "feed": (0, 15, 1), "caps": (0, 15, 1), "capture": (0, 10, 1),
    "pivot": (0, 12, 1), "poultry": (0, 30, 1),
}


class SandboxFarmState(FarmState):
    """The practice farm: the balance never drops below SANDBOX_FUNDS, so anything can be bought."""
    sandbox = True

    @property
    def funds(self):
        return self._funds

    @funds.setter
    def funds(self, value):
        self._funds = max(float(value), float(SANDBOX_FUNDS))


_SANDBOX_COPIED = (
    "ranch_rules", "legacy_perks", "breeds_collected", "combos_found", "hall_of_fame", "family_endings",
    "barns_unlocked", "loadouts_unlocked", "pinned_stats",
)
_SANDBOX_STASHED = _SANDBOX_COPIED + (
    "generation", "legacy_points", "barn_skin", "loadout_choice", "record_coupling_ratio", "last_deltas",
    "delta_pinned", "delta_faded", "plan_steps", "explain_kind", "mixer_message", "golden_cow_status_text",
    "loadout_status_text", "barn_status_text", "last_round_income",
)


def _sandbox_fresh_globals():
    return {
        "last_deltas": {}, "delta_pinned": set(), "delta_faded": False, "plan_steps": [], "explain_kind": None,
        "mixer_message": "", "golden_cow_status_text": "", "loadout_status_text": "", "barn_status_text": "",
        "last_round_income": None,
    }


def new_sandbox_farm():
    fresh = SandboxFarmState()
    fresh.audit_perks = []
    return fresh


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


def _sandbox_restore_real():
    """Puts the real farm and every stashed value back exactly as it was (no render; callers do that)."""
    real = runstate._sandbox_real
    runstate.sandbox_active = False
    runstate._sandbox_real = None
    if real is None:
        return
    runstate.farm = real["farm"]
    vars(runstate).update(real["globals"])
    _seed_achievement_toast_baseline()


def sandbox_control_id(name):
    return "sandbox-" + name


def sandbox_current_value(name):
    if name == "herd":
        return runstate.farm.herd_size
    if name == "methane":
        return runstate.farm.methane
    if name == "pivot":
        return runstate.farm.plant_pivot_investment
    if name == "poultry":
        return runstate.farm.poultry_size
    return runstate.farm.decoupling_investment[name]


def set_sandbox_value(name, value):
    """Sets one slider's quantity on the practice farm (clamped to its range). True when it changed."""
    if not runstate.sandbox_active or name not in SANDBOX_CONTROLS or not _is_finite_number(value):
        return False
    low, high, step = SANDBOX_CONTROLS[name]
    value = max(low, min(high, round(value / step) * step))
    if abs(value - sandbox_current_value(name)) < 1e-9:
        return False
    if name == "herd":
        runstate.farm.herd_size = int(value)
    elif name == "methane":
        runstate.farm.methane = float(value)
        runstate.farm.methane_history[-1] = float(value)
    elif name == "pivot":
        runstate.farm.plant_pivot_investment = int(value)
    elif name == "poultry":
        runstate.farm.poultry_size = int(value)
    else:
        runstate.farm.decoupling_investment[name] = int(value)
    return True


def render_sandbox():
    panel = document.getElementById("sandbox-panel")
    panel.hidden = not runstate.sandbox_active
    if not runstate.sandbox_active:
        return
    for name in SANDBOX_CONTROLS:
        value = sandbox_current_value(name)
        document.getElementById(sandbox_control_id(name)).value = f"{value:g}"
        document.getElementById(sandbox_control_id(name) + "-value").innerText = f"{value:g}"
    document.getElementById("sandbox-note").innerText = (
        f"Coupling ratio {runstate.farm.coupling_ratio():.2f}, methane per round {runstate.farm.methane_this_round():.1f}, pressure "
        f"{runstate.farm.pressure_fraction() * 100:.0f}% income loss, income per round {runstate.farm.income_breakdown()['total']:.1f}. "
        "Nothing here is scored, saved or compared with other farms."
    )
