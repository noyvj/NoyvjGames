"""The practice-progress ledger (record_practice and the header score), the study buddy, the golden plot of the day and the
daily goals. Every practice mode feeds record_practice().
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import champ_runstate as runstate
from champ_rules import (
    DOUBLE_POINT_MODES, PRACTICE_COUNT_LIMIT, PRACTICE_DAILY_CAP, PRACTICE_MAX_POINTS_PER_ANSWER,
    PRACTICE_MODES, PRACTICE_MODE_CAP, _blank_practice_entry,
)
from champ_model import is_due, state
from champ_util import _element
from champ_calendar import note_study_answer


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


def practice_score():
    """The player's total practice points across every mode."""
    return sum(entry["points"] for entry in runstate.practice_ledger.values())


def record_practice(mode, correct, points=1, count_study=True):
    """Tally one answered question for `mode`; True if it earned a point.
    `points` is how many it is worth (1, or 2 for a golden plot or a finished
    daily goal); the daily and lifetime caps clip it. `count_study` is False
    for a call that rides on an answer already counted as a study answer."""
    entry = runstate.practice_ledger.get(mode)
    if entry is None:
        return False
    entry["total"] = min(entry["total"] + 1, PRACTICE_COUNT_LIMIT)
    if count_study:
        note_study_answer()
    if entry["day"] != state.current_day:
        entry["day"] = state.current_day
        entry["day_points"] = 0
    awarded = False
    if correct:
        entry["correct"] = min(entry["correct"] + 1, PRACTICE_COUNT_LIMIT)
        if entry["day_points"] < PRACTICE_DAILY_CAP and entry["points"] < PRACTICE_MODE_CAP:
            gain = max(1, min(int(points), PRACTICE_MAX_POINTS_PER_ANSWER))
            gain = min(gain, PRACTICE_DAILY_CAP - entry["day_points"], PRACTICE_MODE_CAP - entry["points"])
            entry["points"] += gain
            entry["day_points"] += gain
            awarded = True
        if mode not in DOUBLE_POINT_MODES:
            _quest_note("practice")
            if mode == "liaison":
                _quest_note("liaison")
    try:
        render_practice_score()
    except Exception:
        # A headline-tile repaint must never break answering a question.
        pass
    return awarded


# L13 -- an opt-in "study buddy": a daily suggested review-session length
# based on how many already-watered plots are due (never-watered seeds don't
# count, or a brand-new farm would demand hundreds of reviews). It only
# ever suggests; nothing is blocked or scored, and there's no streak
# framing, matching the game's calm, no-guilt stance.
STUDY_BUDDY_MAX_SUGGESTION = 25
STUDY_BUDDY_SECONDS_PER_REVIEW = 30


def study_buddy_overdue_count():
    return sum(1 for p in state.plots if p.last_reviewed is not None and is_due(p, state.current_day))


def study_buddy_message():
    overdue = study_buddy_overdue_count()
    if overdue == 0:
        return "Study buddy: you're all caught up. If you want to add something new, water a handful of fresh plots."
    suggested = min(overdue, STUDY_BUDDY_MAX_SUGGESTION)
    minutes = max(1, round(suggested * STUDY_BUDDY_SECONDS_PER_REVIEW / 60))
    message = f"Study buddy: about {suggested} review{'s' if suggested != 1 else ''} today, roughly {minutes} min."
    if overdue > suggested:
        message += f" You have {overdue} due; a Mixed Review Marathon can clear more."
    return message


def on_toggle_study_buddy(event=None):
    runstate.study_buddy_enabled = not runstate.study_buddy_enabled
    render()


def render_study_buddy():
    button = _element("study-buddy-toggle-button")
    display = _element("study-buddy-display")
    button.innerText = f"Study buddy: {'on' if runstate.study_buddy_enabled else 'off'}"
    display.hidden = not runstate.study_buddy_enabled
    display.innerText = study_buddy_message() if runstate.study_buddy_enabled else ""


