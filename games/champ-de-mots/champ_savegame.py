"""Saving: get_state() and load_state() (the shared save widget's contract) and resume_note().
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import narrative_log

import champ_runstate as runstate
from champ_rules import DEFAULT_EASE, STAGE_RANK, STAGE_SEED
from champ_model import _plot_record, _reset_plot, state
from champ_calendar import _validated_study_days
from champ_points import (
    _validated_golden, _validated_practice_ledger, _validated_quests, golden_plot, quest_state,
)
from champ_reportlog import REPORT_LOG_MAX
from champ_watering import _validated_coins, coins_state
from champ_practice_base import close_practice
from champ_leech import _validated_fail_run, _validated_last_watered, _validated_leech_rests
from champ_arrange import apply_farm_arrangement
from champ_placement import _validated_placement_through, close_placement
from champ_phrasebook import _validated_phrasebook
from champ_achievements import achievement_ids_earned
from champ_planner import _planner_cache, _validated_exam_plan


# ===========================================================================
# Milestone 5 — the shared save widget contract (SAVE-BUTTON-INTEGRATION.md §2)
# ===========================================================================
#
# The whole per-game contract is these two functions: get_state() hands back
# one plain JSON-safe dict, load_state() is its exact inverse. The widget in
# shared/save-widget.js is dropped in unchanged and does the rest.
#
# What is saved is only the SRS state — the catalog is static and versioned in
# the repo, so a save that also carried 722 plots' worth of French would be
# storing the same file twice. Better still, only plots that have actually
# been reviewed are written out: an untouched plot's record is exactly the
# defaults the catalog rebuilds it with, so storing 722 of them would turn
# every save into a ~100KB round trip to say almost nothing.

SAVE_VERSION = 1


def resume_note():
    """QI-58: one plain line for the hub's "Pick up where you stopped" strip (read by shared/last-played.js)."""
    due = len(state.due_plots())
    return f"Day {state.current_day}, {due} plot{'s' if due != 1 else ''} ready for water"


def get_state():
    # A plot counts as touched once it has been reviewed at all — including a
    # review that went wrong, which leaves streak 0 and stage Seed but a real
    # last_reviewed and a reduced ease that would otherwise be lost.
    return {
        "version": SAVE_VERSION,
        "current_day": state.current_day,
        "plots": {
            plot.plot_id: _plot_record(plot)
            for plot in state.plots
            if plot.last_reviewed is not None or plot.stage != STAGE_SEED
        },
        "error_patterns": dict(runstate.error_pattern_counts),
        "practice_ledger": {
            mode: dict(entry) for mode, entry in runstate.practice_ledger.items() if entry["total"]
        },
        # Z11 "My Reports" -- only written once something has actually been
        # reported, matching practice_ledger's own "don't bloat an untouched
        # save" rule above.
        **({"report_log": list(runstate.report_log)} if runstate.report_log else {}),
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) -- always
        # freshly recomputed from the farm above, never read back in
        # load_state(). This is what makes this game's achievements show up
        # on the hub-wide dashboard alongside every other game's.
        "achievements_earned": achievement_ids_earned(),
        # L13 -- opt-in study-buddy preference; only written when on, so
        # the default save is unchanged.
        **({"study_buddy": True} if runstate.study_buddy_enabled else {}),
        # L7a -- real calendar days with study activity; only written once
        # something has been studied, like practice_ledger above.
        **({"study_days": dict(runstate.study_days)} if runstate.study_days else {}),
        # L19 -- saved phrasebook plot ids, only once something is saved.
        **({"phrasebook": list(runstate.phrasebook)} if runstate.phrasebook else {}),
        # L4b -- highest row the player was placed through, only once non-zero.
        **({"placement_through": runstate.placement_through} if runstate.placement_through else {}),
        # L-9 -- the exam date and the what-if minutes, only once a date is set.
        **({"exam_plan": {"date": runstate.exam_date, "minutes": runstate.exam_minutes}} if runstate.exam_date else {}),
        # L-17 / L-14 / L-18: today's golden plot and daily goals, and how many
        # stubborn plots have been rested; each written only once it means something.
        **({"golden": dict(golden_plot)} if golden_plot["claimed"] else {}),
        **(
            {"quests": {"day": quest_state["day"], "progress": dict(quest_state["progress"]), "done": list(quest_state["done"])}}
            if quest_state["day"] >= 0 and (quest_state["progress"] or quest_state["done"])
            else {}
        ),
        **({"leech_rests": runstate.leech_rests} if runstate.leech_rests else {}),
        # L-1 (shop): coins and skins, only once a coin has been earned.
        **({"coins": {"earned": coins_state["earned"], "spent": coins_state["spent"], "owned": list(coins_state["owned"]), "equipped": coins_state["equipped"]}} if coins_state["earned"] else {}),
    }


