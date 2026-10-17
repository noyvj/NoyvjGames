"""Click handlers for playing: build, retire, maintain, plant keys, advance and auto-advance, arbitrage, scenarios,
policies, shadow and real-grid pickers, difficulty, and the sandbox (enter, leave, sliders).
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document

import grid_runstate as runstate
from grid_rules import ARBITRAGE_MODES, PLANT_LABEL, SCENARIO_ORDER
from grid_sandbox_state import SANDBOX_BALANCE_DEFAULTS, new_sandbox_state
from grid_shadow import record_shadow_action, set_shadow_scenario
from grid_savegame import get_state
from grid_announce import _check_new_achievements_for_toast, _funds_phrase, announce, round_announcement_text
from grid_difficulty import DIFFICULTY_PRESETS, apply_difficulty_preset
from grid_sandbox import _SANDBOX_STASHED, _sandbox_fresh_globals, _sandbox_restore_real
from grid_realgrid import set_real_grid
from grid_slots import autosave_slot
from grid_callouts import (
    _check_disruption_toast, _check_renewable_milestone, _confirm_dialog_ask, _control_kind,
    _play_demolition_puff, plant_key_command,
)
from grid_advance import _play_round_animation, auto_advance
from grid_renderer import render


def on_cycle_arbitrage_mode(event=None):
    """C9: cycle Idle -> Charge -> Discharge for the next round."""
    modes = ARBITRAGE_MODES
    runstate.state.set_arbitrage_mode(modes[(modes.index(runstate.state.arbitrage_mode) + 1) % len(modes)])
    render()


def _make_build_handler(plant_type):
    def handler(event=None):
        cost = runstate.state.plant_cost(plant_type)
        funds_before = runstate.state.funds
        if runstate.state.build_plant(plant_type):
            record_shadow_action("build", plant_type)
            announce(
                f"Built a {PLANT_LABEL[plant_type]} plant, {runstate.state.plant_name_list(plant_type)[-1]}. "
                f"{runstate.state.plant_counts[plant_type]} {PLANT_LABEL[plant_type]} standing. {_funds_phrase()}"
            )
        else:
            announce(
                f"Cannot build {PLANT_LABEL[plant_type]}: it costs {cost:.0f} and you have {funds_before:.0f}"
            )
        reached_before = runstate.state.renewable_50_reached
        _check_renewable_milestone()
        if runstate.state.renewable_50_reached and not reached_before:
            announce("More than half your grid's capacity is now renewable")
        render()
        _check_new_achievements_for_toast()
    return handler


def on_cycle_scenario(event=None):
    """C13: cycle to the next starting scenario (only before any build)."""
    next_id = SCENARIO_ORDER[(SCENARIO_ORDER.index(runstate.state.scenario) + 1) % len(SCENARIO_ORDER)]
    if runstate.sandbox_active:  # Z-18: any time; the practice grid starts over on the new scenario
        runstate.state = new_sandbox_state(next_id, runstate.state.balance)
    else:
        runstate.state.apply_scenario(next_id)
    render()


def on_dismiss_renewable_milestone(event=None):
    runstate.renewable_milestone_visible = False
    render()


def _make_retire_handler(plant_type):
    def do_retire():
        eulogy_before = runstate.state.last_eulogy
        funds_before = runstate.state.funds
        succeeded = runstate.state.retire_plant(plant_type)
        if succeeded:
            record_shadow_action("retire", plant_type)
            announce(
                f"Retired a {PLANT_LABEL[plant_type]} plant. {runstate.state.plant_counts[plant_type]} "
                f"{PLANT_LABEL[plant_type]} standing. Refund {runstate.state.funds - funds_before:.0f}. {_funds_phrase()}"
            )
        else:
            announce(f"Cannot retire {PLANT_LABEL[plant_type]}: none are standing")
        if succeeded and runstate.state.last_eulogy is not eulogy_before:
            _play_demolition_puff()
        if succeeded and not runstate.state.seen_retire_callout:
            runstate.state.seen_retire_callout = True
            runstate.retire_callout_visible = True
        _check_renewable_milestone()
        render()
        _check_new_achievements_for_toast()

    def handler(event=None):
        # C14 (planning/TODO.md's shared confirmation-dialog goal) --
        # retiring a plant type's very last unit is a real, not-quite-free
        # decision (refund_plant() only rebates REFUND_FRACTION of the
        # current cost -- rebuilding costs full price again), so that one
        # case alone is gated behind the shared confirm dialog. Retiring
        # down from 2+ units stays exactly as instant as it always was.
        if runstate.state.plant_counts[plant_type] <= 0:
            do_retire()  # already 0 -- retire_plant() is a no-op; let it report False as usual
            return
        if runstate.state.plant_counts[plant_type] == 1:
            _confirm_dialog_ask(
                action_id=f"grid-retire-last-{plant_type}",
                message=(
                    f"Retire your last {PLANT_LABEL[plant_type]} plant "
                    f"(wear {runstate.state.wear_percent(plant_type)}%, average age {runstate.state.plant_age[plant_type]:.1f} rounds)? "
                    "You'll lose that capacity, and rebuilding later costs "
                    "full price again."
                ),
                confirm_label="Retire it",
                on_confirm=do_retire,
            )
        else:
            do_retire()
    return handler


def _make_plant_key_handler(plant_type):
    def handler(event=None):
        if event is None:
            return
        target = getattr(event, "target", None)
        target_id = getattr(target, "id", "") or ""
        command = plant_key_command(
            getattr(event, "key", ""), plant_type, target_id, getattr(target, "tagName", ""),
            bool(getattr(event, "ctrlKey", False)), bool(getattr(event, "altKey", False)), bool(getattr(event, "metaKey", False)),
        )
        if command is None:
            return
        prevent = getattr(event, "preventDefault", None)
        if prevent is not None:
            prevent()
        action, plant = command
        if action in ("build", "retire") and getattr(event, "repeat", False):
            return  # a held key must not spend funds round after round
        if action == "build":
            _make_build_handler(plant)(None)
        elif action == "retire":
            _make_retire_handler(plant)(None)
        else:
            focus = getattr(document.getElementById(f"{plant}-{_control_kind(target_id)}-button"), "focus", None)
            if focus is not None:
                focus()
    return handler


def _make_maintain_handler(plant_type):
    def handler(event=None):
        succeeded = runstate.state.maintain_plant(plant_type)
        if succeeded:
            announce(
                f"Maintained the {PLANT_LABEL[plant_type]} fleet. Wear now {runstate.state.wear_percent(plant_type)}%. "
                f"{_funds_phrase()}"
            )
        elif runstate.state.plant_counts[plant_type] <= 0:
            announce(f"Cannot maintain {PLANT_LABEL[plant_type]}: none are standing")
        else:
            announce(
                f"Cannot maintain {PLANT_LABEL[plant_type]}: it costs {runstate.state.maintenance_cost(plant_type):.0f} "
                f"and you have {runstate.state.funds:.0f}"
            )
        if succeeded and not runstate.state.seen_maintain_callout:
            runstate.state.seen_maintain_callout = True
            runstate.maintain_callout_visible = True
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_maintenance_schedule_handler(plant_type):
    """TODO-C23: the per-plant-type auto-maintain cadence <select>'s own
    change handler -- reads the just-changed value straight off the
    event's target, same convention as on_grid_size_change() elsewhere in
    this file."""
    def handler(event):
        runstate.state.set_maintenance_schedule(plant_type, int(event.target.value))
        render()
    return handler


def on_dismiss_retire_callout(event=None):
    runstate.retire_callout_visible = False
    render()


def on_dismiss_maintain_callout(event=None):
    runstate.maintain_callout_visible = False
    render()


def on_toggle_steeper_demand(event=None):
    runstate.state.steeper_demand_growth_enabled = not runstate.state.steeper_demand_growth_enabled
    render()


def on_toggle_weather_variability(event=None):
    runstate.state.weather_variability_enabled = not runstate.state.weather_variability_enabled
    render()


def on_invest_demand_response(event=None):
    """TODO-C7: the demand-response lever's own button click."""
    cost = runstate.state.demand_response_cost()
    if runstate.state.invest_demand_response():
        announce(
            f"Invested in demand response, level {runstate.state.demand_response_level}. Demand now grows by "
            f"{runstate.state.demand_growth_this_round():g} a round. {_funds_phrase()}"
        )
    else:
        announce(f"Cannot invest in demand response: it costs {cost:.0f} and you have {runstate.state.funds:.0f}")
    render()


