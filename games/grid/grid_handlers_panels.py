"""Click and change handlers for panels and settings: preferences, fleet sort, confirmations, rank theme, run slots,
career finish, run setup, Today's run, import and export.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import json

import seed as seed_lib
from js import document

import grid_runstate as runstate
from grid_rules import CAREER_MIN_ROUNDS, PLANT_LABEL, RANK_THEMES, SEED_GAME
from grid_career_actions import run_career_points, set_loadout
from grid_prefs import reset_prefs, reset_skipped_confirmations, set_pref
from grid_savegame import get_state
from grid_announce import _funds_phrase, announce
from grid_runs import _start_new_run, _tell_footer_seed, finish_run
from grid_fleet import set_fleet_sort
from grid_runsetup import START_OPTION_NONE
from grid_slots import _attach, _load_slot_name, _selected_slot, _store_run_in_slot, _write_slots, load_slots
from grid_gridley import OPERATOR_RANKS, unlocked_rank_themes
from grid_callouts import _confirm_dialog_ask
from grid_careerpanel import _copy_to_clipboard, export_career_to_field, import_career_from_text, reset_career
from grid_renderer import render
from grid_loading import load_state


def on_reset_prefs(event=None):
    reset_prefs()
    render()


def _make_pref_checkbox_handler(key):
    def handler(event=None):
        target = getattr(event, "target", None)
        checked = getattr(target, "checked", None)
        set_pref(key, (not runstate.prefs[key]) if checked is None else bool(checked))
        render()
    return handler


def _make_pref_select_handler(key):
    def handler(event=None):
        target = getattr(event, "target", None)
        set_pref(key, getattr(target, "value", None))
        render()
    return handler


def start_todays_run(seed_text):
    """Z-5c: the "Today's run" button (shared/seed.js) hands over the UTC date's shared seed. It becomes this run's seed only
    while nothing has been built or advanced, exactly like the "Use a seed" box, and never in the sandbox. A run already under
    way is left alone (the button says how to start a fresh one), so nothing is lost. Returns the sentence to show."""
    result = seed_lib.validate(seed_text, SEED_GAME)
    if not result["ok"]:
        return result["message"]
    if runstate.sandbox_active:
        return "Today's run does not count in the sandbox. Switch the sandbox off, then press the button again."
    if not runstate.state.unstarted():
        _tell_footer_seed()
        return ("Today's run starts a fresh run, and this one is under way. Nothing was changed. "
                "Finish it first (Career, Finish run), then press the button again.")
    runstate.state.set_seed(result["seed"])
    render()
    _tell_footer_seed()
    return f"Today's run is set: seed {runstate.state.seed}. Build and advance as usual; finishing the run (Career, Finish run) counts it for today."


def _make_fleet_sort_handler(key):
    def handler(event=None):
        set_fleet_sort(key)
        render()
    return handler


def on_reset_confirmations(event=None):
    count = reset_skipped_confirmations()
    runstate.confirm_reset_message = (
        f"Done: {count} question(s) will be asked again." if count else "Nothing was switched off, so nothing changed."
    )
    announce(runstate.confirm_reset_message)
    render()
    runstate.confirm_reset_message = ""


def _slot_say(text):
    runstate.slot_message = text
    render()
    announce(text)


def slot_save_here(index, name=None):
    """Saves the live run into a slot and attaches to it."""
    if runstate.sandbox_active:
        _slot_say("Leave the practice sandbox first: slots keep your real runs.")
        return False
    error = _store_run_in_slot(index, name)
    if error:
        _slot_say(error)
        return False
    _attach(index)
    _slot_say(f"Saved this run to slot {index + 1} ({_load_slot_name(index)}). It now saves itself after every round.")
    return True


def slot_switch_to(index):
    """Loads a slot: the current run goes into its own slot first (or asks, if it is in none)."""
    if runstate.sandbox_active:
        _slot_say("Leave the practice sandbox first: slots keep your real runs.")
        return False
    slot = load_slots()[index]
    if slot is None:
        _slot_say(f"Slot {index + 1} is empty. Use Save here to put this run in it, or New run here.")
        return False

    def go():
        if runstate.slot_attached is not None and runstate.slot_attached != index:
            error = _store_run_in_slot(runstate.slot_attached)
            if error:
                _slot_say(error + " Nothing was switched.")
                return
        backup = json.loads(json.dumps(get_state()))
        try:
            load_state(json.loads(json.dumps(slot["state"])))
        except Exception:  # noqa: BLE001 -- a slot with damaged contents must never break the run on screen
            load_state(backup)
            _slot_say(f"Slot {index + 1} could not be read, so this run was left as it was.")
            return
        _attach(index)
        _slot_say(f"Loaded slot {index + 1}: {slot['name']}.")

    if runstate.slot_attached is None and not runstate.state.unstarted():
        _confirm_dialog_ask(
            "grid-slot-switch",
            "This run is not saved in any slot and loading the slot will replace it. Save it to a slot first if you want to keep it.",
            "Replace this run", go, allow_skip=False,
        )
    else:
        go()
    return True


def slot_new_run(index, name=None):
    """Starts a fresh run in a slot (the current run is saved into its own slot first, or asked about)."""
    if runstate.sandbox_active:
        _slot_say("Leave the practice sandbox first: slots keep your real runs.")
        return False
    existing = load_slots()[index]

    def go():
        if runstate.slot_attached is not None and runstate.slot_attached != index:
            error = _store_run_in_slot(runstate.slot_attached)
            if error:
                _slot_say(error + " Nothing was switched.")
                return
        _start_new_run()
        error = _store_run_in_slot(index, name)
        if error:
            _slot_say(error)
            return
        _attach(index)
        _slot_say(f"Started a new run in slot {index + 1} ({_load_slot_name(index)}).")

    if existing is not None:
        _confirm_dialog_ask(
            "grid-slot-new",
            f"Slot {index + 1} already holds {existing['name']}. Starting a new run in it replaces that run.",
            "Replace the slot", go, allow_skip=False,
        )
    elif runstate.slot_attached is None and not runstate.state.unstarted():
        _confirm_dialog_ask(
            "grid-slot-new-unsaved",
            "This run is not saved in any slot and a new run will replace it. Save it to a slot first if you want to keep it.",
            "Start new run", go, allow_skip=False,
        )
    else:
        go()
    return True


def slot_clear(index):
    slots = load_slots()
    if slots[index] is None:
        _slot_say(f"Slot {index + 1} is already empty.")
        return False

    def go():
        slots[index] = None
        _write_slots(slots)
        if runstate.slot_attached == index:
            runstate.slot_attached = None
        _slot_say(f"Cleared slot {index + 1}. The run on screen was not touched.")

    _confirm_dialog_ask(
        "grid-slot-clear", f"Clear slot {index + 1} ({slots[index]['name']}) for good?", "Clear slot", go, allow_skip=False
    )
    return True


def on_slot_save(event=None):
    index = _selected_slot()
    existing = load_slots()[index]
    name = getattr(document.getElementById("slot-name-input"), "value", "")
    if existing is not None and runstate.slot_attached != index:
        _confirm_dialog_ask(
            "grid-slot-save",
            f"Slot {index + 1} already holds {existing['name']}. Saving here replaces that run.",
            "Replace the slot", lambda: slot_save_here(index, name), allow_skip=False,
        )
    else:
        slot_save_here(index, name)


def on_slot_load(event=None):
    index = _selected_slot()
    slot = load_slots()[index]
    if slot is not None and runstate.slot_attached == index and json.dumps(slot["state"], sort_keys=True) != json.dumps(get_state(), sort_keys=True):
        _confirm_dialog_ask(
            "grid-slot-reload",
            f"Slot {index + 1} was last saved before the changes made this round. Loading it undoes those changes.",
            "Load the slot", lambda: slot_switch_to(index), allow_skip=False,
        )
        return
    slot_switch_to(index)


def on_slot_new(event=None):
    slot_new_run(_selected_slot(), getattr(document.getElementById("slot-name-input"), "value", ""))


def on_slot_clear(event=None):
    slot_clear(_selected_slot())


def on_slot_select(event=None):
    render()


def on_rank_theme_change(event=None):
    target = getattr(event, "target", None)
    choice = getattr(target, "value", None)
    if choice not in RANK_THEMES:
        return
    if choice not in unlocked_rank_themes():
        needed = OPERATOR_RANKS[RANK_THEMES.index(choice)][1]
        runstate.rank_theme_message = f"The {choice} theme unlocks at the rank {needed}."
    else:
        runstate.rank_theme_message = ""
        set_pref("rank_theme", choice)
    render()


def on_toggle_career(event=None):
    runstate.career_open = not runstate.career_open
    render()


def on_finish_run(event=None):
    def do_finish():
        finish_run()
        render()

    if runstate.sandbox_active or runstate.state.round_number - 1 < CAREER_MIN_ROUNDS:
        return
    points, _ = run_career_points()
    _confirm_dialog_ask(
        action_id="grid-finish-run",
        message=(
            f"Finish this run and bank {points} career point(s)? "
            "Your grid resets to a fresh start; career points, unlocked perks and earned achievements stay."
        ),
        confirm_label="Finish run",
        on_confirm=do_finish,
    )


def on_start_option_change(event=None):
    value = document.getElementById("start-option-select").value
    option = None if value in (START_OPTION_NONE, "", None) else value
    if set_loadout(option):
        runstate.run_setup_message = ""
    else:
        runstate.run_setup_message = "That loadout is not available."
    render()


def on_apply_run_seed(event=None):
    text = document.getElementById("run-seed-input").value or ""
    result = seed_lib.validate(text, SEED_GAME)
    if not result["ok"]:
        runstate.run_setup_message = result["message"]
    elif not runstate.state.set_seed(result["seed"]):
        runstate.run_setup_message = "The seed can only be changed before you build or advance a round."
    else:
        runstate.run_setup_message = f"Seed {runstate.state.seed} set."
    render()


def on_copy_run_seed(event=None):
    """Z-1a: copy the run's seed so it can be shared; the note says so (or shows it to copy by hand)."""
    if _copy_to_clipboard(runstate.state.seed):
        runstate.run_setup_message = f"Copied {runstate.state.seed}."
    else:
        runstate.run_setup_message = f"Your browser would not copy it. The seed is {runstate.state.seed}: select it above and copy it."
    render()


