"""The Scarcity Run's fixed numbers, saved days, factors and the text helpers the stats card shares."""

import challenges

import sol_runstate as runstate
from sol_rules import PLANET_DISPLAY_NAMES, planet_state
from sol_util import _split_time, _today_utc


# =============================================================================
# Round-6 batch (2026-10-11): A-11 / A-12 Scarcity Run, A-29 Ghost Run.
# Every save key is optional, written only when non-default and cleaned on load.
# The pure parts (dates, seed words, the day's rules, recording validators) live in
# challenges.py; this block owns the simulation and the panels.
# =============================================================================

# --- A-11 / A-12: the Scarcity Run -----------------------------------------------------
# One challenge per UTC date, the same for everybody, played on a COPY of the game: starting
# a run stashes the real game (the exact dict get_state() returns), swaps a fresh start in,
# and leaving puts the stash back, so the campaign and its save are never touched. While a
# run is on, get_state() hands the widget the stash (plus the run records), achievements,
# the leaderboard, capsules, prestige and the campaign's own ghost recording are all off,
# and timed anomalies, the rhythm bonus and chain bonuses are off so the rules are the same
# for everyone. The goal is checked every tick; the time is kept in ticks (game time), never
# wall-clock, in `scarcity_days` (the only new thing in the save). Nothing is a streak.
# Fairness: before a date is accepted the Governor alone (nobody standing anywhere, default
# settings) must reach the goal within SCARCITY_BOUND_TICKS; its time is the par.
SCARCITY_BOUND_TICKS = 9000  # 15 minutes of game time: the Governor alone must finish by here
SCARCITY_BOT_CLICKS_PER_TICK = 0.3  # three clicks a second: a patient hand, well under a real player's pace
SCARCITY_STALL_CHECK = 1500  # a candidate day whose progress did not move in this many ticks is stuck
SCARCITY_MIN_TICKS = 500  # and not so fast that the day is a non-event

SCARCITY_BOT_PRIORITY = "ecology"  # the Governor alone is told to restore ecology first (recyclers only) ...
SCARCITY_BOT_BUDGET = 100.0  # ... and may spend everything it has
SCARCITY_RESEARCH_LEVEL = 0  # Near Bodies is researched at the start (Moon and Mars open)

scarcity_days = {}  # date -> {"ticks", "tries", "under_par"?}: the only saved part

_scarcity_specs = {}

_scarcity_refs = {}


def scarcity_active():
    return runstate._scarcity is not None


def scarcity_yield(planet):
    """The day's resource-mix factor for a world (1 outside a run)."""
    return 1.0 if runstate._scarcity is None else runstate._scarcity["spec"]["yields"].get(planet, 1.0)


def scarcity_decay():
    return 1.0 if runstate._scarcity is None else runstate._scarcity["spec"]["decay"]


def scarcity_cost():
    return 1.0 if runstate._scarcity is None else runstate._scarcity["spec"]["cost"]


def scarcity_terraform():
    return 1.0 if runstate._scarcity is None else challenges.TERRAFORM_SPEED


def _load_scarcity(data):
    if runstate._scarcity_keep_days:
        return  # an internal swap: the run records are not part of what is being swapped
    scarcity_days.clear()
    scarcity_days.update(challenges.clean_days(data.get("scarcity_days")))


def _scarcity_mean_progress():
    targets = runstate._scarcity["spec"]["targets"]
    return sum(planet_state[w]["terraform_progress"] for w in targets) / len(targets)


def scarcity_goal_met():
    spec = runstate._scarcity["spec"]
    return all(planet_state[w]["terraform_progress"] >= spec["target_pct"] for w in spec["targets"])


def _scarcity_status_line():
    run = runstate._scarcity
    spec = run["spec"]
    if run["done"] is not None:
        return f"Scarcity Run {spec['words']}: done in {_split_time(run['done'])}. You can keep playing or leave."
    parts = ", ".join(
        f"{PLANET_DISPLAY_NAMES.get(w, w)} {planet_state[w]['terraform_progress']:.1f}/{spec['target_pct']}%" for w in spec["targets"])
    return f"Scarcity Run {spec['words']}: {parts} - {_split_time(runstate.total_ticks)} in."


# --- A-12 helpers shared with the Stats & Share card --------------------------------------
def scarcity_today_words():
    today = _today_utc()
    return challenges.seed_words(today) if today else None


def scarcity_share_lines():
    """Lines for the Stats & Share card: today's seed and today's result."""
    today = _today_utc()
    if today is None:
        return []
    lines = [f"Today's seed: {challenges.seed_words(today)}"]
    record = scarcity_days.get(today)
    if record:
        lines.append(f"Scarcity Run today: {_split_time(record['ticks'])}" + (" (under par)" if record.get("under_par") else ""))
    return lines


def scarcity_run_card_text():
    """The card shown instead of the campaign card while a run is on."""
    run = runstate._scarcity
    spec = run["spec"]
    lines = ["\U0001f30c SOL Scarcity Run", f"Seed: {spec['words']} ({spec['date']})", f"Goal: {challenges.goal_text(spec)}"]
    if run["done"] is not None:
        lines.append(f"Done in {_split_time(run['done'])} (the Governor alone: {_split_time(spec['par'])})")
    else:
        lines.append(_scarcity_status_line())
    return "\n".join(lines)
