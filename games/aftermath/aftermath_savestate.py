"""steward_summary(), get_state() and load_state(): the save format."""

import copy
import json

import ghost as ghost_lib

import aftermath_runstate as runstate
from aftermath_achievements import (
    _clean_event_badges, _season_hook, _seed_achievement_toast_baseline, achievement_ids_earned,
)
from aftermath_actions import challenge_run_from_code
from aftermath_bonuses import TIMER_MAX_SECONDS, run_timer_enabled
from aftermath_challenges import _load_resources_log, daily_seed_of_code, ghost_run_eligible
from aftermath_model_run import RunState
from aftermath_persist import _now, skill_tree_strength
from aftermath_renderer import render
from aftermath_rules import DEFAULT_SCENARIO, SKILLS


# B-23: a few honest, already-computed numbers for the hub's Climate Steward page. Written into the save as a
# read-only `summary` list ({label, value, unit, note?}); never read back by load_state().
def steward_summary():
    return [
        {"label": "Resilience skills unlocked", "value": skill_tree_strength(), "unit": f"of {len(SKILLS)}"},
        {"label": "Run number", "value": int(runstate.run.run_number), "unit": ""},
        {"label": "Resilience built this run", "value": int(runstate.run.resilience_capacity), "unit": ""},
    ]


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state()/load_state() cover Aftermath's in-memory *per-run* state
# only — the current RunState (run_number, event_index, resources,
# resilience_capacity, growth_capacity, damage_taken, event_log) — which
# is what needs to round-trip so a saved-and-reloaded run resumes at the
# exact point it was saved. The persistent skill tree (SkillTreeState),
# run_history, and legacy_events are deliberately NOT part of this
# round trip: per CLAUDE.md's Tech notes, those are a distinct,
# already-working persistence mechanism keyed to localStorage (not to a
# save code) that survives across runs and browser visits on its own.
# Folding them into this save system would mean a loaded save code could
# silently overwrite a browser's separately-accumulated skill tree with
# whatever it looked like at save time — the wrong behavior for state
# that's supposed to be permanent. A save code loaded on a different
# browser/device therefore resumes the exact in-progress run, but keeps
# whatever skill tree/legacy history (or lack of it) already exists
# locally — consistent with how that persistence already behaves
# independent of any one run.
def get_state():
    """Return the current run's in-memory state as a plain JSON-safe dict.
    `event_log` is deep-copied — it's a list of dicts, and a shallow copy
    would still alias it, so continued play after taking a "snapshot"
    would silently mutate the saved copy."""
    return {
        "run_number": runstate.run.run_number,
        "event_index": runstate.run.event_index,
        "resources": runstate.run.resources,
        "resilience_capacity": runstate.run.resilience_capacity,
        "growth_capacity": runstate.run.growth_capacity,
        "damage_taken": runstate.run.damage_taken,
        "event_log": copy.deepcopy(runstate.run.event_log),
        # E18: whether this run is using the doubled-length schedule.
        # Added after this save contract first shipped -- load_state()
        # below defaults it to False for any older save code that
        # predates the field, rather than the KeyError every other key
        # here deliberately gets.
        "extended": runstate.run.extended,
        **({"scenario": runstate.run.scenario} if runstate.run.scenario != DEFAULT_SCENARIO else {}),
        # E-4 / E-13: a challenge run keeps its run code (the schedule and draw are rebuilt from it) and a
        # run on a built schedule keeps the events and name. Absent for ordinary runs.
        **({"challenge_code": runstate.run.challenge["code"]} if runstate.run.normalised and runstate.run.challenge else {}),
        # Z-5c: set only for a run begun with the Today's run button (the seed is rebuilt from the code on load).
        **({"challenge_daily": True} if runstate.run.normalised and runstate.run.challenge and runstate.run.challenge.get("daily_seed") else {}),
        **({"custom_events": list(runstate.run.custom_events), "custom_name": runstate.run.custom_name or ""}
           if runstate.run.custom_events and not runstate.run.normalised else {}),
        # GE-23: the run timer's seconds so far, only for a run that is being timed.
        **({"timer_seconds": int(runstate.run.elapsed)} if runstate.run.timed and runstate.run.elapsed >= 1 else {}),
        # Z-3d: the resources after each event, only while the run can be compared with a ghost.
        **({"resources_log": [ghost_lib.clean_number(v) for v in runstate.run.resources_log]}
           if runstate.run.resources_log and ghost_run_eligible(runstate.run) and len(runstate.run.resources_log) == runstate.run.event_index else {}),
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed, never read back by load_state() below.
        "summary": steward_summary(),  # B-23: write-only, never read back
        "achievements_earned": achievement_ids_earned(),
        **({"event_badges": list(runstate.event_badges)} if runstate.event_badges else {}),
        # E9: a write-only number for the community resilience index (how many
        # resilience skills this player's tree has unlocked); never read back.
        "skill_tree_strength": skill_tree_strength(),
    }