def on_toggle_ironman(event=None):
    if runstate.state.set_ironman(not runstate.state.ironman):
        runstate.run_setup_message = (
            "Ironman on: no undo, every action is final." if runstate.state.ironman else "Ironman off."
        )
    else:
        runstate.run_setup_message = "Ironman can only be switched before you build or advance a round."
    render()


def on_undo_build(event=None):
    if runstate.state.can_undo_build():
        record = runstate.state.undo_record
        last = runstate.shadow_actions[-1] if runstate.shadow_actions else None
        if last is not None and last.get("kind") == "build" and last.get("type") == record["plant"] \
                and last.get("round") == record["round"]:
            runstate.shadow_actions.pop()
    record = runstate.state.undo_record
    if runstate.state.undo_last_build():
        announce(
            f"Took back the {PLANT_LABEL[record['plant']]} build. Refunded {record['cost']:.0f}. {_funds_phrase()}"
        )
    else:
        announce("Nothing to undo: only the last build this round can be taken back")
    render()


def on_accept_grant(event=None):
    if runstate.state.accept_grant():
        announce(runstate.state.last_grant_message)
    render()


def on_decline_grant(event=None):
    if runstate.state.decline_grant():
        announce(runstate.state.last_grant_message)
    render()


def on_peek_forecast(event=None):
    runstate.state.buy_peek()
    render()


def on_export_career(event=None):
    export_career_to_field()
    render()


def on_import_career(event=None):
    text = document.getElementById("career-data-field").value or ""

    def do_import():
        import_career_from_text(text)
        render()

    _confirm_dialog_ask(
        action_id="grid-import-career",
        message="Replace your whole career (points, perks, records and run history) with the pasted data?",
        confirm_label="Replace career",
        on_confirm=do_import,
        allow_skip=False,
    )


def on_reset_career(event=None):
    # Offer the backup first: the JSON goes into the box (and the clipboard)
    # before the question is asked, so it is there whatever the answer is.
    export_career_to_field()

    def do_reset():
        reset_career()
        render()

    _confirm_dialog_ask(
        action_id="grid-reset-career",
        message=(
            "Reset your whole career? Points, perks, records, run history and banked achievements are erased. "
            "A copy of the current career has just been copied or placed in the box so you can restore it later."
        ),
        confirm_label="Reset career",
        on_confirm=do_reset,
        allow_skip=False,
    )
    render()