# REVIEW(testing): existing tests always pass explicit version/current_day/
# plots keys (even if plots is {}) -- no test calls load_state({}) exercising
# the data.get("plots") or {} and data.get("current_day", 0) defaults
# together end-to-end, the "truly empty save" case CLAUDE.md's Milestone 5
# notes call out as in-scope. Also no test loads a save with an unrecognized
# stage string to exercise the STAGE_RANK fallback a few lines below.
def _is_valid_report_log_entry(entry):
    return (
        isinstance(entry.get("day"), int)
        and not isinstance(entry.get("day"), bool)
        and isinstance(entry.get("topic"), str)
        and isinstance(entry.get("text"), str)
    )


def load_state(data):
    runstate.study_buddy_enabled = data.get("study_buddy") is True

    saved_plots = data.get("plots") or {}
    state.current_day = data.get("current_day", 0)
    state.invalidate_unlocks()
    runstate.error_pattern_counts = dict(data.get("error_patterns") or {})
    runstate.practice_ledger = _validated_practice_ledger(data.get("practice_ledger"))
    runstate.study_days = _validated_study_days(data.get("study_days"))
    runstate.phrasebook = _validated_phrasebook(data.get("phrasebook"))
    runstate.placement_through = _validated_placement_through(data.get("placement_through"))
    runstate.exam_date, runstate.exam_minutes = _validated_exam_plan(data.get("exam_plan"))
    golden_plot.update(_validated_golden(data.get("golden")))
    quest_state.update(_validated_quests(data.get("quests")))
    runstate.leech_rests = _validated_leech_rests(data.get("leech_rests"))
    coins_state.update(_validated_coins(data.get("coins")))
    _planner_cache.clear()
    # Z11 "My Reports" -- an old save predating this feature simply has no
    # "report_log" key, which sanitize() already treats as "empty list",
    # the same forward-compatibility standard every other per-game field
    # in this hub's save schemas already holds itself to.
    runstate.report_log = narrative_log.sanitize(
        data.get("report_log"), REPORT_LOG_MAX, is_valid=_is_valid_report_log_entry
    )

    for plot in state.plots:
        # Plots missing from the save are reset rather than left as they are:
        # loading someone else's farm must not leave this session's plants
        # standing in it.
        _reset_plot(plot)
        record = saved_plots.get(plot.plot_id)
        if not record:
            continue
        plot.ease_factor = record.get("ease_factor", DEFAULT_EASE)
        plot.interval_days = record.get("interval_days", 0)
        plot.last_reviewed = record.get("last_reviewed")
        plot.next_due = record.get("next_due")
        plot.correct_streak = record.get("correct_streak", 0)
        plot.stage = record.get("stage", STAGE_SEED)
        if plot.stage not in STAGE_RANK:
            plot.stage = STAGE_SEED
        plot.in_weeds = bool(record.get("in_weeds", False))
        plot.fail_run = _validated_fail_run(record.get("fail_run"))
        plot.last_watered = _validated_last_watered(record, plot)

    # Any question on screen was generated against the farm that just got
    # replaced, so it is closed rather than answered into the new one.
    apply_farm_arrangement()
    close_placement()
    close_practice()
    return True