# Direct key access (data["run_number"], etc.), no defensive handling --
# unlike SkillTreeState.load()'s try/except. This is intentional, not an
# oversight: a real save handed here always came from this same site's own
# get_state() via the save widget's fetch/PUT round trip, so a malformed
# payload means something upstream already went wrong, and a loud KeyError
# is preferable to silently starting a run in a half-restored state. Pinned
# by tests/test_save_system.py::test_load_state_on_a_malformed_dict_raises_rather_than_corrupting_the_run
# so this stays a deliberate choice, not something a future change reverts.
def load_state(data):
    """The exact inverse of get_state() — rebuilds the current run from a
    saved dict and re-renders so the UI reflects the loaded run
    immediately. Constructs a fresh RunState (which reads current
    skill-tree bonuses, same as starting any new run) and then overwrites
    every field with the saved values, so the restored run matches
    exactly what was saved regardless of the skill tree's state now."""
    # data.get(...) rather than data["extended"] -- see get_state()'s
    # comment on this one field: it postdates this save contract, and an
    # older save code simply never was an extended run.
    saved_scenario = data.get("scenario")
    restored = None
    if isinstance(data.get("challenge_code"), str):  # E-4: rebuild the challenge from its code
        restored, _error = challenge_run_from_code(data["challenge_code"])
        if restored is not None:
            restored.run_number = data["run_number"]
            if data.get("challenge_daily") is True:  # Z-5c: only a classic-mode code can be a Today's run
                restored.challenge["daily_seed"] = daily_seed_of_code(data["challenge_code"])
    if restored is None:
        custom = data.get("custom_events")
        restored = RunState(
            run_number=data["run_number"], extended=data.get("extended", False),
            scenario=saved_scenario if isinstance(saved_scenario, str) else DEFAULT_SCENARIO,
            custom_events=custom if isinstance(custom, list) else None,
            custom_name=data.get("custom_name") if isinstance(data.get("custom_name"), str) else None,
        )
    runstate.run = restored
    runstate.run.event_index = data["event_index"]
    runstate.run.resources = data["resources"]
    runstate.run.resilience_capacity = data["resilience_capacity"]
    runstate.run.growth_capacity = data["growth_capacity"]
    runstate.run.damage_taken = data["damage_taken"]
    runstate.run.event_log = copy.deepcopy(data["event_log"])
    runstate.run.resources_log = _load_resources_log(data.get("resources_log"), runstate.run.event_index)  # Z-3d: absent in older saves
    saved_seconds = data.get("timer_seconds")  # GE-23: absent from older saves; a bad value is ignored
    if (
        isinstance(saved_seconds, (int, float)) and not isinstance(saved_seconds, bool)
        and 1 <= saved_seconds <= TIMER_MAX_SECONDS and not runstate.run.normalised and run_timer_enabled()
    ):
        runstate.run.timed, runstate.run.elapsed, runstate.run._timer_last = True, float(int(saved_seconds)), _now()
    runstate.event_badges = _clean_event_badges(data.get("event_badges"))
    if runstate.event_badges:
        _season_hook("aftermathAdoptBadges", json.dumps(runstate.event_badges))
    render()
    # "achievements_earned" is intentionally never read back here — see
    # get_state()'s comment and ACHIEVEMENTS-SYSTEM-DESIGN.md §1. Re-seed
    # the toast baseline instead of leaving it as-is, so a loaded save with
    # several achievements already earned doesn't flood the player with
    # toasts for all of them at once (same reasoning as setup()'s seed).
    _seed_achievement_toast_baseline()
    return True
