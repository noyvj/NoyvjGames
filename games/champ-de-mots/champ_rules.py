"""Le Champ de Mots' fixed numbers and small tables: the spaced-repetition constants, the growth stages, the file names,
the practice-ledger modes and caps and the exam-planner defaults. Pure data. Ask for this file to change a number.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

CATALOG_FILENAME = "fren_combined_catalog.json"
SUPPLEMENTARY_NOTES_FILENAME = "fren_supplementary_notes.json"

# --- Spaced repetition constants (design doc §6) ---------------------------
# Lightweight SM-2-flavoured scheduling: simplicity over academic rigour.
DEFAULT_EASE = 2.5
MIN_EASE = 1.3
MAX_EASE = 3.0
EASE_CORRECT_BONUS = 0.1
EASE_INCORRECT_PENALTY = 0.2

FIRST_INTERVAL_DAYS = 1
SECOND_INTERVAL_DAYS = 3
RESET_INTERVAL_DAYS = 1
BLOOMING_INTERVAL_DAYS = 7
AUTOMATION_INTERVAL_DAYS = 14

# --- Improvement Ideas §2/§3 (2026-09-13 addendum): combo bonus + confidence
# rating. Both are purely additive to the SM-2-flavoured scheduler above --
# every existing caller of schedule_after_review()/FarmState.review() that
# doesn't pass the new keyword arguments gets byte-identical behaviour.
#
# Combo bonus: consecutive correct answers *in the session* (any plot, not a
# single plot's own correct_streak) shave the growth curve's edges off a
# little for whichever plot you just got right -- "genuinely easy items grow
# faster and stop demanding attention sooner" was the explicit ask. Purely
# positive: a wrong answer resets the session combo to zero with no
# additional penalty beyond the normal one below, matching this game's
# no-punishment stance (design doc §3).
COMBO_BONUS_PER_STEP = 0.03
MAX_COMBO_BONUS = 0.4

# Confidence rating: an optional "Sure" / "Not sure" tag the player can put
# on a question before answering. It only ever changes anything on a *wrong*
# answer -- a confident miss represents a more concerning gap than an unsure
# one, so it costs a bit more ease; an unsure miss costs a bit less, since
# the player already flagged the guess as shaky rather than committed to it.
# A correct answer is unaffected either way -- the doc's own wording scopes
# this to "weights the SRS harder against a confident-wrong answer," not to
# rewarding confident-and-correct.
CONFIDENT_WRONG_PENALTY_MULTIPLIER = 1.5
UNSURE_WRONG_PENALTY_MULTIPLIER = 0.5

# --- Growth stages (design doc §3) -----------------------------------------
STAGE_SEED = "seed"
STAGE_SPROUT = "sprout"
STAGE_BUDDING = "budding"
STAGE_BLOOMING = "blooming"
STAGE_AUTOMATED = "automated"

STAGE_ORDER = [STAGE_SEED, STAGE_SPROUT, STAGE_BUDDING, STAGE_BLOOMING, STAGE_AUTOMATED]
STAGE_RANK = {stage: index for index, stage in enumerate(STAGE_ORDER)}

# FREN151 is already finished in real life, so its 11 rows are a catch-up
# zone that is open from the start (design doc §7). Used from Milestone 6.
CATCH_UP_MAX_SEQUENCE = 11


# ===========================================================================
# Practice progress ledger (TODO R2-L1b)
# ===========================================================================
#
# The user's rule: "practice through games should show progress on
# respective topics... it should impact the player score" and "everything
# gives progress to something measured at the top". Every practice mode
# outside the farm's own watering (the four arcade minigames, the gender
# drill, liaison practice, proficiency tests, bonus sentence sections) feeds
# ONE shared ledger through record_practice(): a lifetime correct/total tally
# per mode (its "respective topic" -- Verb Racer is verbs, Boutique Dash is
# clothing, the gender drill is noun gender, and so on), plus capped
# "practice points" that sum into the header's Practice score tile.
#
# Deliberately NOT touched: SRS state. A minigame answer never calls
# state.review() or nudges an interval/next_due (CLAUDE.md Milestone 5's
# stance that only real watering moves the schedule still holds); the ledger
# is a parallel, purely additive measure. Anti-farming: 1 point per correct
# answer, at most PRACTICE_DAILY_CAP points per mode per in-game day and
# PRACTICE_MODE_CAP per mode for good, so a 60-second Blitz can't inflate the
# score no matter how fast it is replayed. Wrong answers count toward the
# accuracy tally but earn nothing. Saved (validated on load) as
# "practice_ledger".

PRACTICE_MODES = {
    "blitz": "Greetings & Basics Blitz",
    "sprint": "Passé Composé Sprint",
    "racer": "Verb Racer",
    "boutique": "Boutique Dash",
    "cafe": "Café Rush",
    "quick": "Quick water",
    "wateropts": "Water options",
    "pairs": "Word Match",
    "gaps": "Grammar Gaps",
    "listenpick": "Listening Pick",
    "wordorder": "Word Order Race",
    "amis": "Faux Amis (false friends)",
    "builder": "Sentence builder",
    "conversation": "Conversation simulator",
    "listening": "Listening practice",
    "placement": "Placement test",
    "gender": "Gender drill (le/la)",
    "liaison": "Liaison practice",
    "proficiency": "Proficiency tests",
    "bonus": "Bonus sentences",
    "golden": "Golden plot of the day",
    "quests": "Daily goals",
    # FS-17 to FS-22: the six exam formats (formats.py), one ledger entry each
    "clock": "Clock reading",
    "truefalse": "True or false reading",
    "rewrite": "Sentence rewriting",
    "pronoun": "Answer with a pronoun",
    "reciprocal": "Reciprocal pronouns",
    "pairq": "Pair questions",
}
# L-17 / L-14: a golden-plot answer and a finished daily goal each earn two
# points instead of one. The caps above still apply, so the most any mode can
# ever add is PRACTICE_MODE_CAP.
PRACTICE_MAX_POINTS_PER_ANSWER = 2
DOUBLE_POINT_MODES = ("golden", "quests")
PRACTICE_DAILY_CAP = 10
PRACTICE_MODE_CAP = 100
PRACTICE_COUNT_LIMIT = 1_000_000  # sanity bound when loading a save


def _blank_practice_entry():
    return {"correct": 0, "total": 0, "points": 0, "day": -1, "day_points": 0}


# ===========================================================================
# L-9 / L-28: exam-date planner and the header exam countdown
# ===========================================================================
#
# The player enters an exam date and a what-if "minutes a day"; the planner
# projects how many plots would be Automated by then, by replaying the REAL
# scheduler (schedule_after_review) over lightweight copies of every plot's
# current state, so the projection can never drift from what the game does.
# It also suggests the minimum daily effort that reaches PLANNER_TARGET_PERCENT.
#
# Assumptions, all stated in the panel: the player advances the in-game day
# once per real day; one answer takes STUDY_BUDDY_SECONDS_PER_REVIEW seconds;
# reviews of already-planted plots come first (most overdue first), leftover
# time plants new ones; and the "cautious" figure gets every
# PLANNER_MISS_EVERY-th answer wrong (the "best case" gets none wrong).
#
# The date itself is a real calendar date, so the day arithmetic uses
# calendar.timegm (Milestone 7 bans the standard date-time module here) and "today"
# comes from study_today(). Saved as "exam_plan" only once a date is set.
# This is a planning aid, not a drill: it never touches SRS state or the
# practice ledger.
PLANNER_MIN_MINUTES = 5
PLANNER_MAX_MINUTES = 120
PLANNER_STEP_MINUTES = 5
PLANNER_DEFAULT_MINUTES = 15
PLANNER_TARGET_PERCENT = 80
PLANNER_MAX_DAYS = 400
PLANNER_MISS_EVERY = 4

# FS-23: the real written exam (from the subject outline). Offered as one click while no date is set; never set for you.
EXAM_DEFAULT_DATE = "2026-11-13"
EXAM_DEFAULT_NOTE = "Fri 13 Nov 2026, online written exam on Moodle, 2 hours"
