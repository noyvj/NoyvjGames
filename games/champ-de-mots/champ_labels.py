"""Fixed wording for the farm (stage icons and labels, legend and status messages, report button labels) and the failure
feedback blurb.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from champ_rules import STAGE_AUTOMATED, STAGE_BLOOMING, STAGE_BUDDING, STAGE_SEED, STAGE_SPROUT
from champ_model import state


# ===========================================================================
# Milestone 4 — the static farm grid UI (design doc §3 and §8)
# ===========================================================================
#
# Deliberately static: the farm is a plain grid of cells, one per plot, and a
# growth stage is just a different sprite and class on the cell. No animation,
# nothing that has to be caught mid-motion for a screenshot. The grid is built
# once at boot and only its cells' text/classes are rewritten afterwards —
# 722 cells is too many to recreate on every answer.

STAGE_ICON = {
    STAGE_SEED: "🟤",
    STAGE_SPROUT: "🌱",
    STAGE_BUDDING: "🌿",
    STAGE_BLOOMING: "🌷",
    STAGE_AUTOMATED: "🌻",
}

STAGE_LABEL = {
    STAGE_SEED: "Seed — planted, not yet watered",
    STAGE_SPROUT: "Sprout — recalled once",
    STAGE_BUDDING: "Budding — recalled across spaced visits",
    STAGE_BLOOMING: "Blooming — holding over long gaps",
    STAGE_AUTOMATED: "Automated — on the sprinkler, back rarely",
}

WILTING_LEGEND = "Drooping — overdue, one watering brings it back"
WEEDS_ICON = "🌾"
WEEDS_LEGEND = "Weeds — a known French mix-up, one correct answer clears it"
AUTOMATED_TOOLTIP_NOTE = "auto-watered"
WEEDS_TOOLTIP_NOTE = "a common mix-up — worth another look"
DUE_NOTE = "ready for water"
NOTHING_DUE_MESSAGE = "Nothing needs water today. The farm is ticking over on its own."
LOCK_NOTE = "opens when row {previous} has all sprouted"
PACE_NOTE = "Water as many or as few as you like. Nothing here expires, and stopping costs nothing."
DUE_MESSAGE_ONE = "1 plot is ready for water today."
DUE_MESSAGE_MANY = "{count} plots are ready for water today."
ROW_DUE_NOTE = "{count} ready"

FEEDBACK = {
    "correct": "Yes — {answer}. This plot is growing.",
    "incorrect": "Not quite — it was {answer}. This plot just needs another water.",
}

# §14.2.4: the report queue this feeds is a new `answer_reports` table in the
# existing Neon/Postgres backend (app/), not the static catalog.
ANSWER_REPORTS_ENDPOINT = "https://noyvjgames.fastapicloud.dev/answer-reports"
REPORT_GAME_ID = "champ-de-mots"
REPORT_BUTTON_LABEL = "I think this should count"
REPORT_SENT_LABEL = "Reported — thanks"

# Milestone 24: a second, independent report type on the same backend table
# and endpoint -- a pronunciation concern isn't "my answer should have
# counted" (AnswerReport's own shape already covers that), it's "this
# catalog text itself might be a mispronunciation trap." Reusing the table
# rather than adding a new one: every required field already fits (a fixed
# marker string stands in for `submitted_answer`, the item's own fr text
# satisfies `marked_correct_answer`'s "at least one" rule), and
# `topic_type="pronunciation"` is enough for a human triaging the queue
# (`GET /answer-reports?topic_type=pronunciation`) to tell the two kinds
# apart without a schema change to the shared backend.
PRONUNCIATION_REPORT_TOPIC_TYPE = "pronunciation"
PRONUNCIATION_REPORT_MARKER = "[pronunciation concern]"
PRONUNCIATION_REPORT_BUTTON_LABEL = "🔊 Report a pronunciation concern"
PRONUNCIATION_REPORT_SENT_LABEL = "Reported — thanks"


# ===========================================================================
# Milestone 10 — the failure feedback blurb (design doc §14.3), Phase 1 only
# ===========================================================================
#
# Phase 1 (this milestone): every field is mechanically template-filled from
# fields the catalog already has -- topic title, grammar rule, the item's own
# fr/en pair, topic_type -- plus this file's own fixed wording. Phase 2 (a
# one-off Claude API call per item, cached in the database) is an explicit
# stretch goal, out of scope here; there is no network call anywhere in this
# section.

FAILURE_BLURB_MEMORY_TIP = {
    "vocab": 'Link "{fr}" to "{en}" with a quick mental image or a similar-sounding English word.',
    "phrase": "Say the whole phrase aloud a few times — phrases stick better as one chunk than word-by-word.",
    "grammar": "Focus on the pattern behind the rule, not just this one example.",
    "phonetic": "Say the letter or symbol and its spoken name aloud together a few times in a row.",
}

# §14.3: explicitly a *generic* per-topic_type template, not per-item content.
FAILURE_BLURB_WHY_IT_MATTERS = {
    "vocab": "This word keeps reappearing in later vocabulary and in sentences built from it.",
    "phrase": "Phrases like this get reused as building blocks in later conversation practice.",
    "grammar": "This rule underlies many sentences later in the syllabus, so it pays off to get it solid now.",
    "phonetic": "Recognising this quickly is foundational for spelling and pronunciation all through the course.",
}


def _blurb_what_it_is(plot):
    """One-line restatement: the `rule` field already covers this for
    grammar items (§14.3, literally); everything else is templated from the
    item's own fr/en pair and its topic title."""
    if plot.topic_type == "grammar":
        return plot.rule or plot.topic_title
    item = plot.items[0]
    return f'"{item["fr"]}" = "{item["en"]}" — from "{plot.topic_title}".'


def _blurb_memory_tip(plot):
    template = FAILURE_BLURB_MEMORY_TIP[plot.topic_type]
    item = plot.items[0]
    return template.format(fr=item.get("fr", ""), en=item.get("en", ""))


def build_failure_blurb(question):
    """The §14.3 card for a question that was just marked wrong: what it is,
    a memory tip, and why it matters. None if the question doesn't map back
    to a real plot (e.g. a hand-built dict in a test)."""
    plot = state.plots_by_id.get(question.get("plot_id"))
    if plot is None:
        return None
    return {
        "what_it_is": _blurb_what_it_is(plot),
        "memory_tip": _blurb_memory_tip(plot),
        "why_it_matters": FAILURE_BLURB_WHY_IT_MATTERS[plot.topic_type],
    }


# Milestone 26: report buttons for tasks 2 and 3 (both always typed). Task 1
# (tile ordering) has no typed answer, so it gets neither -- same rule that
# already keeps a wrong multiple-choice pick in the main panel report-free.
# Bonus sentences aren't plot-backed (they're hand-authored, §14.6), so their
# reports use their own item-id/topic-type scheme rather than the
# plot-lookup one the farm/Review/Proficiency questions share -- see
# BONUS_TILE_REPORT_TOPIC_TYPE / BONUS_SENTENCE_REPORT_TOPIC_TYPE below.
BONUS_TILE_REPORT_TOPIC_TYPE = "bonus_tile"
BONUS_SENTENCE_REPORT_TOPIC_TYPE = "bonus_sentence"
