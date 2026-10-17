"""Click handlers for the panels: ranch rules, ghost, ledger, mixer, family story, profile, recovery, settings import, barns,
golden cow, blind run, loadouts and the sandbox (enter, leave, sliders, reset).
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import copy

from js import document

import herd_runstate as runstate
from herd_rules import MIXER_AUTO_QUALITY, MIXER_MIN_QUALITY
from herd_util import _is_finite_number, _write_local_storage_item
from herd_purchases import _confirm_dialog_ask
from herd_blind import reveal_blind_run, set_blind_run
from herd_achievements import _display_milestone_toast
from herd_sandbox import (
    _SANDBOX_COPIED, _SANDBOX_STASHED, _sandbox_fresh_globals, _sandbox_restore_real, new_sandbox_farm,
    sandbox_control_id, set_sandbox_value,
)
from herd_barns import barn_by_id, choose_barn, welcome_golden_cow
from herd_loadouts import LOADOUTS, choose_loadout
from herd_rules_ui import reset_rules, rule_id, set_rule
from herd_ledger import GHOST_PREF_KEY, _ghost_el, file_ghost, ledger_entry, ledger_record
from herd_mixer import mixer_blend, render_mixer
from herd_family import family_choices_now, family_choose, family_ending_ready
from herd_savegame import get_state, render_save_recovery, sanitize_save
from herd_settings_code import _set_settings_code_status, import_settings_code
from herd_renderer import render
from herd_loading import _apply_state


def _make_rule_handler(name):
    def handler(event=None):
        try:
            value = float(document.getElementById(rule_id(name)).value)
        except (TypeError, ValueError):
            return
        set_rule(name, value)
        render()
    return handler


def on_reset_rules(event=None):
    reset_rules()
    render()


def on_toggle_ghost(event=None):
    toggle = _ghost_el("ghost-toggle")
    on = True if toggle is None else bool(toggle.checked)
    _write_local_storage_item(GHOST_PREF_KEY, "1" if on else "0")
    render()


def on_ledger_add(event=None):
    if runstate.sandbox_active:
        return
    reveal_blind_run()  # GF-28: filing a farm ends a blind run (the ledger line carries the baseline gap)
    ledger_record(ledger_entry(finished=False))
    file_ghost()  # Z-3e
    render()
    _display_milestone_toast("Filed this farm in the Ranch Ledger.")


def on_mixer_result(event=None):
    try:
        quality = float(document.getElementById("mixer-result-button").getAttribute("data-quality"))
    except (TypeError, ValueError):
        return
    if not _is_finite_number(quality):
        return  # junk from the page never uses up the round's blend
    if mixer_blend(max(MIXER_MIN_QUALITY, min(1.0, quality))) is not None:
        render()
    else:
        render_mixer()


def on_mixer_auto(event=None):
    if mixer_blend(MIXER_AUTO_QUALITY, auto=True) is not None:
        render()
    else:
        render_mixer()


def _make_family_choice_handler(slot):
    def handler(event=None):
        offered = family_choices_now()
        if slot < len(offered) and family_choose(offered[slot][0]):
            render()
    return handler


def on_family_retell(event=None):
    """Starts the story over for this farm. Endings already found stay found."""
    if family_ending_ready():
        runstate.farm.story_choices = []
        render()


def on_profile_change(event=None):
    render()


def on_recovery_defaults(event=None):
    if runstate.pending_recovery is None or runstate.pending_recovery["data"] is None:
        return
    clean = sanitize_save(runstate.pending_recovery["data"], runstate.pending_recovery["problems"])
    runstate.pending_recovery = None
    render_save_recovery()
    _apply_state(clean)


def on_settings_import(event=None):
    box = document.getElementById("settings-code-box")
    ok, message = import_settings_code(box.value)
    _set_settings_code_status(message)
    if ok:
        render()


def _make_barn_handler(barn_id):
    def handler(event=None):
        if choose_barn(barn_id):
            runstate.barn_status_text = f"{barn_by_id(barn_id)['label']} chosen. It only changes how the pasture looks."
        render()
    return handler


def on_welcome_golden_cow(event=None):
    paid = welcome_golden_cow()
    if paid is not None:
        runstate.golden_cow_status_text = f"The golden cow left {paid:g} funds behind. Welcomed so far: {runstate.farm.golden_claimed}."
        _display_milestone_toast(f"\u2728 Golden cow welcomed: +{paid:g} funds.")
    render()


def on_toggle_blind_run(event=None):
    set_blind_run(document.getElementById("blind-run-checkbox").checked)
    render()


def on_reveal_blind_run(event=None):
    def do_reveal():
        if reveal_blind_run():
            _display_milestone_toast("Blind run revealed. Open the Baseline Farm card for the full comparison.")
        render()

    _confirm_dialog_ask(
        action_id="herd-blind-reveal",
        message="Reveal the baseline comparison? The blind run ends for this farm and it cannot be hidden again.",
        confirm_label="Reveal",
        on_confirm=do_reveal,
        allow_skip=False,
    )


def on_loadout_change(event=None):
    value = document.getElementById("loadout-select").value
    result = choose_loadout(value)
    if result == "applied":
        runstate.loadout_status_text = f"{LOADOUTS[runstate.loadout_choice]['label']} applied to this farm."
    elif result == "saved":
        runstate.loadout_status_text = f"{LOADOUTS[runstate.loadout_choice]['label']} will open your next generation (this farm has already started)."
    else:
        runstate.loadout_status_text = "That loadout is still locked."
    render()


def sandbox_enter():
    """Sets the real farm aside and starts a practice farm. True when the sandbox is on."""
    if runstate.sandbox_active:
        return True
    snapshot = get_state()
    stash = {name: vars(runstate)[name] for name in _SANDBOX_STASHED}
    runstate._sandbox_real = {"farm": runstate.farm, "snapshot": snapshot, "earned": list(snapshot["achievements_earned"]), "globals": stash}
    runstate.sandbox_active = True
    for name in _SANDBOX_COPIED:  # the sandbox works on copies; the originals wait untouched
        vars(runstate)[name] = copy.deepcopy(stash[name])
    vars(runstate).update(_sandbox_fresh_globals())
    runstate.farm = new_sandbox_farm()
    render()
    return True


def sandbox_leave():
    """Back to the real farm, unchanged. True when the real game is back."""
    if not runstate.sandbox_active:
        return True
    _sandbox_restore_real()
    render()
    return True


def _make_sandbox_handler(name):
    def handler(event=None):
        try:
            value = float(document.getElementById(sandbox_control_id(name)).value)
        except (TypeError, ValueError):
            return
        set_sandbox_value(name, value)
        render()
    return handler


def on_sandbox_reset(event=None):
    if not runstate.sandbox_active:
        return
    runstate.farm = new_sandbox_farm()
    render()
