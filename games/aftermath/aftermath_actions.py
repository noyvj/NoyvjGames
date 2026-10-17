"""Actions that replace the running game and redraw: new run, challenge and daily starts, custom runs, the second founding, community resilience."""

import json

import run_code as shared_run_code
from js import document, localStorage

import aftermath_runstate as runstate
from aftermath_achievements import _check_new_achievements_for_toast
from aftermath_bonuses import COMMUNITY_RESILIENCE_CACHE_KEY, _community_value, founding_star_resources
from aftermath_challenges import (
    RUN_CODE_GAME, _challenge_info, _custom_named, _reset_run_ui_state, challenge_spec, daily_run_code,
    daily_seed_of_code, run_is_untouched,
)
from aftermath_chronicle import chronicle_note, founding_ready, founding_refund_total
from aftermath_model_run import RunState
from aftermath_persist import FOUNDING_MAX_STARS, _el, _now, save_meta
from aftermath_renderer import render
from aftermath_rules import DEFAULT_SCENARIO, SCENARIOS
from aftermath_runview import announce


def set_community_resilience(mean):
    """Called by the page with the community mean of skill_tree_strength once the stats summary has
    answered (a number), or with None when the summary has no usable figure (too few players, field not
    listed). Anything else counts as no figure. Keeps the last good figure in this browser so the next
    visit (including an offline or "reduce data" one) agrees with it. Returns True when a figure is kept."""
    value = _community_value(mean)
    runstate.community_resilience = value
    if value is None:
        try:
            localStorage.removeItem(COMMUNITY_RESILIENCE_CACHE_KEY)
        except Exception:
            pass
    else:
        try:  # not _storage_write: a cached figure is not player progress, so it must not touch the "Saved" badge
            localStorage.setItem(COMMUNITY_RESILIENCE_CACHE_KEY, json.dumps({"mean": value, "at": _now()}))
        except Exception:
            pass
    if runstate.run is not None:
        render()
    return value is not None


def challenge_run_from_code(code):
    """(RunState, error) for a pasted code; the run is NOT installed."""
    decoded = shared_run_code.decode(code, RUN_CODE_GAME)
    spec, error = challenge_spec(decoded)
    if spec is None:
        return None, error
    state = RunState(
        run_number=max(1, runstate.highest_awarded_run),
        extended=spec["extended"],
        scenario=spec["scenario"],
        normalised=True,
        draw=spec["draw"],
        custom_events=spec["custom_events"],
        custom_name="Friend's schedule" if spec["custom_events"] else None,
        challenge=_challenge_info(decoded),
    )
    return state, ""


def start_challenge(code):
    """Plays a friend's run code as a challenge run. Only between runs (a finished run or one with
    no event faced yet), so nothing in progress is ever thrown away. Returns the message shown."""
    if not (runstate.run.is_complete() or runstate.run.event_index == 0):
        message = "Finish your current run first (or save it with the Save button), then play the challenge."
    else:
        state, error = challenge_run_from_code(code)
        if state is None:
            message = error
        else:
            runstate.run = state
            _reset_run_ui_state()
            message = (
                f"Challenge started: {len(runstate.run.schedule)} events, your skills and memory are switched off, "
                "no knowledge is earned."
            )
    runstate.challenge_status_text = message
    render()
    announce(message)
    return message


def start_todays_run(seed_text):
    """Z-5c: the "Today's run" button (shared/seed.js) hands over the UTC date's shared seed. It starts a challenge-style run on
    the classic schedule at that seed (your skill tree and memory switched off, so everyone faces the same numbers), but only
    between runs: a run under way is never replaced. Returns the sentence shown."""
    if not (runstate.run.is_complete() or run_is_untouched()):
        message = (
            "Today's run starts a fresh settlement, and this run is under way. Nothing was changed. "
            "Finish your current run first (or save it with the Save button), then press the button again."
        )
    else:
        code, error = daily_run_code(seed_text)
        state, error = challenge_run_from_code(code) if code else (None, error)
        if state is None:
            message = error
        else:
            state.challenge["daily_seed"] = daily_seed_of_code(code)
            runstate.run = state
            _reset_run_ui_state()
            runstate.challenge_status_text = ""  # the sentence below is shown beside the button, not repeated under the challenge stats
            message = (
                f"Today's run started: the classic schedule, {len(runstate.run.schedule)} events, the same for everyone today. "
                "Your skills and memory are switched off and no knowledge is earned; finishing it counts for today."
            )
    render()
    announce(message)
    return message