def on_enact_carbon_pricing(event=None):
    """TODO-C19: accept the currently-offered policy lever as carbon pricing."""
    if runstate.state.enact_policy("carbon_pricing"):
        announce(f"Carbon pricing enacted: fossil plants cost more to build for {runstate.state.active_policy['rounds_remaining']} rounds")
    else:
        announce("No policy lever is on offer right now")
    render()


def on_enact_renewable_subsidy(event=None):
    """TODO-C19: accept the currently-offered policy lever as a renewable subsidy."""
    if runstate.state.enact_policy("renewable_subsidy"):
        announce(f"Renewable subsidy enacted: renewable plants cost less to build for {runstate.state.active_policy['rounds_remaining']} rounds")
    else:
        announce("No policy lever is on offer right now")
    render()


def on_decline_policy(event=None):
    """TODO-C19: turn down the currently-offered policy lever entirely."""
    if runstate.state.decline_policy():
        announce("Policy lever declined")
    else:
        announce("No policy lever is on offer right now")
    render()


def on_shadow_change(event=None):
    value = document.getElementById("shadow-select").value
    set_shadow_scenario(None if value == "off" else value)
    render()


def on_real_grid_change(event=None):
    value = document.getElementById("real-grid-select").value
    set_real_grid(None if value == "off" else value)
    render()


