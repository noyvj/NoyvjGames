"""Click handlers for levels, vault, expedition, survey commit, wildfire and rival."""

import seed as seed_lib

import canopy_runstate as runstate
from canopy_expedition import (
    EXPEDITION_SEASONS, SEED_GAME, _rebuild_expedition_terrain, _save_expedition_meta, _tell_footer_seed,
    expedition_best_for, expedition_finished, expedition_season, new_expedition_seed,
)
from canopy_handlers_core import cancel_survey, enter_survey_mode, on_clear, on_replant, queue_survey_action
from canopy_handlers_panels import decline_stakeholder_request
from canopy_hazards import (
    FIRE_DAMPEN_COOLDOWN, FIRE_DAMP_TICKS, can_buy_out, can_dampen, can_lock, easement_cost, fire_damp,
    fires,
)
from canopy_helpers import _el, _log_event, _plot_ref
from canopy_levels import (
    LEVEL_SPECS, _js_window, _reset_level_run, drive_off_poacher, level_lock_reason, next_level_id,
)
from canopy_renderer import render, render_expedition, render_vault, reset_session, start_level
from canopy_rules import DIFFICULTY_NORMAL, SCENARIO_NONE, expedition_meta
from canopy_session import _confirm_dialog_ask
from canopy_survey import _leave_survey_mode, survey_queue
from canopy_valuation import standing_forest_value
from canopy_worldvars import CHALLENGE_NONE, PACE_NORMAL, RIVAL_BUYOUT_COST, rival_claims, rival_locked


def on_leave_level(event=None):
    """Back to free play: the forest stays as it is, the level's rules and goal stop."""
    if runstate.current_level is None:
        return False
    title = LEVEL_SPECS[runstate.current_level]["title"]
    runstate.current_level = None
    _reset_level_run(reset_crews=False)
    _log_event("level", f"Left {title}: free play", None)
    render()
    return True


def on_next_level(event=None):
    """GN-3: from a finished level straight into the next one (only when this level is done and the next is unlocked)."""
    next_id = next_level_id()
    if next_id is None or runstate.level_done_tick is None or level_lock_reason(next_id):
        return False
    return start_level(next_id)


def hotkey_drive_off_poacher(event=None):
    if drive_off_poacher():
        render()
        return True
    return False


def on_toggle_vault(event=None):
    runstate.vault_open = not runstate.vault_open
    render_vault()


def start_expedition(seed_text=None):
    """Starts an Expedition on a seed (a fresh one when none is given): a new forest with the seed's map. Returns the
    seed, or None when the text is not a valid Canopy seed (the panel says why)."""
    if seed_text is None or not str(seed_text).strip():
        seed_text = new_expedition_seed()
    check = seed_lib.validate(str(seed_text), SEED_GAME)
    if not check["ok"]:
        runstate._expedition_message = check["message"]
        render_expedition()
        return None
    seed_text = check["seed"]
    started = reset_session(
        grid_size="normal", difficulty=DIFFICULTY_NORMAL, challenge=CHALLENGE_NONE, pace=PACE_NORMAL,
        scenario=SCENARIO_NONE, level=None, layout=None, expedition=seed_text, _render_after=False,
    )
    if not started:
        return None
    expedition_meta["last_seed"] = seed_text
    _save_expedition_meta()
    runstate._expedition_message = ""
    best = expedition_best_for(seed_text)
    _log_event("expedition", f"Expedition {seed_text} started: {EXPEDITION_SEASONS} seasons" + (f" (your best here: {best})" if best is not None else ""), None)
    render()
    return seed_text


def on_leave_expedition(event=None):
    """Back to normal play: the forest stays exactly as it is, the map's terrain and the upgrades stop."""
    if runstate.current_expedition is None:
        return False
    seed_text = runstate.current_expedition["seed"]
    runstate.current_expedition = None
    _rebuild_expedition_terrain()
    _log_event("expedition", f"Left Expedition {seed_text}: normal play on the same forest", None)
    render()
    return True


def on_toggle_expedition(event=None):
    runstate.expedition_open = not runstate.expedition_open
    render_expedition()


def on_expedition_new_seed(event=None):
    field = _el("expedition-seed-input")
    seed_text = new_expedition_seed()
    if field is not None:
        field.value = seed_text
    runstate._expedition_message = f"New seed {seed_text}. Press Start Expedition to play it."
    render_expedition()


def on_expedition_copy(event=None):
    field = _el("expedition-seed-input")
    text = runstate.current_expedition["seed"] if runstate.current_expedition is not None else (getattr(field, "value", "") if field is not None else "")
    window = _js_window()
    clipboard = getattr(getattr(window, "navigator", None), "clipboard", None) if window is not None else None
    copied = False
    if clipboard is not None and text:
        try:
            clipboard.writeText(text)
            copied = True
        except Exception:  # noqa: BLE001 -- a blocked clipboard just means the player copies by hand
            copied = False
    runstate._expedition_message = f"Copied {text}." if copied else (f"Seed: {text} (select it and copy by hand)." if text else "No seed to copy yet.")
    render_expedition()