def leave_challenge(event=None):
    """Drops an unfinished challenge and starts the next normal run."""
    if not runstate.run.normalised:
        return
    extended = _el("extended-run-toggle")
    scenario = _el("scenario-select")
    runstate.run = RunState(
        run_number=runstate.highest_awarded_run + 1,
        extended=bool(extended.checked) if extended is not None else False,
        scenario=scenario.value if scenario is not None and scenario.value in SCENARIOS else DEFAULT_SCENARIO,
    )
    _reset_run_ui_state()
    runstate.challenge_status_text = "Left the challenge: back to your own settlement."
    render()


def start_custom_run(name):
    """Runs a saved schedule as a normal run (your tree applies; it is tagged 'custom schedule'),
    only between runs. Returns the message shown."""
    entry = _custom_named(name)
    if entry is None:
        return "That schedule no longer exists."
    if not (runstate.run.is_complete() or runstate.run.event_index == 0):
        return "Finish your current run first (or save it with the Save button), then run a custom schedule."
    number = max(runstate.run.run_number, runstate.highest_awarded_run) + 1 if runstate.run.is_complete() else runstate.run.run_number
    if runstate.run.normalised:
        number = runstate.highest_awarded_run + 1
    runstate.run = RunState(run_number=number, custom_events=entry["events"], custom_name=entry["name"])
    _reset_run_ui_state()
    return f"Started a run on {entry['name']}: {len(entry['events'])} events. It is tagged as a custom schedule."


def start_new_run(event=None):
    """Starts a fresh run, reading current skill-tree bonuses — each run
    begins a little more capable than the last, per unlocked skills.

    Derives the new run_number from whichever is higher, the current run's
    own number or the persisted highest-awarded-run mark, not just the
    current run's number + 1. The current `run` can itself be a stale,
    reloaded snapshot (e.g. the player loaded an old still-in-progress save
    before starting anew) whose run_number sits behind runs that have
    since completed and been awarded elsewhere in the session -- basing
    the new number on it alone could hand out a run_number that's already
    in highest_awarded_run's past, silently blocking this genuinely new
    run's own completion payout later (see the double-award guard on
    resolve_next_event() above, and its dedicated test coverage in
    tests/test_save_system.py).

    E18: reads the extended-run-mode checkbox to decide whether the new
    run uses the doubled-length schedule (RunState's own `extended` flag)
    -- opt-in, and only ever read at the moment a new run starts, so it
    has no effect on a run already in progress."""
    runstate.skill_ranks_just_gained = []  # E-11: the rank callout belongs to the run that just ended
    _reset_run_ui_state()
    runstate.challenge_status_text = ""
    extended = document.getElementById("extended-run-toggle").checked
    scenario = document.getElementById("scenario-select").value
    # A finished challenge run never counted as a numbered run, so the next real one follows the last awarded.
    base = runstate.highest_awarded_run if runstate.run.normalised else runstate.run.run_number
    runstate.run = RunState(run_number=max(base, runstate.highest_awarded_run) + 1, extended=extended, scenario=scenario)
    render()
    _check_new_achievements_for_toast()


def begin_second_founding():
    """Gives the tree up for a Founding star. Returns (ok, message)."""
    if not founding_ready():
        return False, "A Second Founding needs all skills owned and a star still to earn."
    refund = founding_refund_total()
    runstate.skill_tree.unlocked = set()
    runstate.skill_tree.knowledge_points += refund
    runstate.skill_tree.save()
    runstate.meta["founding"] = {"stars": runstate.meta["founding"]["stars"] + 1, "owned": []}
    save_meta()
    chronicle_note("founding", f"Began a Second Founding: Founding star {runstate.meta['founding']['stars']} of {FOUNDING_MAX_STARS}.")  # E-7
    runstate.skill_map_selected = None
    runstate.skill_map_reveal = None
    runstate.founding_message_text = (
        f"The Second Founding has begun. Founding star {runstate.meta['founding']['stars']} of {FOUNDING_MAX_STARS} is yours, "
        f"you start every run with {founding_star_resources()} more resources, and the Founding skills can be bought. "
        f"Knowledge in hand: {runstate.skill_tree.knowledge_points}."
    )
    announce(runstate.founding_message_text)
    return True, runstate.founding_message_text