def on_connect_regional_grid(event=None):
    if runstate.state.regional_grid_connected:
        return
    runstate.state.connect_regional_grid()
    render()


def on_advance_round(event=None):
    runstate.auto_advance_message = ""
    runstate.last_finish_records = []
    reached_before = runstate.state.renewable_50_reached
    runstate.state.advance_round()
    _check_renewable_milestone()
    render()
    autosave_slot()
    _play_round_animation()
    announce(round_announcement_text(milestone_new=runstate.state.renewable_50_reached and not reached_before))
    _check_disruption_toast()
    _check_new_achievements_for_toast()


def on_auto_advance(event=None):
    runstate.last_finish_records = []
    reached_before = runstate.state.renewable_50_reached
    played, message = auto_advance()
    runstate.auto_advance_message = message
    if played:
        render()
        autosave_slot()
        _play_round_animation()
        announce(message)
        announce(round_announcement_text(milestone_new=runstate.state.renewable_50_reached and not reached_before))
        _check_disruption_toast()
        _check_new_achievements_for_toast()
    else:
        render()
        announce(message)


def on_difficulty_preset_change(event=None):
    key = getattr(getattr(event, "target", None), "value", None)
    if key not in DIFFICULTY_PRESETS:
        render()
        return
    applied = apply_difficulty_preset(key)
    runstate.difficulty_note = (
        "" if applied
        else "The starting scenario is locked once you build or advance, so only the toggles changed."
    )
    render()


def _make_sandbox_balance_handler(key):
    def handler(event=None):
        if not runstate.sandbox_active:
            return
        target = getattr(event, "target", None)
        runstate.state.set_balance(key, getattr(target, "value", None))
        render()
    return handler


def on_sandbox_balance_reset(event=None):
    if not runstate.sandbox_active:
        return
    for key, value in SANDBOX_BALANCE_DEFAULTS.items():
        runstate.state.set_balance(key, value)
    render()


def sandbox_enter():
    """Sets the real game aside and starts a practice grid. True when the sandbox is on."""
    if runstate.sandbox_active:
        return True
    snapshot = get_state()
    runstate._sandbox_real = {
        "state": runstate.state,
        "snapshot": snapshot,
        "earned": list(snapshot["achievements_earned"]),
        "globals": {name: vars(runstate)[name] for name in _SANDBOX_STASHED},
    }
    runstate.sandbox_active = True
    runstate.state = new_sandbox_state("standard")
    vars(runstate).update(_sandbox_fresh_globals())
    render()
    return True


def sandbox_leave():
    """Leaves the sandbox; the real game is back and untouched. True when it is."""
    if not runstate.sandbox_active:
        return True
    _sandbox_restore_real()
    render()
    return True
