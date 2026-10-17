"""Farm succession (F25): handing the farm over, legacy points and perks, and the round celebration.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

from js import document

import herd_runstate as runstate
from herd_model import FarmState, rules_unranked
from herd_blind import blind_hidden, blind_reveal_message, reveal_blind_run
from herd_achievements import _display_milestone_toast
from herd_pasture import retire_herd_to_hall
from herd_loadouts import _shift_loadout, loadout_is_unlocked
from herd_ledger import file_ghost, ledger_entry, ledger_record


# ===========================================================================
# F25: farm succession -- an Aftermath-style meta-progression, built
# independently. A certified farm can be handed to the next generation: the
# farm restarts from scratch, the generation counter rises and the outgoing
# farm earns legacy points, which buy permanent perks. Tied to F23: raising a
# poultry flock feeds the handover, and the Heritage Flock perk carries the
# poultry unlock into every later generation. Deliberately module-level (like
# `chains_completed_count` in Loop): a reset of `farm` must never touch it.
# ===========================================================================
SUCCESSION_BASE_POINTS = 1
SUCCESSION_FLOCK_BONUS_POINTS = 1
SUCCESSION_FLOCK_MIN_SIZE = 3
LEGACY_PERKS = {
    "family_savings": {"label": "Family Savings", "cost": 1, "max": 3,
                       "blurb": "+75 starting funds per level, every generation."},
    "heritage_flock": {"label": "Heritage Flock", "cost": 2, "max": 1,
                       "blurb": "The poultry flock is available from round 1, no certification needed."},
    "mentor_methods": {"label": "Mentor's Methods", "cost": 2, "max": 1,
                       "blurb": "Every generation starts with one Feed Additives unit already in place."},
}
FAMILY_SAVINGS_FUNDS = 75


def can_hand_over():
    return runstate.farm.certified and not runstate.sandbox_active


def handover_points():
    """Points the current farm would earn on handover."""
    points = SUCCESSION_BASE_POINTS
    if runstate.farm.poultry_size >= SUCCESSION_FLOCK_MIN_SIZE:
        points += SUCCESSION_FLOCK_BONUS_POINTS
    return points


def _apply_perk_to_farm(name):
    """One level of a perk's effect on the CURRENT farm (used both when a perk
    is bought and when a new generation starts)."""
    if name == "family_savings":
        runstate.farm.funds += FAMILY_SAVINGS_FUNDS
        runstate.farm.counterfactual_funds += FAMILY_SAVINGS_FUNDS
    elif name == "mentor_methods":
        runstate.farm.decoupling_investment["feed"] += 1


def buy_legacy_perk(name):
    spec = LEGACY_PERKS.get(name)
    if spec is None:
        return False
    level = runstate.legacy_perks.get(name, 0)
    if level >= spec["max"] or runstate.legacy_points < spec["cost"]:
        return False
    runstate.legacy_points -= spec["cost"]
    runstate.legacy_perks[name] = level + 1
    _apply_perk_to_farm(name)
    return True


def hand_over_farm():
    """Awards points, starts the next generation on a fresh farm and applies
    every perk owned so far. Returns the points earned, or None if the farm
    can't be handed over yet."""
    if not can_hand_over():
        return None
    earned = handover_points()
    if blind_hidden():
        reveal_blind_run()  # GF-28: the blind run ends with the farm; say how it went before it is retired
        _display_milestone_toast(blind_reveal_message())
    ledger_record(ledger_entry(finished=True))  # F-2: the finished farm is filed before it is retired
    file_ghost()  # Z-3e: and kept as the ghost when it is the best result in its mode
    retire_herd_to_hall()  # GF-13: the longest-serving animals are honoured before the herd is retired
    runstate.legacy_points += earned
    runstate.generation += 1
    runstate.farm = FarmState()
    runstate.last_deltas = {}  # the old farm's round-change chips do not belong to the new one
    for name, level in runstate.legacy_perks.items():
        for _ in range(level):
            _apply_perk_to_farm(name)
    if runstate.loadout_choice != "standard" and loadout_is_unlocked(runstate.loadout_choice):
        _shift_loadout(runstate.farm, runstate.loadout_choice, +1)  # GF-23: the chosen starting loadout opens the new generation
        runstate.farm.loadout = runstate.loadout_choice
    return earned


def render_succession():
    panel = document.getElementById("succession-panel")
    visible = runstate.farm.certified or runstate.generation > 1 or runstate.legacy_points > 0 or bool(runstate.legacy_perks)
    panel.hidden = not visible
    if not visible:
        return
    status = f"Generation {runstate.generation}. Legacy points: {runstate.legacy_points}."
    if can_hand_over():
        status += f" Handing over now would earn {handover_points()} point(s)."
    else:
        status += " Earn sustainable certification to be able to hand the farm down."
    document.getElementById("succession-display").innerText = status
    hand_button = document.getElementById("succession-button")
    hand_button.disabled = not can_hand_over()
    for name, spec in LEGACY_PERKS.items():
        level = runstate.legacy_perks.get(name, 0)
        button = document.getElementById(f"perk-{name.replace('_', '-')}-button")
        button.innerText = f"{spec['label']} ({level}/{spec['max']}) \u2014 {spec['cost']} pt"
        button.title = spec["blurb"]
        button.disabled = level >= spec["max"] or runstate.legacy_points < spec["cost"]


def _report_decoupling_gap():
    """F21: the decoupling gap (score minus the pure-growth counterfactual's
    score) goes to the shared opt-in leaderboard widget, which only submits
    for an opted-in, signed-in player and remembers the personal best."""
    gap = runstate.farm.score() - runstate.farm.counterfactual_score()
    if gap <= 0 or rules_unranked():  # F-1: custom-rule runs stay off the leaderboard
        return
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    board = getattr(window, "NoyvjLeaderboard", None)
    if board is not None:
        board.report("herd", "decoupling_gap", round(gap, 1), f"round {runstate.farm.round_number}")


def celebrate_round(income, beat):
    """GF-14: hands the round's income to the page's optional HerdFx hook (settings.js), which counts it up
    under the Advance Round button and bursts confetti when `beat` is true. A page without the hook, or the
    pytest harness, is a silent no-op."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    hook = getattr(window, "HerdFx", None)
    if hook is None:
        return False
    hook.roundGain(float(income), bool(beat))
    return True
