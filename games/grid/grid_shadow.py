"""The shadow grid (C21): replaying your build and retire actions on a different starting scenario to compare.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import random

from js import document

import grid_runstate as runstate
from grid_rules import SCENARIOS
from grid_state import GridState


# ===========================================================================
# C21: the shadow grid ("grid twin", the lighter version). A second,
# NON-interactive grid that copies every build and retire you make onto a
# DIFFERENT starting scenario, so the two outcomes can be compared side by side
# ("what would the same choices have done from a coal-heavy start?"). It is
# not a second game to play: it is derived by replaying your recorded actions,
# round by round, on a fresh grid with its own fixed random stream, so it is
# reproducible, can never affect your grid, and needs only the scenario name
# and the action log to save. A mirrored action the shadow cannot afford is
# simply skipped and counted. It sits beside the C15 global comparison.
# ===========================================================================
SHADOW_SEED = 20260926
SHADOW_MAX_ACTIONS = 400


def default_shadow_scenario():
    """A contrasting start to the one being played."""
    return "standard" if runstate.state.scenario != "standard" else "coal_legacy"


def set_shadow_scenario(scenario_id):
    """Turns the shadow on for a scenario (or off with None). Existing actions
    are kept, so switching scenario replays the same choices somewhere else."""
    if scenario_id is not None and not (isinstance(scenario_id, str) and scenario_id in SCENARIOS):
        return False
    runstate.shadow_scenario = scenario_id
    return True


def record_shadow_action(kind, plant_type):
    if runstate.shadow_scenario is None:
        return
    runstate.shadow_actions.append({"round": runstate.state.round_number, "kind": kind, "type": plant_type})
    del runstate.shadow_actions[:-SHADOW_MAX_ACTIONS]


def replay_shadow():
    """Returns (shadow_grid, skipped_actions) for the player's current round."""
    grid_copy = GridState()
    grid_copy.apply_scenario(runstate.shadow_scenario)
    rng = random.Random(SHADOW_SEED)
    skipped = 0
    by_round = {}
    for action in runstate.shadow_actions:
        by_round.setdefault(action["round"], []).append(action)
    for round_number in range(1, runstate.state.round_number + 1):
        for action in by_round.get(round_number, []):
            ok = (
                grid_copy.build_plant(action["type"]) if action["kind"] == "build"
                else grid_copy.retire_plant(action["type"])
            )
            if not ok:
                skipped += 1
        if round_number < runstate.state.round_number:
            grid_copy.advance_round(rng=rng.random, age_rng=rng.random, weather_rng=rng.random)
    return grid_copy, skipped


def shadow_rows():
    """Comparison rows for the page: (metric, yours, shadow's)."""
    if runstate.shadow_scenario is None:
        return None
    twin, skipped = replay_shadow()
    rows = [
        ("Score", f"{runstate.state.score():.0f}", f"{twin.score():.0f}"),
        ("Funds", f"{runstate.state.funds:.0f}", f"{twin.funds:.0f}"),
        ("Clean share of capacity", f"{(1 - runstate.state.fossil_share()) * 100:.0f}%", f"{(1 - twin.fossil_share()) * 100:.0f}%"),
        ("Emissions avoided", f"{runstate.state.emissions_avoided():.0f}", f"{twin.emissions_avoided():.0f}"),
    ]
    if runstate.state.score() > twin.score() + 0.5:
        verdict = f"You are ahead of the {SCENARIOS[runstate.shadow_scenario]['label']} twin."
    elif twin.score() > runstate.state.score() + 0.5:
        verdict = f"The {SCENARIOS[runstate.shadow_scenario]['label']} twin is ahead of you."
    else:
        verdict = f"You and the {SCENARIOS[runstate.shadow_scenario]['label']} twin are level."
    if skipped:
        verdict += f" (The twin could not afford {skipped} of your mirrored moves.)"
    return rows, verdict


def render_shadow():
    select = document.getElementById("shadow-select")
    table = document.getElementById("shadow-table")
    verdict_el = document.getElementById("shadow-verdict")
    select.value = runstate.shadow_scenario or "off"
    table.innerHTML = ""
    result = shadow_rows()
    if result is None:
        verdict_el.innerText = "Pick a starting scenario to compare your choices against a shadow grid that copies every build and retire."
        return
    rows, verdict = result
    verdict_el.innerText = verdict
    header = document.createElement("div")
    header.className = "shadow-row shadow-row--head"
    for text in ("", "You", f"Twin ({SCENARIOS[runstate.shadow_scenario]['label']})"):
        cell = document.createElement("span")
        cell.innerText = text
        header.appendChild(cell)
    table.appendChild(header)
    for metric, yours, theirs in rows:
        line = document.createElement("div")
        line.className = "shadow-row"
        for text in (metric, yours, theirs):
            cell = document.createElement("span")
            cell.innerText = text
            line.appendChild(cell)
        table.appendChild(line)