def on_expedition_start(event=None):
    """Start Expedition: reads the seed box (an empty box means a fresh seed), asks first when a forest would be given up."""
    field = _el("expedition-seed-input")
    raw = getattr(field, "value", "") if field is not None else ""
    if raw and str(raw).strip():
        check = seed_lib.validate(str(raw), SEED_GAME)
        if not check["ok"]:
            runstate._expedition_message = check["message"]
            render_expedition()
            return
        seed_text = check["seed"]
    else:
        seed_text = new_expedition_seed()
    if field is not None:
        field.value = seed_text
    if standing_forest_value() <= 0 and runstate.total_income <= 0:
        start_expedition(seed_text)
        return
    _confirm_dialog_ask(
        "canopy-expedition-start",
        f"Start Expedition {seed_text}? It begins a new forest, so you will give up {standing_forest_value():.1f} standing value"
        f" and {runstate.total_income:.1f} income. Saves you have already made are not touched, and you can leave the Expedition for normal play at any time.",
        "Start Expedition",
        lambda: start_expedition(seed_text),
    )


def start_todays_run(seed_text):
    """Z-5c: the "Today's run" button (shared/seed.js, inside the Expedition panel) hands over the UTC date's shared seed. Today's
    run is an Expedition on that seed: the same map for everyone that day. It asks first (the usual Expedition question) when a
    forest would be given up, does nothing when this very run is already under way, and never touches a save. Returns the
    sentence shown in the panel."""
    check = seed_lib.validate(str(seed_text or ""), SEED_GAME)
    if not check["ok"]:
        runstate._expedition_message = check["message"]
        _tell_footer_seed()
        render_expedition()
        return runstate._expedition_message
    seed_text = check["seed"]
    if runstate.current_expedition is not None and runstate.current_expedition["seed"] == seed_text and not expedition_finished():
        runstate._expedition_message = f"You are already playing today's run (season {expedition_season()} of {EXPEDITION_SEASONS}). Nothing was changed."
        _tell_footer_seed()
        render_expedition()
        return runstate._expedition_message

    def begin():
        if start_expedition(seed_text) is None:
            runstate._expedition_message = "Today's run could not start. Nothing was changed."
        else:
            runstate._expedition_message = (
                f"Today's run is on: Expedition {seed_text}, {EXPEDITION_SEASONS} seasons on the day's shared map, the same for everyone today. "
                "Finishing it counts for today."
            )
        _tell_footer_seed()
        render_expedition()

    if standing_forest_value() <= 0 and runstate.total_income <= 0:
        begin()
        return runstate._expedition_message
    runstate._expedition_message = "Nothing has changed yet: confirm the question to start today's run, or cancel to keep your forest as it is."
    _tell_footer_seed()
    render_expedition()
    _confirm_dialog_ask(
        "canopy-todays-run",
        f"Start today's run (Expedition {seed_text})? It begins a new forest, so you will give up {standing_forest_value():.1f} standing value"
        f" and {runstate.total_income:.1f} income. Saves you have already made are not touched, and you can leave the Expedition for normal play at any time.",
        "Start today's run",
        begin,
    )
    return runstate._expedition_message


def commit_survey(event=None):
    """Runs the plan in order through the ordinary handlers, then lets time run again."""
    plan = list(survey_queue)
    previous_selection = runstate.selected_index
    _leave_survey_mode()
    for item in plan:
        if item["kind"] == "decline":
            decline_stakeholder_request()
            continue
        runstate.selected_index = item["plot"]
        (on_clear if item["kind"] == "clear" else on_replant)()
    if previous_selection is not None and previous_selection < len(runstate.plots):
        runstate.selected_index = previous_selection
    render()
    return len(plan)


def on_toggle_survey(event=None):
    if runstate.survey_mode:
        cancel_survey()
    else:
        enter_survey_mode()


def on_survey_decline(event=None):
    queue_survey_action("decline")


def on_survey_remove_last(event=None):
    if survey_queue:
        survey_queue.pop()
        render()


def dampen_plot(index=None):
    """Puts out a fire (or the smoking plot's coming spark) and shields that plot for FIRE_DAMP_TICKS."""
    index = runstate.selected_index if index is None else index
    if not can_dampen(index):
        return False
    fires.pop(index, None)
    if runstate.fire_warning is not None and runstate.fire_warning["plot"] == index:
        runstate.fire_warning = None
    fire_damp[index] = FIRE_DAMP_TICKS
    runstate.dampen_cooldown = FIRE_DAMPEN_COOLDOWN
    _log_event("fire", f"Dampened {_plot_ref(index)}: it is safe for {FIRE_DAMP_TICKS} ticks", index)
    render()
    return True


def on_dampen(event=None):
    dampen_plot()


def lock_easement(index=None):
    """Pays for a conservation easement on `index` (default: the plot Halloran has bid on, else the selected plot)."""
    if index is None:
        index = runstate.rival_notice["plot"] if runstate.rival_notice is not None else runstate.selected_index
    if not can_lock(index):
        return False
    cost = easement_cost(index)
    runstate.total_income -= cost
    rival_locked.add(index)
    if runstate.rival_notice is not None and runstate.rival_notice["plot"] == index:
        runstate.rival_notice = None
    _log_event("rival", f"Locked {_plot_ref(index)} with a conservation easement for {cost:.1f}: it can never be claimed", index)
    render()
    return True


def buy_out_claim(index=None):
    index = runstate.selected_index if index is None else index
    if not can_buy_out(index):
        return False
    runstate.total_income -= RIVAL_BUYOUT_COST
    del rival_claims[index]
    _log_event("rival", f"Bought out the mining claim on {_plot_ref(index)}: it is free to replant", index)
    render()
    return True


def on_rival_lock(event=None):
    lock_easement()


def on_rival_buyout(event=None):
    buy_out_claim()
