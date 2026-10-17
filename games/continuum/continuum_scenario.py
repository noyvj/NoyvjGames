"""Starting scenarios (K12), hard mode (K18), consulting cases (K22) and their display updates."""

from js import document

import challengerun
import consulting
import dynasty
import founding
import sim

import continuum_runstate as runstate
from continuum_achievements import _seed_achievement_toast_baseline, achievement_ids_earned
from continuum_archive import archive_load
from continuum_base import current_effects

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# ===========================================================================
# K12/K18 (planning/TODO.md): starting scenario select + opt-in hard mode.
# Built together since K18 is explicitly "likely alongside K12's scenario
# select" in the task's own wording, and both are opt-in starting-
# condition/difficulty controls in the same "toggle set, not a full menu
# system" shape Grid's own steeper-demand-growth/weather-variability
# toggles established (see games/grid/CLAUDE.md's settings-panel section).
# ===========================================================================
#
# Scenario is locked once the settlement has taken its first real action.
# `state.season > 1` is a clean, already-existing "has a season ever been
# advanced" signal — CityState.__init__ always starts at 1, and
# advance_season() is the only thing that ever increments it — so
# re-picking a scenario mid-playthrough can't retroactively rewrite a
# settlement that has already grown past its starting numbers. Hard mode
# has no such lock: like Grid's own toggles, it can be flipped at any
# time; see sustainability.py's own K18 note for exactly what it tightens.
def _scenario_locked():
    # K22: a consulting case replaces the opening conditions wholesale, so the
    # normal scenario picker stays locked while one is on the table.
    return (
        runstate.state.season > 1
        or consulting.get(runstate.campaign.ui) is not None
        or challengerun.get(runstate.campaign.ui) is not None
    )


def refuge_unlocked():
    """O-8: the Refuge Start is offered once any settlement, ever, has
    reached the Space Age (live achievements plus the ones carried over from
    earlier settlements, or an archived settlement that got that far)."""
    return founding.refuge_unlocked(achievement_ids_earned(), archive_load())


def _scenario_available(scenario_id):
    if scenario_id in dynasty.SCENARIO_UNLOCKS:
        return dynasty.scenario_unlocked(runstate.campaign.ui, scenario_id)
    return scenario_id != "refuge" or refuge_unlocked()


def _make_select_scenario_handler(scenario_id):
    def handler(event=None):
        if _scenario_locked() or scenario_id not in sim.SCENARIOS or not _scenario_available(scenario_id):
            return
        config = sim.scenario_config(scenario_id)
        # Mutated in place, the same "restore into the existing object"
        # discipline save.restore_city() already uses, rather than
        # constructing and swapping in a whole new CityState — state is
        # aliased by campaign.state and this module's own `state` name
        # alike, and mutating in place keeps both valid with no
        # reassignment needed.
        runstate.state.scenario = scenario_id
        runstate.state.population = config["population"]
        runstate.state.resources["food"] = config["food"]
        runstate.state.resources["materials"] = config["materials"]
        runstate.state.resources["tools"] = config["tools"]
        # O-8: only the Refuge Start sets its own knowledge; picking any other
        # scenario (or switching back) puts the standard opening figure back.
        runstate.state.resources["knowledge"] = config.get("knowledge", sim.START_KNOWLEDGE)
        runstate.state.land_health = config["land_health"]
        runstate.state.clamp_allocation()
        # Re-baseline the log's own "have we already reported this" state
        # against the newly-chosen starting numbers -- the settlement is
        # still at season 1 with nothing researched, the same precondition
        # bootstrap() itself documents needing, so this is safe to call
        # again here exactly as it was at Campaign construction.
        runstate.chronicle.bootstrap(runstate.state, runstate.tree, current_effects())
        render()
    return handler


def on_toggle_hard_mode(event=None):
    if challengerun.active(runstate.campaign.ui) is not None:
        return  # K-10/K-11: Hard Mode is part of the run's setup, so the par stays comparable
    runstate.state.hard_mode = not runstate.state.hard_mode
    render()


# --- K22 consulting mode --------------------------------------------------
def _make_consulting_start_handler(case_id):
    def handler(event=None):
        if challengerun.get(runstate.campaign.ui) is not None:
            return  # a challenge run already owns this opening
        if consulting.apply(runstate.campaign, case_id, runstate.chronicle):
            runstate.chronicle.log_challenge(
                runstate.state.season, runstate.state.era, f"Called in to advise: {consulting.CASES[case_id]['label']}."
            )
            render()
            _seed_achievement_toast_baseline()
    return handler


def on_consulting_abandon(event=None):
    if consulting.abandon(runstate.campaign, runstate.chronicle):
        render()
        _seed_achievement_toast_baseline()


def update_consulting_display():
    entry = consulting.get(runstate.campaign.ui)
    pristine = consulting.is_pristine(runstate.campaign)
    for case_id in consulting.CASES:
        button = document.getElementById(f"consulting-case-{case_id}-button")
        button.disabled = not pristine or challengerun.get(runstate.campaign.ui) is not None
        button.classList.toggle("selected", entry is not None and entry["case"] == case_id)
    document.getElementById("consulting-status-display").innerText = (
        consulting.status_text(entry, runstate.state)
        or (
            "Take over a struggling, pre-built city. Only offered before you play a season."
            if pristine
            else "Consulting cases are only offered on a fresh, untouched start."
        )
    )
    document.getElementById("consulting-abandon-button").hidden = entry is None


def update_scenario_display():
    locked = _scenario_locked()
    note = document.getElementById("scenario-select-note")
    note.innerText = (
        "Locked in for this settlement now that play has begun."
        if locked
        else "Pick before advancing your first season — this can't be changed afterward."
    )
    for scenario_id in sim.SCENARIOS:
        button = document.getElementById(f"scenario-{scenario_id}-button")
        available = _scenario_available(scenario_id)
        button.disabled = locked or not available
        button.classList.toggle("selected", runstate.state.scenario == scenario_id)
        if scenario_id == "refuge" or scenario_id in dynasty.SCENARIO_UNLOCKS:
            label = sim.SCENARIOS[scenario_id]["label"]
            button.innerText = label if available else f"🔒 {label}"
            hint = sim.SCENARIOS[scenario_id]["blurb"]
            if scenario_id == "refuge":
                lock_text = f"reach the {sim.ERA_LABEL[sim.REFUGE_UNLOCK_ERA]} in any settlement"
            else:
                lock_text = f"buy the \u201c{dynasty.scenario_unlock_label(scenario_id)}\u201d perk in the Dynasty"
            button.title = hint if available else f"Locked: {lock_text} to unlock this opening."
            button.setAttribute(
                "aria-label",
                f"{label}, available" if available else f"{label}, locked until you {lock_text}",
            )


def update_hard_mode_display():
    button = document.getElementById("hard-mode-toggle-button")
    button.innerText = f"☠️ Hard Mode: {'ON' if runstate.state.hard_mode else 'OFF'}"
    button.classList.toggle("active", runstate.state.hard_mode)
    button.disabled = challengerun.active(runstate.campaign.ui) is not None