def gender_drill_accuracy_text():
    """L10 -- the gender-tagging drill's own running accuracy, read from the
    practice ledger (the same numbers the dashboard's per-mode section shows)."""
    entry = runstate.practice_ledger.get("gender")
    if not entry or entry["total"] == 0:
        return ""
    percent = round(100 * entry["correct"] / entry["total"])
    return f"Gender drill so far: {entry['correct']}/{entry['total']} right ({percent}%)"


def render_practice_score():
    _element("practice-score-display").innerText = f"Practice score: {practice_score()}"


def _validated_practice_ledger(raw):
    """Defaulted/clamped ledger from an untrusted save value."""
    ledger = {mode: _blank_practice_entry() for mode in PRACTICE_MODES}
    if not isinstance(raw, dict):
        return ledger

    def as_int(value, low, high, default):
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return max(low, min(high, value))

    for mode in PRACTICE_MODES:
        record = raw.get(mode)
        if not isinstance(record, dict):
            continue
        total = as_int(record.get("total"), 0, PRACTICE_COUNT_LIMIT, 0)
        correct = min(as_int(record.get("correct"), 0, PRACTICE_COUNT_LIMIT, 0), total)
        ledger[mode] = {
            "correct": correct,
            "total": total,
            # Points can never exceed (correct answers x the most one answer is worth) or the lifetime cap.
            "points": min(
                as_int(record.get("points"), 0, PRACTICE_MODE_CAP, 0),
                correct * (PRACTICE_MAX_POINTS_PER_ANSWER if mode in DOUBLE_POINT_MODES else 1),
            ),
            "day": as_int(record.get("day"), -1, PRACTICE_COUNT_LIMIT, -1),
            "day_points": as_int(record.get("day_points"), 0, PRACTICE_DAILY_CAP, 0),
        }
    return ledger


# ===========================================================================
# Round 3 batch 2 (2026-10-08): the golden plot (L-17), daily goals (L-14),
# stubborn weeds (L-18), slip forgiveness (L-19), session highlights (L-27)
# and the weak-items export (L-29).
# ===========================================================================
#
# None of these touch the SRS scheduler: a golden plot, a daily goal and a
# stubborn-weed rest only ever add to the practice ledger (or move one plot's
# next_due when the player asks to rest it), and slip forgiveness puts a plot
# back exactly as it was before the answer.
# --- L-17: the golden plot of the day --------------------------------------
# One due plot a day is marked gold. A correct answer on it earns two practice
# points in the "golden" ledger mode (the farm's own watering earns none, so
# this is the one place the daily loop adds to the headline score). Nothing is
# lost by missing it or by answering it wrong: it just stays unclaimed.
GOLDEN_POINTS = 2
golden_plot = {"day": -1, "plot_id": None, "claimed": False}


def _golden_pool():
    due = state.due_plots()
    watered = [p for p in due if p.last_reviewed is not None]
    return sorted(watered or due, key=lambda p: p.plot_id)


def ensure_golden():
    """Today's golden plot id (or None). Picked deterministically from the
    plots that are due, preferring ones already watered, the first time it is
    asked for on a given in-game day."""
    day = state.current_day
    if golden_plot["day"] != day:
        golden_plot.update({"day": day, "plot_id": None, "claimed": False})
    if golden_plot["plot_id"] is None and not golden_plot["claimed"]:
        pool = _golden_pool()
        if pool:
            golden_plot["plot_id"] = pool[(day * 7919 + 13) % len(pool)].plot_id
    return golden_plot["plot_id"]


def is_golden(plot):
    return (
        golden_plot["day"] == state.current_day
        and not golden_plot["claimed"]
        and golden_plot["plot_id"] == plot.plot_id
    )


def golden_text():
    ensure_golden()
    if golden_plot["claimed"]:
        return f"Golden plot claimed today: +{GOLDEN_POINTS} practice points."
    plot_id = golden_plot["plot_id"]
    if plot_id is None:
        return ""
    plot = state.plots_by_id[plot_id]
    return f"Golden plot today: {plot.label} (a correct answer earns {GOLDEN_POINTS} practice points)"


def _claim_golden(plot_id, correct):
    ensure_golden()
    if not correct or golden_plot["claimed"] or golden_plot["plot_id"] != plot_id:
        return False
    golden_plot["claimed"] = True
    record_practice("golden", True, points=GOLDEN_POINTS, count_study=False)
    return True


def _validated_golden(raw):
    clean = {"day": -1, "plot_id": None, "claimed": False}
    if not isinstance(raw, dict):
        return clean
    day = raw.get("day")
    if isinstance(day, bool) or not isinstance(day, int) or day < 0 or day > PRACTICE_COUNT_LIMIT:
        return clean
    plot_id = raw.get("plot_id")
    clean["day"] = day
    clean["plot_id"] = plot_id if isinstance(plot_id, str) and plot_id in state.plots_by_id else None
    clean["claimed"] = raw.get("claimed") is True
    return clean


# --- L-14: three small goals a day -----------------------------------------
# Goals are a rotation over the in-game day (no streak: a day with no play
# leaves its goals unfinished and nothing carries over). Each finished goal
# earns two points in the "quests" ledger mode.
QUEST_REWARD_POINTS = 2
QUESTS = {
    "water": ("Water {n} plots", 5),
    "practice": ("Answer {n} questions correctly in the practice games and drills", 8),
    "combo": ("Reach a {n}-in-a-row combo while watering", 3),
    "grammar": ("Water {n} grammar plots", 3),
    "liaison": ("Answer {n} liaison items correctly", 3),
    "review": ("Answer {n} Review questions", 5),
}
QUEST_ORDER = ("water", "practice", "combo", "grammar", "liaison", "review")
QUESTS_PER_DAY = 3
quest_state = {"day": -1, "progress": {}, "done": []}


def quests_for_day(day):
    return [QUEST_ORDER[(day + 2 * i) % len(QUEST_ORDER)] for i in range(QUESTS_PER_DAY)]


def ensure_quests():
    if quest_state["day"] != state.current_day:
        quest_state["day"] = state.current_day
        quest_state["progress"] = {}
        quest_state["done"] = []


def _quest_note(kind, amount=1, absolute=False):
    ensure_quests()
    if kind not in quests_for_day(state.current_day):
        return
    target = QUESTS[kind][1]
    current = quest_state["progress"].get(kind, 0)
    updated = max(current, amount) if absolute else current + amount
    updated = max(0, min(updated, target))
    quest_state["progress"][kind] = updated
    if updated >= target and kind not in quest_state["done"]:
        quest_state["done"].append(kind)
        record_practice("quests", True, points=QUEST_REWARD_POINTS, count_study=False)


def quest_lines():
    """[(text, progress, target, done)] for today's three goals."""
    ensure_quests()
    lines = []
    for kind in quests_for_day(state.current_day):
        template, target = QUESTS[kind]
        done = kind in quest_state["done"]
        lines.append((template.format(n=target), quest_state["progress"].get(kind, 0), target, done))
    return lines


def quest_summary_text():
    done = sum(1 for line in quest_lines() if line[3])
    return f"Daily goals: {done} of {QUESTS_PER_DAY} done"


def _validated_quests(raw):
    clean = {"day": -1, "progress": {}, "done": []}
    if not isinstance(raw, dict):
        return clean
    day = raw.get("day")
    if isinstance(day, bool) or not isinstance(day, int) or day < 0 or day > PRACTICE_COUNT_LIMIT:
        return clean
    clean["day"] = day
    progress = raw.get("progress")
    if isinstance(progress, dict):
        for kind, value in progress.items():
            if kind in QUESTS and not isinstance(value, bool) and isinstance(value, int):
                clean["progress"][kind] = max(0, min(value, QUESTS[kind][1]))
    done = raw.get("done")
    if isinstance(done, list):
        clean["done"] = [k for k in QUEST_ORDER if k in done and k in QUESTS]
    return clean
