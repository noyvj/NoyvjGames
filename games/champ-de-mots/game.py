"""Le Champ de Mots — a French-syllabus farming game.

Runs in-browser via Pyodide, per the hub's default stack. Milestone 2: the
plant-state data model and the spaced-repetition scheduler underneath it
(design doc §6). Plots are built straight from the combined FREN151/FREN152
catalog and laid out as one continuous run of rows, sequence 1-23, with no
season break between the two courses.

Design doc §3's wellbeing constraint is enforced here rather than only in the
UI: a plot's visible growth stage only ever moves *up*. An incorrect recall
reschedules the plot sooner (it "needs water again") but never demotes the
plant, never removes it, and never produces a failure state.
"""

import calendar as _calendar
import difflib
import heapq
import json
import random
import re
import unicodedata
import zlib

import narrative_log
from js import document
from pyodide.ffi import create_proxy

# Milestones 27-30: the arcade minigame family lives entirely in its own
# file (minigames.py) -- see that file's module docstring for the full
# wellbeing-constraint-exception rationale (the farm's own no-timer/
# no-animation tests scan only this file and style.css by name, so keeping
# every minigame's timer/animation code out of both files is what lets
# those tests keep passing completely unchanged). A plain `import minigames`
# is tried first -- in the browser, index.html writes minigames.py's source
# onto Pyodide's virtual filesystem before running this file, so the normal
# import machinery finds it on the default sys.path with no extra plumbing.
# The except branch is a pytest-harness fallback only: this file's own
# directory isn't necessarily on sys.path when game.py is loaded by
# importlib file-path (tests/conftest.py's approach), so that path is added
# and the import retried.
try:
    import minigames
except ImportError:  # pragma: no cover -- exercised by every test run
    import os as _os
    import sys as _sys

    _GAME_DIR = _os.path.dirname(_os.path.abspath(__file__))
    if _GAME_DIR not in _sys.path:
        _sys.path.insert(0, _GAME_DIR)
    import minigames

# JS calls a minigame's countdown tick by name via
# `pyodide.globals.get("...")` (the same lookup shared/save-widget.js uses
# for get_state()/load_state()) -- that only ever sees names bound in *this*
# module's namespace, not minigames.py's own, so each tick function needs a
# plain re-export here. This is a name binding, not a call to any of the
# banned timer APIs, so it doesn't trip test_nothing_in_the_game_runs_on_a_timer's
# substring scan over this file.
blitz_tick = minigames.blitz_tick
racer_tick = minigames.racer_tick
boutique_tick = minigames.boutique_tick
cafe_tick = minigames.cafe_tick
sprint_tick = minigames.sprint_tick
pairs_tick = minigames.pairs_tick
gaps_tick = minigames.gaps_tick
listenpick_tick = minigames.listenpick_tick
wordorder_tick = minigames.wordorder_tick
amis_tick = minigames.amis_tick
minigame_run_active = minigames.any_timed_run_active

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


def _read_json_asset(filename, window_attr):
    """The page's boot script fetches each JSON asset and hands it to Python
    as a window global before running this file; the pytest harness sets
    the same attribute on its fake `js` module. A filesystem fallback keeps
    the module importable outside both. Shared by the catalog and the
    supplementary-notes file below -- same loading contract, different
    filename/global name."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, window_attr, None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, filename), encoding="utf-8") as handle:
        return handle.read()


def _read_catalog_json():
    return _read_json_asset(CATALOG_FILENAME, "CATALOG_JSON")


def _read_supplementary_notes_json():
    return _read_json_asset(SUPPLEMENTARY_NOTES_FILENAME, "SUPPLEMENTARY_NOTES_JSON")


CATALOG = json.loads(_read_catalog_json())

CHAPTER_TITLES = {str(c["number"]): c["title"] for c in CATALOG.get("chapters", [])}

# Improvement Ideas §4: optional cultural/usage notes, sourced from the
# slideshow cross-check's supplementary file (2026-09-13 merge). Keyed by
# `sequence` (a week can have at most one note in the source data today;
# a list-of-notes-per-sequence would be the natural extension if that ever
# changes). A missing/unparseable file degrades to "no cultural notes"
# rather than crashing the whole game -- this is optional flavor, not core
# gameplay, the same posture _dispatch_report() already takes for a failed
# report send.
try:
    SUPPLEMENTARY_NOTES = json.loads(_read_supplementary_notes_json())
except (ValueError, OSError, NameError):
    # NameError included defensively: `_read_json_asset()`'s filesystem
    # fallback (for running outside both Pyodide and the pytest harness)
    # reads `__file__`, which a plain `pyodide.runPythonAsync(code)` string
    # exec never defines -- if the boot script's own window global for this
    # file is ever missing again (as it genuinely was, live-breaking the
    # whole page on load, before this file's own boot script was fixed to
    # actually set window.SUPPLEMENTARY_NOTES_JSON), this must degrade to
    # "no cultural notes/liaison drill/pronunciation notes" exactly as
    # already documented above, not crash the entire module import.
    SUPPLEMENTARY_NOTES = {}

CULTURAL_NOTES_BY_SEQUENCE = {
    entry["sequence"]: entry["note"]
    for entry in SUPPLEMENTARY_NOTES.get("cultural_notes", [])
}

# Improvement Ideas addendum: liaison/elision as a real practice type. Unlike
# every other practice question, these aren't generated from a plot -- they're
# hand-authored (same posture as Milestone 13's bonus sentences: some content
# genuinely needs a human, not a mechanical recombination of catalog facts),
# grounded one-for-one in the TTS pronunciation watchlist half of the same
# supplementary-notes file (the other half of that file, cultural_notes, is
# already wired up above). Not every watchlist entry became a question --
# "travailler is commonly mispronounced" (sequence 4) is a tutor's listen-check
# flag, not a testable mechanical fact, so it stayed a note rather than being
# forced into a quiz.
LIAISON_DRILL_QUESTIONS = SUPPLEMENTARY_NOTES.get("liaison_drill", [])

# Milestone 24: a mispronunciation-risk report button. Most of the TTS
# watchlist's 11 entries describe a *rule* (liaison, an ending pattern) with
# no single catalog item to attach a note to -- those are already covered
# abstractly by the liaison drill above. A handful, though, name one exact
# catalog item by its own fr text ("travailler", flagged by the tutor as
# commonly mispronounced by learners) -- computed by membership rather than
# hardcoded, so a future catalog/watchlist edit that makes another entry
# resolve cleanly picks it up automatically instead of needing a second,
# parallel list kept in sync by hand.
_CATALOG_FR_TEXTS = {
    item["fr"]
    for week in CATALOG["weeks"]
    for topic in week["topics"]
    for item in topic.get("items", [])
    if item.get("fr")
}
PRONUNCIATION_RISK_NOTES = {
    entry["item"]: entry["note"]
    for entry in SUPPLEMENTARY_NOTES.get("tts_watchlist", [])
    if entry["item"] in _CATALOG_FR_TEXTS
}


class Plot:
    """One plot of the farm: a single fact you are trying to grow.

    Granularity follows the design doc's own wording — "a new unit unlocks a
    batch of plots (vocab words, a conjugation pattern, a grammar rule)". So
    vocab/phrase/phonetic get one plot per item, while a grammar topic is a
    single plot whose example items feed its question variants (§5).
    """

    def __init__(self, plot_id, topic, week, items, label):
        self.plot_id = plot_id
        self.topic_id = topic["id"]
        self.topic_type = topic["topic_type"]
        self.topic_title = topic["title"]
        self.rule = topic.get("rule")
        self.items = items
        self.label = label

        self.sequence = week["sequence"]
        self.course = week["course"]
        self.week = week["week"]
        self.chapter = week["chapter"]

        # SRS state (§6)
        self.ease_factor = DEFAULT_EASE
        self.interval_days = 0
        self.last_reviewed = None
        self.next_due = None
        self.correct_streak = 0
        self.stage = STAGE_SEED

        # Improvement Ideas §2: "weeds" -- a specific-error overlay, not a
        # growth stage. Set the moment a wrong answer matches a known
        # commonly-confused counterpart (WEED_CONFUSIONS below), cleared on
        # the next correct answer, same "one watering brings it back" rule
        # wilting already follows. Independent of `stage`, which never
        # regresses.
        self.in_weeds = False
        # L-18: consecutive wrong answers on this plot (cleared by a correct
        # one). At LEECH_THRESHOLD it becomes a "stubborn weed" (see below).
        self.fail_run = 0
        # 2026-10-08 watering rule: the in-game day of this plot's last FULL
        # watering (the first correct answer for it on a day, from any
        # plot-linked activity), saved with the plot. `nudged_day` is the day
        # of its last nudge (a later correct answer the same day); it is
        # transient session state and never saved (see water_plot()).
        self.last_watered = None
        self.nudged_day = None

    @property
    def is_grammar_rule(self):
        return self.topic_type == "grammar"


class Row:
    """One row of the farm — one syllabus week, keyed by its sequence number."""

    def __init__(self, week, plot_ids):
        self.sequence = week["sequence"]
        self.course = week["course"]
        self.week = week["week"]
        self.chapter = week["chapter"]
        self.chapter_title = CHAPTER_TITLES.get(str(week["chapter"]), "")
        self.plot_ids = plot_ids

    @property
    def chapter_label(self):
        chapter = self.chapter
        prefix = "Bridge" if str(chapter) == "Bridge" else f"Ch. {chapter}"
        return f"{prefix} — {self.chapter_title}" if self.chapter_title else prefix

    @property
    def label(self):
        return f"{self.sequence}. {self.course} wk {self.week}"


def candidate_stage(plot):
    """The stage the plot's current scheduling state would justify."""
    if plot.last_reviewed is None or plot.correct_streak == 0:
        return STAGE_SEED
    if plot.interval_days >= AUTOMATION_INTERVAL_DAYS:
        return STAGE_AUTOMATED
    if plot.interval_days >= BLOOMING_INTERVAL_DAYS:
        return STAGE_BLOOMING
    if plot.correct_streak >= 2:
        return STAGE_BUDDING
    return STAGE_SPROUT


def is_due(plot, day):
    """A plot needs water today if it has never been watered, or its interval
    has elapsed."""
    if plot.next_due is None:
        return True
    return day >= plot.next_due


def is_wilting(plot, day):
    """Overdue, not failing. A seed has no plant to droop, so it never wilts —
    it is simply waiting to be planted."""
    if plot.next_due is None or plot.last_reviewed is None:
        return False
    return day > plot.next_due


def schedule_after_review(plot, correct, day, combo=0, confidence=None):
    """Apply one review outcome to a plot's SRS state (design doc §6).

    `combo` (a session-wide consecutive-correct count, not this plot's own
    correct_streak) and `confidence` ("sure" | "unsure" | None) are both
    optional and default to no-ops, so every pre-existing call site keeps
    its exact prior behaviour."""
    if correct:
        plot.correct_streak += 1
        if plot.correct_streak == 1:
            plot.interval_days = FIRST_INTERVAL_DAYS
        elif plot.correct_streak == 2:
            plot.interval_days = SECOND_INTERVAL_DAYS
        else:
            grown = max(
                plot.interval_days + 1, int(round(plot.interval_days * plot.ease_factor))
            )
            combo_bonus = 1 + min(MAX_COMBO_BONUS, max(0, combo) * COMBO_BONUS_PER_STEP)
            plot.interval_days = max(plot.interval_days + 1, int(round(grown * combo_bonus)))
        plot.ease_factor = min(MAX_EASE, plot.ease_factor + EASE_CORRECT_BONUS)
    else:
        plot.correct_streak = 0
        plot.interval_days = RESET_INTERVAL_DAYS
        penalty = EASE_INCORRECT_PENALTY
        if confidence == "sure":
            penalty *= CONFIDENT_WRONG_PENALTY_MULTIPLIER
        elif confidence == "unsure":
            penalty *= UNSURE_WRONG_PENALTY_MULTIPLIER
        plot.ease_factor = max(MIN_EASE, plot.ease_factor - penalty)

    plot.last_reviewed = day
    plot.next_due = day + plot.interval_days

    # Monotonic: a plant never visibly regresses (§3).
    candidate = candidate_stage(plot)
    if STAGE_RANK[candidate] > STAGE_RANK[plot.stage]:
        plot.stage = candidate
    return plot


class FarmState:
    """The whole farm: every plot, every row, and what day it is."""

    def __init__(self, catalog):
        self.catalog = catalog
        self.current_day = 0
        self.plots = []
        self.plots_by_id = {}
        self.rows = []
        # Flat, syllabus-ordered index of every topic, used by the question
        # generator to reach "the same or a nearby topic" for distractors (§5).
        self.topic_records = []
        self.topic_pos = {}
        # Recomputed lazily — render() asks about the lock state once per plot,
        # 722 times a repaint, so it cannot be an O(rows) walk each time.
        self._unlocked_cache = None
        self._build_farm()

    def _build_farm(self):
        for week in self.catalog["weeks"]:
            plot_ids = []
            for topic in week["topics"]:
                self.topic_pos[topic["id"]] = len(self.topic_records)
                self.topic_records.append(
                    {"sequence": week["sequence"], "topic": topic, "items": topic["items"]}
                )
                if topic["topic_type"] == "grammar":
                    plot = Plot(
                        plot_id=topic["id"],
                        topic=topic,
                        week=week,
                        items=list(topic["items"]),
                        label=topic["title"],
                    )
                    self._register(plot, plot_ids)
                else:
                    for index, item in enumerate(topic["items"]):
                        plot = Plot(
                            plot_id=f"{topic['id']}-i{index:02d}",
                            topic=topic,
                            week=week,
                            items=[item],
                            label=item["fr"],
                        )
                        self._register(plot, plot_ids)
            self.rows.append(Row(week, plot_ids))

    def _register(self, plot, plot_ids):
        self.plots.append(plot)
        self.plots_by_id[plot.plot_id] = plot
        plot_ids.append(plot.plot_id)

    # --- queries -----------------------------------------------------------
    def row_by_sequence(self, sequence):
        for row in self.rows:
            if row.sequence == sequence:
                return row
        return None

    def row_plots(self, sequence):
        row = self.row_by_sequence(sequence)
        if row is None:
            return []
        return [self.plots_by_id[pid] for pid in row.plot_ids]

    def is_row_unlocked(self, sequence):
        """L4a (2026-09-20): the §7 pacing gate this method used to enforce —
        a row opened only once every plot in the row before it had reached at
        least Sprout — has been removed outright, not just loosened. A player
        joining weeks into the real course was being locked out of syllabus
        content their classmates already covered, which defeated the whole
        point of a study tool. Every row is unlocked from the very first day
        now, unconditionally.

        The method (and the cache/invalidation machinery below it) is kept
        exactly as it was rather than deleted, on purpose: well over a dozen
        call sites across this file and minigames.py ask "is this row's
        content available" as their one real question, and every one of them
        keeps working unchanged because the answer is just always "yes" now.
        See this file's own CLAUDE.md, the L4a build note, for the full
        reasoning and for what downstream UI (the lock note, `.row--locked`/
        `.plot--locked` CSS, the disabled proficiency/bonus buttons) this
        leaves permanently dormant rather than torn out.
        """
        if self._unlocked_cache is None:
            self._unlocked_cache = self._compute_unlocked()
        return sequence in self._unlocked_cache

    def _compute_unlocked(self):
        # L4a: no gate. Every row is open from the start, regardless of any
        # other row's stage — CATCH_UP_MAX_SEQUENCE stays defined below as a
        # content-boundary fact (FREN151 ends at sequence 11), it just no
        # longer does any gating work here.
        return {row.sequence for row in self.rows}

    def invalidate_unlocks(self):
        """Anything that can change a plot's stage has to drop the cache."""
        self._unlocked_cache = None

    def available_plots(self):
        return [p for p in self.plots if self.is_row_unlocked(p.sequence)]

    def due_plots(self):
        return [p for p in self.available_plots() if is_due(p, self.current_day)]

    def next_due_plot(self):
        due = self.due_plots()
        if not due:
            return None
        # Longest-overdue first; unwatered seeds count as maximally overdue so
        # new plots get planted rather than starved by an endless review queue.
        return min(due, key=lambda p: (p.next_due if p.next_due is not None else -1))

    # --- mutations ---------------------------------------------------------
    def review(self, plot_id, correct, day=None, combo=0, confidence=None):
        plot = self.plots_by_id.get(plot_id)
        if plot is None:
            return None
        self.invalidate_unlocks()
        return schedule_after_review(
            plot,
            correct,
            self.current_day if day is None else day,
            combo=combo,
            confidence=confidence,
        )

    def advance_day(self, days=1):
        self.current_day += max(0, int(days))
        return self.current_day


state = FarmState(CATALOG)


# ===========================================================================
# Milestone 3 — runtime question generator (design doc §5)
# ===========================================================================
#
# Every prompt a player ever sees is assembled here, at runtime, out of the
# catalog's raw fr/en facts plus this file's own fixed instruction strings.
# Nothing is ever read back out of the workbook: the catalog deliberately
# holds only vocabulary pairs and grammar facts, and the generator only ever
# recombines those (translate either direction, blank a word out of a fact,
# swap the pronoun on a conjugation table, match a letter to its spoken
# name). That is the whole reason this approach is safe, so no other kind of
# content may be introduced here — see §4.

QUESTION_CHOICE_COUNT = 4
DISTRACTOR_COUNT = QUESTION_CHOICE_COUNT - 1
DISTRACTOR_POOL_SIZE = 14

# Improvement Ideas §3: adaptive distractor difficulty. Once a plot has
# survived a couple of spaced recalls (Budding or further), its multiple-
# choice distractors get biased toward near-spelling/near-synonym matches
# to the real answer instead of the plain uniform sample newer plots get --
# a Seed plot still draws evenly across the whole nearby-topic pool, so
# early practice stays approachable rather than confusing from the start.
ADAPTIVE_DISTRACTOR_MIN_STAGE = STAGE_BUDDING
ADAPTIVE_DISTRACTOR_POOL_MULTIPLIER = 3


def _answer_similarity(value, answer):
    """0-1 spelling/word similarity between a candidate distractor and the
    real answer, used only to rank which distractors are "tricky" -- never
    to decide correctness (check_answer's own leniency is unrelated)."""
    return difflib.SequenceMatcher(
        None, normalize_answer(str(value)), normalize_answer(str(answer))
    ).ratio()


NEARBY_TOPIC_SPAN = 4  # topics either side ≈ the same and adjacent weeks
BLANK_MARKER = "_____"
MAX_TYPED_ANSWER_LENGTH = 32

# Variant ids. The design floor is 3-4 plausible variants per plot so that
# watering the same plot twice rarely produces an identical question.
V_FR_EN_CHOICE = "fr_to_en_choice"
V_EN_FR_CHOICE = "en_to_fr_choice"
V_FR_EN_TYPED = "fr_to_en_typed"
V_EN_FR_TYPED = "en_to_fr_typed"
V_SYMBOL_NAME_CHOICE = "symbol_to_name_choice"
V_NAME_SYMBOL_CHOICE = "name_to_symbol_choice"
V_SYMBOL_NAME_TYPED = "symbol_to_name_typed"
V_NAME_SYMBOL_TYPED = "name_to_symbol_typed"
V_EXAMPLE_FR_EN = "example_fr_to_en"
V_EXAMPLE_EN_FR = "example_en_to_fr"
V_BLANK_WORD = "blank_word"
V_BLANK_ENDING = "blank_ending"
V_CONJUGATION_SWAP = "conjugation_swap"
V_GENDER_TAG = "gender_tag"

INSTRUCTIONS = {
    V_FR_EN_CHOICE: "Which English matches this?",
    V_EN_FR_CHOICE: "Which French matches this?",
    V_FR_EN_TYPED: "Type the English for this.",
    V_EN_FR_TYPED: "Type the French for this.",
    V_SYMBOL_NAME_CHOICE: "How is this said aloud?",
    V_NAME_SYMBOL_CHOICE: "Which letter or symbol is this?",
    V_SYMBOL_NAME_TYPED: "Type how this is said aloud.",
    V_NAME_SYMBOL_TYPED: "Type the letter or symbol this names.",
    V_EXAMPLE_FR_EN: "Which English matches this example?",
    V_EXAMPLE_EN_FR: "Which French matches this example?",
    V_BLANK_WORD: "Fill the gap.",
    V_BLANK_ENDING: "Finish the ending.",
    V_CONJUGATION_SWAP: "Which form goes with this pronoun?",
    V_GENDER_TAG: "Is it le or la?",
    # Progressive format (2026-10-08): the typed form of a fill-the-gap question,
    # shown for plots that have grown (see question_format_percent()).
    V_BLANK_WORD + "_typed": "Type the word that fills the gap.",
    V_CONJUGATION_SWAP + "_typed": "Type the form that goes with this pronoun.",
}

# Improvement Ideas addendum: gender-tagging drill -- masc/fem tested
# separately from meaning. Only a noun whose own catalog text leads with an
# unambiguous "le "/"la " article can be drilled this way -- an elided "l'"
# doesn't reveal its gender at all, so those items are left out rather than
# guessed at.
GENDER_TAG_PATTERN = re.compile(r"^(le|la)\s+(\S.*)$")


def gender_tag_parts(fr_text):
    """(article, bare_noun) for an unambiguously gendered noun, else None."""
    match = GENDER_TAG_PATTERN.match(fr_text)
    return (match.group(1), match.group(2)) if match else None


# The six-person set, plus the shared forms and reflexive/elided spellings the
# catalog actually uses. Longest first so "il/elle/on" wins over "il".
PRONOUN_FORMS = [
    "il/elle/on",
    "ils/elles",
    "il/elle",
    "je",
    "j'",
    "tu",
    "il",
    "elle",
    "on",
    "nous",
    "vous",
    "ils",
    "elles",
]

# Determiners and other function words worth blanking out in their own right —
# for a gender/article or possessive rule, the little word *is* the point.
FUNCTION_WORDS = {
    "un", "une", "des", "le", "la", "les", "l'", "du", "de", "d'",
    "au", "aux", "à", "ce", "cet", "cette", "ces", "mon", "ma", "mes",
    "ton", "ta", "tes", "son", "sa", "ses", "notre", "nos", "votre", "vos",
    "leur", "leurs", "c'est", "il", "elle", "on", "y", "en", "ne", "pas",
    "plus", "moins", "aussi", "très", "quel", "quelle", "quels", "quelles",
}

ARTICLE_PREFIXES = ("a ", "an ", "the ", "to ", "some ")


def strip_parentheticals(text):
    """Drop the catalog's parenthetical asides, e.g. "j'imite (je + imite)"."""
    return re.sub(r"\s*\([^)]*\)", "", str(text)).strip()


def normalize_answer(text, fold_accents=True):
    """Case-, punctuation-insensitive form used for comparisons, with accent
    folding as an opt-out rather than a given (§14.2's accent-sensitivity
    toggle: default ON in the live game, via `check_answer`'s
    `accent_sensitive` parameter — this function's own default stays "fold",
    unchanged from Milestone 3, so every existing caller that doesn't pass
    the new argument keeps behaving exactly as it always has).
    """
    text = str(text)
    if fold_accents:
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("’", "'").replace("‘", "'")
    # FY-8 sweep (2026-10-08): the ligatures have no key on most keyboards and
    # the usual fallback is the two letters, so "oeuf" is "œuf" and "soeur"
    # is "sœur" whatever the accent setting says; a "/" has the same worth
    # with or without spaces round it ("I/you/he" is "I / you / he").
    text = text.replace("œ", "oe").replace("Œ", "oe").replace("æ", "ae").replace("Æ", "ae")
    text = re.sub(r"\s*/\s*", " / ", text)
    # Answer-report review 2026-10-08 (GP-10): an internal comma, semicolon
    # or colon and a hyphen or dash are not part of what is being tested --
    # "Hello my name is Léa" is "Hello, my name is Léa.", "so so" is
    # "so-so", "quatre vingt dix" is "quatre-vingt-dix". They compare as
    # plain word breaks on both sides.
    text = re.sub(r"[,;:\-\u2010\u2011\u2013\u2014]", " ", text)
    text = re.sub(r"\s+", " ", text.casefold()).strip()
    return text.strip(" .!?¡¿\"«»")


MAX_VERB_FORM_TOKENS = 3


def split_pronoun(text):
    """("nous", "parlons") for a single-person conjugated item, else None.

    The rest has to look like one person's form: a couple of words at most
    (room for reflexives and compound tenses) and no "/" separator. Some
    catalog items pack a whole table into one string ("je bois / tu bois / il
    boit"); those are facts to translate, not one person to swap a pronoun on.
    """
    cleaned = strip_parentheticals(text)
    lowered = cleaned.casefold()
    for pronoun in PRONOUN_FORMS:
        if pronoun.endswith("'"):
            matched = lowered.startswith(pronoun)
            rest = cleaned[len(pronoun):].strip() if matched else ""
        else:
            matched = lowered.startswith(pronoun + " ")
            rest = cleaned[len(pronoun) + 1:].strip() if matched else ""
        if not matched or not rest:
            continue
        if "/" in rest or len(rest.split()) > MAX_VERB_FORM_TOKENS:
            return None
        return cleaned[: len(pronoun)], rest
    return None


def is_conjugation_plot(plot):
    """A grammar plot whose examples are a person-by-person verb table."""
    if plot.topic_type != "grammar":
        return False
    splits = [split_pronoun(item["fr"]) for item in plot.items]
    splits = [s for s in splits if s]
    if len(splits) < 3:
        return False
    return len({p.casefold() for p, _ in splits}) >= 2


UNBLANKABLE_CHARS = set("[]{}+<>")
TRAILING_PUNCTUATION = ".,;:!?"


def _split_trailing_punctuation(token):
    stripped = token.rstrip(TRAILING_PUNCTUATION)
    return stripped, token[len(stripped):]


def _is_blankable(token):
    core, _ = _split_trailing_punctuation(token)
    if len(core) < 2 or UNBLANKABLE_CHARS & set(core):
        return False
    return sum(1 for ch in core if ch.isalpha()) >= 2


# A trailing "+ <slot>" marks where a word of a given kind would go in a live
# sentence ("Je suis + [occupation]", "assez + adjective") rather than being
# part of the fact itself, so it is never the word to hide — asking someone to
# recall "adjective" is asking for metalanguage, not French. Anchored to the
# end of the string on purpose: the catalog also uses "+" mid-string as real
# rule notation ("à + le → au"), where the word after it *is* the lesson.
TEMPLATE_SLOT = re.compile(r"\s\+\s(?:\[[^\]]*\]|\S+)\s*$")


def blank_target(text):
    """Pick the word worth hiding in a fact, and return (blanked, answer).

    Function words go first — an article or possessive rule is *about* the
    little word — and otherwise the rightmost real word is hidden, since that
    is the content word in practice. Bracketed placeholders the catalog uses
    for open slots are never chosen, and trailing punctuation stays visible
    so the gap reads as a gap rather than as a typing puzzle.

    An item built around a whitespace-bounded "/" is refused outright, because
    neither shape the catalog uses it in can produce a sensible gap. Where "/"
    joins whole alternate phrasings ("Comment vas-tu? / Ça va?"), blanking a
    word inside one while the other sits fully visible next to it is a garbled
    prompt ("Comment vas-tu? / Ça _____?"). Where it joins single-word variants
    ("australien / australienne"), the alternation *is* the entire item, so
    hiding it — as one unit or as one of its halves — leaves a prompt that is
    nothing but the gap, with four gendered pairs to choose between and no clue
    which. Either way the item is better carried by its direct translate/typed
    variants, which already accept both sides of a "/" (`answer_alternatives`).
    A "/" inside a single token, like the catalog's own "[places/attractions]"
    placeholder, is part of that word and falls through to the normal path.
    """
    stripped = strip_parentheticals(text)
    if re.search(r"\s/\s", stripped):
        return None

    # A trailing template slot stays visible in the prompt but is set aside so
    # it can never be chosen as the answer.
    slot = TEMPLATE_SLOT.search(stripped)
    tail = ""
    if slot:
        tail = stripped[slot.start():]
        stripped = stripped[: slot.start()].strip()

    tokens = stripped.split()
    if len(tokens) < 2:
        return None

    index = None
    if tokens[0].casefold() in FUNCTION_WORDS and _is_blankable(tokens[0]):
        index = 0
    else:
        blankable = [i for i, token in enumerate(tokens) if _is_blankable(token)]
        if not blankable:
            return None
        cores = [_split_trailing_punctuation(t)[0].casefold() for t in tokens]
        # Content words make better gaps than the pronouns and particles
        # around them — several catalog items pack a whole verb table into one
        # string, and blanking a form there is a real question where blanking
        # "il" is barely one.
        content = [i for i in blankable if cores[i] not in FUNCTION_WORDS]
        candidates = content or blankable
        # Prefer a word that appears only once, so hiding it really hides it.
        unique = [i for i in candidates if cores.count(cores[i]) == 1]
        index = (unique or candidates)[-1]

    answer, _trail = _split_trailing_punctuation(tokens[index])
    target = answer.casefold()
    blanked = []
    for token in tokens:
        core, trail = _split_trailing_punctuation(token)
        # If the same word recurs, every occurrence becomes the gap — the
        # answer must never be readable off the prompt.
        blanked.append(BLANK_MARKER + trail if core.casefold() == target else token)
    return " ".join(blanked) + tail, answer


def _common_stem(forms):
    if len(forms) < 2:
        return ""
    stem = forms[0]
    for form in forms[1:]:
        while stem and not form.casefold().startswith(stem.casefold()):
            stem = stem[:-1]
        if not stem:
            return ""
    # Every form must actually extend the stem, or there is no ending to blank.
    if any(len(form) <= len(stem) for form in forms):
        return ""
    return stem


def conjugation_forms(plot):
    """[(pronoun, form)] for a conjugation table, in catalog order."""
    return [split for split in (split_pronoun(i["fr"]) for i in plot.items) if split]


def _ending_split(plot):
    """(stem, [(pronoun, ending)]) when a table's forms share a stem."""
    entries = conjugation_forms(plot)
    stem = _common_stem([form for _, form in entries])
    if len(stem) < 2:
        return None, []
    return stem, [(pronoun, form[len(stem):]) for pronoun, form in entries]


# --- distractor pools ------------------------------------------------------


def nearby_items(farm, plot):
    """Items from the plot's own topic first, then outward through the
    syllabus — the "same or a nearby topic" rule from §5."""
    pos = farm.topic_pos.get(plot.topic_id)
    if pos is None:
        return []
    records = farm.topic_records
    out = list(records[pos]["items"])
    for delta in range(1, NEARBY_TOPIC_SPAN + 1):
        for neighbour in (pos - delta, pos + delta):
            if 0 <= neighbour < len(records):
                out.extend(records[neighbour]["items"])
    return out


def _ordered_pool(values, exclude):
    """Closest-first, de-duplicated, capped — the generator then samples from
    this small plausible pool so the distractor set re-rolls every watering."""
    seen = {normalize_answer(value) for value in exclude}
    seen.discard("")
    pool = []
    for value in values:
        value = str(value).strip()
        key = normalize_answer(value)
        if not key or key in seen:
            continue
        seen.add(key)
        pool.append(value)
        if len(pool) >= DISTRACTOR_POOL_SIZE:
            break
    return pool


def _raw_pool(farm, plot, field, answer):
    return _ordered_pool((item.get(field, "") for item in nearby_items(farm, plot)), [answer])


def _target_pool(farm, plot, answer):
    values = []
    for item in nearby_items(farm, plot):
        blanked = blank_target(item["fr"])
        if blanked:
            values.append(blanked[1])
    return _ordered_pool(values, [answer])


def _form_pool(farm, plot, answer):
    """The other people of the same verb are the most plausible distractors
    there are, so a full table never reaches outside itself."""
    own = [s[1] for s in (split_pronoun(i["fr"]) for i in plot.items) if s]
    pool = _ordered_pool(own, [answer])
    if _enough(pool):
        return pool
    nearby = [s[1] for s in (split_pronoun(i["fr"]) for i in nearby_items(farm, plot)) if s]
    return _ordered_pool(own + nearby, [answer])


def _ending_pool(plot, answer):
    _, entries = _ending_split(plot)
    return _ordered_pool([ending for _, ending in entries], [answer])


def nearby_strings(farm, plot):
    """Every string the generator is allowed to use as a distractor for this
    plot: nearby raw facts plus the fragments derived from them."""
    pool = set()
    for item in nearby_items(farm, plot):
        pool.add(str(item.get("fr", "")).strip())
        pool.add(str(item.get("en", "")).strip())
        blanked = blank_target(item["fr"])
        if blanked:
            pool.add(blanked[1])
        split = split_pronoun(item["fr"])
        if split:
            pool.add(split[1])
    _, entries = _ending_split(plot)
    pool.update(ending for _, ending in entries)
    pool.discard("")
    return pool


# --- variant availability --------------------------------------------------


def _is_typable(text):
    answer = strip_parentheticals(text)
    return bool(answer) and len(answer) <= MAX_TYPED_ANSWER_LENGTH


def _typable_items(plot, field, ascii_only=False):
    items = [i for i in plot.items if _is_typable(i[field])]
    if ascii_only:
        items = [i for i in items if str(i[field]).isascii()]
    return items


def _enough(pool):
    return len(pool) >= DISTRACTOR_COUNT


def variants_for(plot, farm=None):
    """The pool of question variants this plot can actually produce."""
    if getattr(plot, "_variants", None) is not None:
        return plot._variants

    farm = state if farm is None else farm
    phonetic = plot.topic_type == "phonetic"
    grammar = plot.topic_type == "grammar"
    item = plot.items[0]
    variants = []

    if grammar:
        if _enough(_raw_pool(farm, plot, "en", item["en"])):
            variants.append(V_EXAMPLE_FR_EN)
        if _enough(_raw_pool(farm, plot, "fr", item["fr"])):
            variants.append(V_EXAMPLE_EN_FR)
    else:
        if _enough(_raw_pool(farm, plot, "en", item["en"])):
            variants.append(V_SYMBOL_NAME_CHOICE if phonetic else V_FR_EN_CHOICE)
        if _enough(_raw_pool(farm, plot, "fr", item["fr"])):
            variants.append(V_NAME_SYMBOL_CHOICE if phonetic else V_EN_FR_CHOICE)
        if not phonetic and gender_tag_parts(item["fr"]):
            variants.append(V_GENDER_TAG)

    # Fill-in-the-blank: §5 assigns it to grammar rules, and it extends
    # naturally to multi-word expressions, where blanking one word is a far
    # better prompt than asking someone to type a whole sentence back.
    blankable = [i for i in plot.items if blank_target(i["fr"])]
    if grammar or (blankable and len(strip_parentheticals(item["fr"]).split()) >= 3):
        if blankable and _enough(_target_pool(farm, plot, "")):
            variants.append(V_BLANK_WORD)

    if grammar and is_conjugation_plot(plot):
        if _enough(_form_pool(farm, plot, "")):
            variants.append(V_CONJUGATION_SWAP)
        if _enough(_ending_pool(plot, "")):
            variants.append(V_BLANK_ENDING)

    if _typable_items(plot, "en"):
        variants.append(V_SYMBOL_NAME_TYPED if phonetic else V_FR_EN_TYPED)
    # Typing an accented character back is only a real test when accents aren't
    # the thing being taught, so the phonetic accents topic opts out of it.
    if _typable_items(plot, "fr", ascii_only=phonetic):
        variants.append(V_NAME_SYMBOL_TYPED if phonetic else V_EN_FR_TYPED)

    plot._variants = variants
    return variants


# --- generation ------------------------------------------------------------


def _context_line(plot):
    return f"{plot.course} wk {plot.week} · {plot.topic_title}"


def _choice_question(plot, variant, prompt, answer, pool, rng, note=None):
    candidate_pool = pool
    if len(pool) > DISTRACTOR_COUNT and (
        STAGE_RANK[plot.stage] >= STAGE_RANK[ADAPTIVE_DISTRACTOR_MIN_STAGE]
    ):
        ranked = sorted(pool, key=lambda value: _answer_similarity(value, answer), reverse=True)
        hard_pool_size = max(
            DISTRACTOR_COUNT, DISTRACTOR_COUNT * ADAPTIVE_DISTRACTOR_POOL_MULTIPLIER
        )
        candidate_pool = ranked[:hard_pool_size]
    distractors = rng.sample(candidate_pool, DISTRACTOR_COUNT)
    choices = distractors + [answer]
    rng.shuffle(choices)
    return {
        "plot_id": plot.plot_id,
        "variant": variant,
        "topic_type": plot.topic_type,
        "context": _context_line(plot),
        "instruction": INSTRUCTIONS[variant],
        "prompt": prompt,
        "note": note,
        "mode": "choice",
        "choices": choices,
        "answer": answer,
    }


def _typed_question(plot, variant, prompt, answer, note=None):
    return {
        "plot_id": plot.plot_id,
        "variant": variant,
        "topic_type": plot.topic_type,
        "context": _context_line(plot),
        "instruction": INSTRUCTIONS[variant],
        "prompt": prompt,
        "note": note,
        "mode": "typed",
        # Deliberately the raw catalog string, not a rewritten one: what the
        # player is shown on reveal stays verbatim catalog text, and the
        # leniency (parentheticals, accents, articles) lives in check_answer.
        "choices": [],
        "answer": str(answer).strip(),
    }


# ---------------------------------------------------------------------------
# Progressive question format (2026-10-08)
# ---------------------------------------------------------------------------
# A plot that has never been watered always starts with multiple choice. As its
# comprehension grows (its growth stage first, then its correct streak and
# ease factor) typed answers appear more and more often, until a mastered plot
# is mostly typed. Deterministic: whether a given question is typed is decided
# by a fixed hash of the plot's own scheduling state against its typed share,
# so there is no new randomness (the variant is still picked with the caller's
# seeded generator, exactly as before). The "Always multiple choice" setting
# switches the whole thing off.
ALWAYS_MULTIPLE_CHOICE = False
FORMAT_STAGE_BASE_PERCENT = {
    STAGE_SEED: 0,
    STAGE_SPROUT: 20,
    STAGE_BUDDING: 45,
    STAGE_BLOOMING: 70,
    STAGE_AUTOMATED: 90,
}
FORMAT_STREAK_PERCENT_EACH = 2  # per correct in a row, up to FORMAT_STREAK_PERCENT_MAX
FORMAT_STREAK_PERCENT_MAX = 10
FORMAT_EASE_PERCENT_PER_POINT = 20  # per ease point away from the 2.5 default
FORMAT_MAX_PERCENT = 95  # never fully typed: some multiple choice always remains
FORMAT_AFTER_MISS_FACTOR = 0.5  # a plot just missed leans back toward multiple choice
TYPED_VARIANTS = (V_FR_EN_TYPED, V_EN_FR_TYPED, V_SYMBOL_NAME_TYPED, V_NAME_SYMBOL_TYPED)
# Choice variants that have a typed twin of the same plot, and the fill-the-gap
# variants whose question can also be asked as "type the missing word".
TYPED_COUNTERPART = {
    V_FR_EN_CHOICE: V_FR_EN_TYPED,
    V_EN_FR_CHOICE: V_EN_FR_TYPED,
    V_SYMBOL_NAME_CHOICE: V_SYMBOL_NAME_TYPED,
    V_NAME_SYMBOL_CHOICE: V_NAME_SYMBOL_TYPED,
}
TYPED_BLANK_VARIANTS = (V_BLANK_WORD, V_CONJUGATION_SWAP)


def question_format_percent(plot):
    """The share (0-95) of this plot's questions that are typed, from its
    stage, correct streak and ease factor. A plot still at Seed (never answered
    correctly, so never watered) is always 0: multiple choice only."""
    if ALWAYS_MULTIPLE_CHOICE or plot.stage == STAGE_SEED or plot.last_reviewed is None:
        return 0
    percent = FORMAT_STAGE_BASE_PERCENT.get(plot.stage, 0)
    percent += min(FORMAT_STREAK_PERCENT_MAX, FORMAT_STREAK_PERCENT_EACH * max(0, plot.correct_streak))
    percent += round((plot.ease_factor - DEFAULT_EASE) * FORMAT_EASE_PERCENT_PER_POINT)
    if plot.correct_streak == 0:
        percent = int(percent * FORMAT_AFTER_MISS_FACTOR)
    return max(0, min(FORMAT_MAX_PERCENT, int(percent)))


def wants_typed(plot):
    """Whether the next question for this plot should be typed: a fixed hash of
    the plot's scheduling state (so the answer to 'typed or choice?' changes as
    the plot is answered, and is the same every time for the same state)
    against its typed share."""
    percent = question_format_percent(plot)
    if percent <= 0:
        return False
    key = f"{plot.plot_id}|{plot.last_reviewed}|{plot.correct_streak}|{plot.interval_days}|{plot.last_watered}"
    return zlib.crc32(key.encode("utf-8")) % 100 < percent


def _as_typed_blank(question):
    """The typed form of a fill-the-gap choice question: same gap, same answer."""
    question["mode"] = "typed"
    question["choices"] = []
    question["instruction"] = INSTRUCTIONS[question["variant"] + "_typed"]
    return question


def generate_question(plot, rng=None, variant=None, exclude=None, farm=None, format=None):
    """Build one practice prompt for a plot, fresh, from catalog facts.

    `format` is None for the progressive schedule above, "choice" to force a
    multiple-choice question (for screens that cannot take typing), or "typed"
    to ask for a typed one wherever the plot has a typed form."""
    rng = random.Random() if rng is None else rng
    farm = state if farm is None else farm
    available = variants_for(plot, farm)

    if format == "typed":
        typed_now = True
    elif format == "choice":
        typed_now = False
    else:
        typed_now = wants_typed(plot)

    if variant is None:
        excluded = set()
        if isinstance(exclude, str):
            excluded = {exclude}
        elif exclude:
            excluded = set(exclude)
        pool = [v for v in available if v not in excluded] or available
        if typed_now:
            typed_pool = [v for v in pool if v in TYPED_VARIANTS or v in TYPED_BLANK_VARIANTS]
            pool = typed_pool or pool
        else:
            choice_pool = [v for v in pool if v not in TYPED_VARIANTS]
            pool = choice_pool or pool
        variant = rng.choice(pool)
    elif typed_now and variant in TYPED_COUNTERPART and TYPED_COUNTERPART[variant] in available:
        variant = TYPED_COUNTERPART[variant]
    typed_blank = typed_now and variant in TYPED_BLANK_VARIANTS

    note = plot.rule if plot.topic_type == "grammar" else None

    if variant in (V_EXAMPLE_FR_EN, V_EXAMPLE_EN_FR):
        item = rng.choice(plot.items)
        if variant == V_EXAMPLE_FR_EN:
            return _choice_question(
                plot, variant, item["fr"], item["en"],
                _raw_pool(farm, plot, "en", item["en"]), rng, note,
            )
        return _choice_question(
            plot, variant, item["en"], item["fr"],
            _raw_pool(farm, plot, "fr", item["fr"]), rng, note,
        )

    if variant == V_BLANK_WORD:
        candidates = [i for i in plot.items if blank_target(i["fr"])]
        item = rng.choice(candidates)
        blanked, answer = blank_target(item["fr"])
        # If the gap landed on a verb form, the rest of that verb's table is a
        # far better distractor set than unrelated nearby vocabulary.
        split = split_pronoun(item["fr"])
        pool = []
        if split and split[1] == answer:
            pool = _form_pool(farm, plot, answer)
        if not _enough(pool):
            pool = _target_pool(farm, plot, answer)
        built = _choice_question(plot, variant, blanked, answer, pool, rng, note)
        return _as_typed_blank(built) if typed_blank else built

    if variant == V_CONJUGATION_SWAP:
        # The pronoun is re-rolled from the table's own six-person set each
        # visit, so the blank moves around instead of drilling one form (§5).
        pronoun, answer = rng.choice(conjugation_forms(plot))
        built = _choice_question(
            plot, variant, f"{pronoun} {BLANK_MARKER}", answer,
            _form_pool(farm, plot, answer), rng, note,
        )
        return _as_typed_blank(built) if typed_blank else built

    if variant == V_BLANK_ENDING:
        stem, entries = _ending_split(plot)
        pronoun, ending = rng.choice(entries)
        return _choice_question(
            plot, variant, f"{pronoun} {stem}{BLANK_MARKER}", ending,
            _ending_pool(plot, ending), rng, note,
        )

    if variant == V_GENDER_TAG:
        # Always exactly two choices -- bare "le"/"la", not a fabricated
        # "la <noun>" distractor, since gluing the wrong article onto a real
        # noun would be an invented string no catalog item actually contains
        # (§5's copyright rule), where a plain article is just a real French
        # function word already present all over the catalog. The noun
        # stays visible in the prompt throughout: this drill isolates the
        # article, it doesn't also re-test recall of the word itself. Built
        # directly rather than through _choice_question(), whose distractor
        # sampling assumes a pool of plausible-but-wrong *answers* to draw
        # several from -- there is exactly one other article, ever.
        article, noun = gender_tag_parts(plot.items[0]["fr"])
        other = "la" if article == "le" else "le"
        choices = [article, other]
        rng.shuffle(choices)
        return {
            "plot_id": plot.plot_id,
            "variant": variant,
            "topic_type": plot.topic_type,
            "context": _context_line(plot),
            "instruction": INSTRUCTIONS[variant],
            "prompt": noun,
            "note": None,
            "mode": "choice",
            "choices": choices,
            "answer": article,
        }

    if variant in (V_FR_EN_TYPED, V_SYMBOL_NAME_TYPED):
        item = rng.choice(_typable_items(plot, "en"))
        return _typed_question(plot, variant, item["fr"], item["en"], note)
    if variant in (V_EN_FR_TYPED, V_NAME_SYMBOL_TYPED):
        item = rng.choice(
            _typable_items(plot, "fr", ascii_only=plot.topic_type == "phonetic")
        )
        return _typed_question(plot, variant, item["en"], item["fr"], note)

    item = plot.items[0]
    if variant in (V_FR_EN_CHOICE, V_SYMBOL_NAME_CHOICE):
        return _choice_question(
            plot, variant, item["fr"], item["en"],
            _raw_pool(farm, plot, "en", item["en"]), rng, note,
        )
    return _choice_question(
        plot, variant, item["en"], item["fr"],
        _raw_pool(farm, plot, "fr", item["fr"]), rng, note,
    )


def _strip_plus_annotation(text):
    """Drop a trailing "+ [template placeholder]" marker, e.g.
    "I am + [nationality]" -> "I am", "Je suis + [occupation]" -> "Je suis".
    These mark where a specific word would go in a live sentence -- the
    catalog's own template items (see e.g. fren151-w4-phrase002) -- not
    something a typed answer should have to reproduce.

    Deliberately naive: it strips from the *first* "+" onward, which is
    right for a trailing slot label but over-accepts on the 7 items where
    "+" is mid-string rule notation whose tail is the actual lesson, not a
    placeholder (fren151-w8-grammar005's "à + le -> au" and friends,
    fren152-w4-grammar002's "plus + adjective + que" and friends) -- typing
    just "à" or "plus" there is wrongly accepted as a full answer. Known and
    deliberately left as-is rather than tightened: see the audit-pass note
    in CLAUDE.md's Milestone 3 build notes for why (the brief here is *more*
    lenient typed-answer checking, never less)."""
    return re.sub(r"\s*\+.*$", "", text).strip()


# Common English contractions, both directions -- "it's"/"it is" and the
# like should never cost a plant either way. Matched as whole words/phrases
# (word-boundaried) against an already-normalized (casefolded, apostrophe-
# folded) string, so case and curly-vs-straight apostrophes are moot.
CONTRACTION_PAIRS = [
    ("i'm", "i am"), ("you're", "you are"), ("we're", "we are"), ("they're", "they are"),
    ("he's", "he is"), ("she's", "she is"), ("it's", "it is"), ("that's", "that is"),
    ("what's", "what is"), ("who's", "who is"), ("there's", "there is"), ("here's", "here is"),
    ("let's", "let us"),
    ("how's", "how is"), ("where's", "where is"), ("when's", "when is"),
    ("i'd", "i would"), ("you'd", "you would"), ("he'd", "he would"), ("she'd", "she would"),
    ("we'd", "we would"), ("they'd", "they would"),
    ("i've", "i have"), ("you've", "you have"), ("we've", "we have"), ("they've", "they have"),
    ("i'll", "i will"), ("you'll", "you will"), ("he'll", "he will"), ("she'll", "she will"),
    ("we'll", "we will"), ("they'll", "they will"), ("it'll", "it will"),
    ("don't", "do not"), ("doesn't", "does not"), ("didn't", "did not"),
    ("can't", "cannot"), ("won't", "will not"), ("wouldn't", "would not"),
    ("shouldn't", "should not"), ("couldn't", "could not"),
    ("isn't", "is not"), ("aren't", "are not"), ("wasn't", "was not"), ("weren't", "were not"),
    ("haven't", "have not"), ("hasn't", "has not"), ("hadn't", "had not"),
]


def _contraction_variants(text):
    """Both directions of every contraction pair found in `text`."""
    variants = set()
    for short, long in CONTRACTION_PAIRS:
        if re.search(rf"\b{re.escape(short)}\b", text):
            variants.add(re.sub(rf"\b{re.escape(short)}\b", long, text))
        if re.search(rf"\b{re.escape(long)}\b", text):
            variants.add(re.sub(rf"\b{re.escape(long)}\b", short, text))
    return variants


# Belgian/Swiss French use their own words for 70/80/90 instead of the
# France-standard compounds -- both are correct French, so both are
# accepted. ("nonante" is the actual attested regional word for 90;
# "neufante" isn't real French, but accepted too in case that's genuinely
# what you were taught as its counterpart to septante/huitante.)
# Keys are in normalize_answer() form (hyphens read as spaces).
NUMBER_REGIONALISMS = {
    "soixante dix": ("septante",),
    "quatre vingts": ("huitante",),
    "quatre vingt dix": ("nonante", "neufante"),
}


def answer_alternatives(answer, accepted=None, fold_accents=True):
    """Everything a typed answer may reasonably be spelled as -- the LENIENT
    side of §14.2's two tiers. `accepted` is an optional iterable of extra
    catalog-supplied phrasings (the item's `accepted` array, §14.2.4) folded
    in alongside the mechanically-derived ones; omitted, this is byte-for-byte
    Milestone 3's original function, so every pre-existing caller (including
    every test that predates this milestone) sees identical behaviour."""
    alternatives = set()
    raw = str(answer).strip()
    base = strip_parentheticals(raw)
    candidates = {raw, base, _strip_plus_annotation(raw), _strip_plus_annotation(base)}
    pieces = list(candidates)
    for candidate in candidates:
        pieces.extend(re.split(r"\s*/\s*|\s*;\s*", candidate))
    for extra in accepted or ():
        pieces.append(str(extra))
    for chunk in pieces:
        chunk = chunk.strip()
        if not chunk:
            continue
        normalized = normalize_answer(chunk, fold_accents=fold_accents)
        if not normalized:
            continue
        alternatives.add(normalized)
        if " / " in normalized:
            alternatives.add(normalized.replace(" / ", "/"))
        for prefix in ARTICLE_PREFIXES:
            if normalized.startswith(prefix):
                alternatives.add(normalized[len(prefix):])
    for alt in list(alternatives):
        alternatives.update(_contraction_variants(alt))
        alternatives.update(NUMBER_REGIONALISMS.get(alt, ()))
    return {alt for alt in alternatives if alt}


# --- Milestone 8: STRICT/LENIENT grading tiers (design doc §14.2) ----------
#
# The addendum formalizes what Milestone 3 already did into two named tiers,
# decided automatically from an item's own shape rather than hand-flagged:
# a short (single-word-or-compound) answer is STRICT -- exact match after
# shared normalization only, no synonym list -- while a longer phrase or
# sentence is LENIENT and gets the full alternatives treatment above, plus
# whatever a human has since added to that item's catalog `accepted` array
# after triaging a report (§14.2.4).

TIER_STRICT = "strict"
TIER_LENIENT = "lenient"


def grading_tier(answer_text):
    """STRICT for a single word/compound (a vocab word, a number, one
    isolated conjugated form); LENIENT for two or more words (a phrase, a
    full-sentence translation, a fill-in-the-blank answer). The plus-slot and
    parenthetical stripping happen first so a template item like "I am +
    [nationality]" is judged on "I am" (LENIENT), not the annotated original."""
    text = strip_parentheticals(_strip_plus_annotation(str(answer_text)))
    # A "/" lists alternatives ("waiter/waitress"): each side must be
    # accepted on its own, which only the LENIENT path does, however few
    # spaces the author left round the slash (answer-report review 2026-10-08).
    if "/" in text:
        return TIER_LENIENT
    return TIER_STRICT if len(text.split()) <= 1 else TIER_LENIENT


def strict_alternatives(answer, fold_accents=True):
    """STRICT-tier comparison set: normalization only (shared whitespace/
    case/punctuation folding, contraction equivalence, the number-
    regionalism table, and parenthetical-suffix stripping) -- no "/"
    splitting, no leading-article drop, no catalog `accepted` list.
    Contractions and regional number words are kept even here because they
    are genuine alternate spellings of the exact same fact, not a synonym
    list of the kind STRICT is meant to exclude.

    Parenthetical stripping was added after a report-queue review (25
    reports triaged 2026-09-05) found several STRICT items --
    "gentil(le)", "culturel(le)", "intelligent(e)", "regarder (-er)" -- all
    rejecting the correct bare masculine/base form, because this function
    never stripped the "(...)" the catalog uses to note an alternate
    ending exists (unlike answer_alternatives()'s LENIENT path, which
    already did this from Milestone 3 onward). grading_tier() already
    strips parentheticals *before counting words* to decide STRICT vs
    LENIENT, so a bare "gentil(le)" item was always routed to STRICT --
    it just never got the same stripping applied to the actual comparison
    once it got there. 40 catalog items carry this "(...)" suffix shape."""
    raw = str(answer).strip()
    base = strip_parentheticals(raw)
    alternatives = set()
    for candidate in (raw, base):
        normalized = normalize_answer(candidate, fold_accents=fold_accents)
        if normalized:
            alternatives.add(normalized)
    for alt in list(alternatives):
        alternatives.update(_contraction_variants(alt))
        alternatives.update(NUMBER_REGIONALISMS.get(alt, ()))
    return {alt for alt in alternatives if alt}


def generate_accepted_variants(text):
    """The auto-generated seed for a LENIENT item's catalog `accepted` array
    (§14.2): the canonical phrasing, the same with trailing punctuation
    dropped, both directions of any contraction it contains, and -- only
    when the raw text is an explicit "/" alternation -- each side on its own
    plus the pair reordered. Deliberately mechanical: this only ever
    recombines the item's own text, so it stays inside the same
    copyright-safety rule as the runtime question generator (§5). Meant as a
    starting point, not the final word -- the array is meant to keep growing
    afterwards from real usage via the report button (§14.2.4)."""
    raw = str(text).strip()
    variants = []

    def _add(value):
        value = value.strip()
        if value and value not in variants:
            variants.append(value)

    _add(raw)
    stripped = raw.rstrip(TRAILING_PUNCTUATION + "…").strip()
    _add(stripped)
    for candidate in (raw, stripped):
        for short, long in CONTRACTION_PAIRS:
            if re.search(rf"\b{re.escape(short)}\b", candidate, re.IGNORECASE):
                _add(re.sub(rf"\b{re.escape(short)}\b", long, candidate, flags=re.IGNORECASE))
            if re.search(rf"\b{re.escape(long)}\b", candidate, re.IGNORECASE):
                _add(re.sub(rf"\b{re.escape(long)}\b", short, candidate, flags=re.IGNORECASE))
    sides = re.split(r"\s*/\s*", stripped)
    if len(sides) == 2 and all(sides):
        _add(f"{sides[0]} / {sides[1]}")
        _add(f"{sides[1]} / {sides[0]}")
    return variants


def _catalog_item_accepted(item, field):
    """The accepted-answer array for one catalog item/field. A human-curated
    array literally present on the record (added by hand after triaging a
    report, §14.2.4) wins; otherwise it's generated on the fly from the
    item's own text. Generating it lazily rather than writing it out to the
    966-item catalog file up front is what satisfies "auto-generated ...
    not hand-authored for all 966 items" without bloating a file that is
    otherwise just facts -- see CLAUDE.md's Milestone 8 build note."""
    manual = item.get(f"accepted_{field}")
    if manual:
        return list(manual)
    return generate_accepted_variants(item.get(field, ""))


def _lookup_accepted(question, farm=None):
    """Find the catalog item behind a generated question's answer, so
    `check_answer` can consult its accepted-variant array. Safe against the
    hand-built question dicts this file's own pre-Milestone-8 tests use
    (which carry no "plot_id"), since a missing/unknown plot simply yields
    no extra variants rather than raising."""
    farm = state if farm is None else farm
    plot = farm.plots_by_id.get(question.get("plot_id"))
    if plot is None:
        return None
    answer = question.get("answer")
    for item in plot.items:
        if item.get("fr") == answer:
            return _catalog_item_accepted(item, "fr")
        if item.get("en") == answer:
            return _catalog_item_accepted(item, "en")
    return None


def _matched_item_field(question, farm=None):
    """(item, field) of the catalog item a generated question's answer came
    from, or (None, None) for a hand-built question."""
    farm = state if farm is None else farm
    plot = farm.plots_by_id.get(question.get("plot_id"))
    if plot is None:
        return None, None
    answer = question.get("answer")
    for item in plot.items:
        if item.get("fr") == answer:
            return item, "fr"
        if item.get("en") == answer:
            return item, "en"
    return None, None


def _manual_accepted(question, farm=None):
    """Only a hand-curated array: the item's literal accepted_en/accepted_fr
    or one the question itself carries (bonus tiles and sentences). The
    STRICT tier honours these but never the mechanically generated ones."""
    extra = list(question.get("accepted") or [])
    item, field = _matched_item_field(question, farm)
    if item is not None and item.get(f"accepted_{field}"):
        extra.extend(item[f"accepted_{field}"])
    return extra


def _answer_is_english(question, farm=None):
    """True when the typed answer is English, whose accents are never
    assessed (a French accent slipped onto an English word is a slip, not a
    wrong answer). The phonetic accent names (tréma, cédille) stay exact."""
    lang = question.get("lang")
    if lang:
        return lang == "en"
    if question.get("topic_type") == "phonetic":
        return False
    variant = question.get("variant")
    if variant in (V_FR_EN_TYPED, V_EXAMPLE_FR_EN):
        return True
    if variant is not None:
        return False
    item, field = _matched_item_field(question, farm)
    return field == "en" and item.get("fr") != item.get("en")


# Improvement Ideas §2: "weeds" as a distinct plot state for commonly-
# confused pairs -- false friends and French-internal look-alikes, kept
# separate from ordinary wilting. A starter list, not exhaustive: this
# catalog is A1/A2-level, so most "textbook" French/English false-friend
# lists (actuellement, librairie, assister...) don't actually appear in it
# -- travailler/travel is the one confirmed real false friend here. The
# rest are the classic beginner homophone mixups, checkable purely from the
# submitted vs. correct answer text with no new catalog content required.
# Grows the same way accepted_en/accepted_fr overrides do: add a pair here
# when real play surfaces one, rather than trying to anticipate every
# possible confusion up front.
WEED_CONFUSIONS = {
    "to work": {"travel"},  # travailler looks like "travel," means "to work"
    "à": {"a"}, "a": {"à"},
    "ou": {"où"}, "où": {"ou"},
    "ce": {"se"}, "se": {"ce"},
    "son": {"sont"}, "sont": {"son"},
    "ces": {"ses"}, "ses": {"ces"},
    "on": {"ont"}, "ont": {"on"},
    "c'est": {"s'est", "sait"},
    "leur": {"leurs"}, "leurs": {"leur"},
}


def is_weed_confusion(correct_answer, submitted_answer):
    """True if a wrong typed answer matches a *specific*, known mix-up for
    the real answer, rather than being an arbitrary miss. Deliberately
    accent-preserving (fold_accents=False) even though normal grading can
    fold accents -- half of these pairs (à/a, où/ou) are *only* different
    by their accent, so folding it here would make them indistinguishable
    from each other, defeating the whole check."""
    confusable = WEED_CONFUSIONS.get(normalize_answer(str(correct_answer), fold_accents=False))
    if not confusable:
        return False
    return normalize_answer(str(submitted_answer), fold_accents=False) in confusable


# ===========================================================================
# Milestone 20 -- personal error-pattern digest (Improvement Ideas addendum §?)
# ===========================================================================
#
# A wrong typed answer is more useful to a learner as a *reason* than as a
# tally: "you keep dropping accents" is actionable, "3 wrong" isn't. This is
# purely diagnostic -- classify_wrong_typed_answer() never feeds back into
# grading or SRS scheduling, only into a persistent count surfaced on the
# Progress Dashboard.

ERROR_PATTERN_ACCENT = "accent"
ERROR_PATTERN_KNOWN_MIXUP = "known_mixup"
ERROR_PATTERN_CLOSE_TYPO = "close_typo"
ERROR_PATTERN_OTHER = "other"

ERROR_PATTERN_LABELS = {
    ERROR_PATTERN_ACCENT: "Dropped or mistyped an accent",
    ERROR_PATTERN_KNOWN_MIXUP: "Mixed up a known look-alike pair",
    ERROR_PATTERN_CLOSE_TYPO: "Close, but not an exact match",
    ERROR_PATTERN_OTHER: "Didn't recall the answer",
}

# Order matters here (also the order the dashboard lists them in): a mixup
# that happens to also be spelled with a wrong accent is a mixup first, and
# an accent slip that also happens to be textually close to the real answer
# is still specifically an accent slip, not a generic "close" typo.
ERROR_PATTERN_ORDER = [
    ERROR_PATTERN_KNOWN_MIXUP,
    ERROR_PATTERN_ACCENT,
    ERROR_PATTERN_CLOSE_TYPO,
    ERROR_PATTERN_OTHER,
]

CLOSE_TYPO_SIMILARITY_THRESHOLD = 0.8

error_pattern_counts = {}


def classify_wrong_typed_answer(question, given, tier):
    """Best-effort diagnosis of *why* a typed answer missed. Only meaningful
    for typed answers -- a wrong multiple-choice pick carries none of this
    nuance, it's just "picked the wrong one" (see submit_answer's caller)."""
    answer = question["answer"]
    if is_weed_confusion(answer, given):
        return ERROR_PATTERN_KNOWN_MIXUP
    # Would this have passed if accents didn't matter? A genuine accent slip,
    # regardless of whether the live session is currently accent-sensitive
    # (see check_answer's fold_accents mapping just below).
    if check_answer(question, given, tier=tier, accent_sensitive=False):
        return ERROR_PATTERN_ACCENT
    if _answer_similarity(given, answer) >= CLOSE_TYPO_SIMILARITY_THRESHOLD:
        return ERROR_PATTERN_CLOSE_TYPO
    return ERROR_PATTERN_OTHER


def check_question_answer(question, given):
    """Grade one answer to a generated question the way the farm does: a
    multiple-choice pick is exact, a typed answer gets its tier from the
    answer's shape and honours the accent setting. Used by the minigames."""
    typed = question["mode"] == "typed"
    tier = grading_tier(question["answer"]) if typed else None
    return check_answer(question, given, tier=tier, accent_sensitive=ACCENT_SENSITIVE)


def record_error_pattern(pattern):
    error_pattern_counts[pattern] = error_pattern_counts.get(pattern, 0) + 1


def check_answer(question, given, tier=None, accent_sensitive=None):
    """Multiple choice is always exact. Typed answers: with no `tier`
    (the original Milestone 3 signature), this is byte-for-byte the old
    fully-lenient check, so every pre-Milestone-8 caller is unaffected.
    Passing a tier switches on §14.2's formal STRICT/LENIENT behaviour,
    and `accent_sensitive` (default: folded, i.e. accent-insensitive, same
    as always) lets a caller opt into the accent-sensitivity toggle."""
    if question["mode"] == "choice":
        return given == question["answer"]
    fold_accents = True if accent_sensitive is None else not accent_sensitive
    if not fold_accents and _answer_is_english(question):
        fold_accents = True
    typed = normalize_answer(given, fold_accents=fold_accents)
    if not typed:
        return False
    bare_ok = _bare_noun_allowed(question)
    if tier is None:
        allowed = answer_alternatives(question["answer"])
        return typed in (allowed | _bare_nouns(allowed) if bare_ok else allowed)
    if tier == TIER_STRICT:
        allowed = strict_alternatives(question["answer"], fold_accents=fold_accents)
        for extra in _manual_accepted(question):
            allowed |= strict_alternatives(extra, fold_accents=fold_accents)
        return typed in (allowed | _bare_nouns(allowed) if bare_ok else allowed)
    accepted = list(_lookup_accepted(question) or []) + list(question.get("accepted") or [])
    allowed = answer_alternatives(question["answer"], accepted=accepted, fold_accents=fold_accents)
    return typed in (allowed | _bare_nouns(allowed) if bare_ok else allowed)


# FY-14 (owner, 2026-10-08): a question that asks for just the word does not
# make the player type le/la/un/une. "mode" is right for "la mode"; the
# article still appears in the feedback line. A question that shows or asks
# for the article keeps requiring it: it sets "with_article": True (nothing
# in the typed flow does today; the gender drill is a choice between le and
# la and never reaches this). Only vocabulary plots are affected (a grammar
# rule such as "le plus" is about the little word) and only French answers.
_BARE_NOUN_ARTICLES = ("le ", "la ", "un ", "une ")


def _bare_noun_allowed(question):
    if question.get("with_article") or question.get("variant") == V_GENDER_TAG:
        return False
    if question.get("topic_type") != "vocab":
        return False
    return not _answer_is_english(question)


def _bare_nouns(alternatives):
    """The same alternatives without a leading le/la/un/une (a one- or
    few-word noun only: the rest must not start another article)."""
    bare = set()
    for alt in alternatives:
        for article in _BARE_NOUN_ARTICLES:
            if alt.startswith(article):
                rest = alt[len(article):].strip()
                if rest and len(rest.split()) <= 4:
                    bare.add(rest)
    return bare


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


# Module-level UI state.
current_question = None
current_result = None
current_submitted_answer = None
current_water_kind = None  # what the last correct farm answer did: WATER_FULL / WATER_NUDGE / None
practice_open = False
report_sent = False
pronunciation_report_sent = False
plot_cells = {}
QUESTION_RNG = random.Random()

# Session combo count (consecutive correct answers, any plot) and the
# confidence tag on the currently-open question. Both are pure session
# state -- like ACCENT_SENSITIVE below -- and deliberately never reach
# get_state()/load_state(): a fresh page load always starts at zero/unset.
combo_count = 0
current_confidence = None  # None | "sure" | "unsure"
# L6 -- session-only running tally of [correct, total] per confidence tag,
# so the player can see whether "sure" really means right. Same posture as
# combo_count/current_confidence: not persisted, a fresh page starts empty.
confidence_tally = {"sure": [0, 0], "unsure": [0, 0]}


def confidence_stats_text():
    sure, unsure = confidence_tally["sure"], confidence_tally["unsure"]
    if sure[1] == 0 and unsure[1] == 0:
        return ""
    return f"Your confidence so far: sure {sure[0]}/{sure[1]} right · not sure {unsure[0]}/{unsure[1]} right"


# L28 -- a small badge for perfectly answering a full row's worth of plots
# in one sitting: every plot in that row answered correctly this session,
# with zero wrong answers anywhere in the row this session. "One sitting"
# is read literally as *this session*, not a permanent unlock, so -- same
# posture as combo_count/ACCENT_SENSITIVE above -- all three dicts here are
# pure session state and never reach get_state()/load_state(); a fresh
# page load always starts every row unspoiled and un-badged. A row that's
# already spoiled this session can never earn the badge later even if
# every subsequent answer in it is correct -- the point is a clean run
# through the whole row, not just "eventually got them all right".
row_session_correct = {}  # sequence -> set of plot_ids answered correctly this session
row_session_spoiled = set()  # sequences with at least one wrong answer this session
row_session_perfect_badge = set()  # sequences that have earned the badge this session


def _track_row_session_answer(plot, correct):
    sequence = plot.sequence
    if sequence in row_session_spoiled:
        return
    if not correct:
        row_session_spoiled.add(sequence)
        row_session_correct.pop(sequence, None)
        return
    row_session_correct.setdefault(sequence, set()).add(plot.plot_id)
    row_plots = state.row_plots(sequence)
    if row_plots and row_session_correct[sequence] >= {p.plot_id for p in row_plots}:
        row_session_perfect_badge.add(sequence)


# §14.2's accent-sensitivity toggle: default ON (accents must be typed
# correctly) since spelling them right is an assessed skill. A session
# preference, not SRS state, so it deliberately stays out of get_state()/
# load_state() -- same call as `plot.last_variant` in Milestone 4.
ACCENT_SENSITIVE = True

# Choice-button click handlers created by the last render_practice() call.
# Unlike the grid's cell handlers and the panel's other fixed buttons (each
# wired once in build_farm()/setup()), these are rebuilt on every repaint —
# so, unlike those, they have to be explicitly destroyed each time or the
# proxies pile up unboundedly over a play session.
practice_choice_proxies = []


def _destroy_practice_choice_proxies():
    for proxy in practice_choice_proxies:
        proxy.destroy()
    practice_choice_proxies.clear()


# --- Milestone 11: Review tab state (design doc §14.4) ---------------------
#
# Opt-in, entirely separate from the daily watering loop: it never grows a
# plot's stage and never changes row-unlock state (only stage does that), so
# it can't be used to skip the pacing gate. All of it is session state, like
# `ACCENT_SENSITIVE` above — none of it belongs in get_state()/load_state().

review_controls_open = False
review_mode = None  # None | "word" | "grammar"
review_queue = []  # plot_ids, fixed for the session once start_review() rolls it
review_index = 0
review_question = None
review_result = None
review_score = {"correct": 0, "total": 0}
review_choice_proxies = []
review_water_kind = None  # what the last correct Review answer did to its plot
review_listen_revealed = False  # listening water: the French text has been shown
REVIEW_RNG = random.Random()

# Milestone 26: the report buttons, extended here from the main practice
# panel only (see that milestone's build note -- requested directly after
# Milestone 11 had explicitly scoped them out). Same session-only posture as
# everything else in this block.
review_submitted_answer = None
review_report_sent = False
review_pronunciation_report_sent = False


def _destroy_review_choice_proxies():
    for proxy in review_choice_proxies:
        proxy.destroy()
    review_choice_proxies.clear()


# --- Milestone 12: weekly proficiency test state (design doc §14.5) --------
#
# Purely informational, like Review — but unlike Review, it never touches SRS
# state at all (no nudge, nothing), since §14.5 explicitly frames this as
# "regardless of what's currently planted/watered", not a practice mode.

PROFICIENCY_TEST_LENGTH = 18
PROFICIENCY_RNG = random.Random()
PROFICIENCY_SUMMARY_MESSAGE = "Score: {correct}/{total}."
PROFICIENCY_TOPIC_LINE = "{title}: {correct}/{total}"

proficiency_mode = False
proficiency_sequence = None
proficiency_questions = []  # [{"topic_id","topic_title","topic_type","question"}, ...]
proficiency_index = 0
proficiency_result = None
proficiency_score = {"correct": 0, "total": 0}
proficiency_topic_scores = {}  # topic_id -> {"title", "correct", "total"}
proficiency_choice_proxies = []

# Milestone 26: same report-button extension as Review, see that milestone's
# build note.
proficiency_submitted_answer = None
proficiency_report_sent = False
proficiency_pronunciation_report_sent = False


def _destroy_proficiency_choice_proxies():
    for proxy in proficiency_choice_proxies:
        proxy.destroy()
    proficiency_choice_proxies.clear()


# --- Milestone 13: bonus sentence-building section state (design doc §14.6) -
#
# Purely informational like Review and the proficiency test — nothing here
# ever touches a plot's SRS state or row-unlock state. Three tasks per
# sentence: order the tiles, translate each tile (STRICT), translate the
# whole sentence (LENIENT) — see CLAUDE.md's Milestone 13 build note for why
# those two tiers are fixed by task rather than decided by grading_tier().

BONUS_RNG = random.Random()

bonus_mode = False
bonus_sequence = None
bonus_queue = []  # this week's bonus_sentences, fixed for the session
bonus_index = 0  # which sentence in the queue
bonus_task = None  # None | "order" | "translate_tiles" | "translate_sentence"
bonus_tile_pool = []  # tiles not yet placed (task 1), shuffled
bonus_placed = []  # tiles placed so far, in the player's chosen order
bonus_order_correct = None  # None | True | False, set once the pool empties
bonus_tile_index = 0  # which tile (in correct order) is being translated (task 2)
bonus_tile_result = None  # None | True | False for the tile currently shown
bonus_tile_score = {"correct": 0, "total": 0}  # this sentence's task-2 tally
bonus_sentence_result = None  # None | True | False (task 3)
bonus_score = {"correct": 0, "total": 0}  # every checkable step, this session

BONUS_ORDER_CORRECT = "That's the right order."
BONUS_ORDER_INCORRECT = "Not quite — the sentence is: {sentence}"
BONUS_SUMMARY_MESSAGE = "Bonus section complete — {correct}/{total} correct."

# Milestone 26: report buttons for tasks 2 and 3 (both always typed). Task 1
# (tile ordering) has no typed answer, so it gets neither -- same rule that
# already keeps a wrong multiple-choice pick in the main panel report-free.
# Bonus sentences aren't plot-backed (they're hand-authored, §14.6), so their
# reports use their own item-id/topic-type scheme rather than the
# plot-lookup one the farm/Review/Proficiency questions share -- see
# BONUS_TILE_REPORT_TOPIC_TYPE / BONUS_SENTENCE_REPORT_TOPIC_TYPE below.
BONUS_TILE_REPORT_TOPIC_TYPE = "bonus_tile"
BONUS_SENTENCE_REPORT_TOPIC_TYPE = "bonus_sentence"

bonus_tile_submitted_answer = None
bonus_tile_report_sent = False
bonus_tile_pronunciation_report_sent = False
bonus_sentence_submitted_answer = None
bonus_sentence_report_sent = False
bonus_sentence_pronunciation_report_sent = False


# ===========================================================================
# "My Reports" (Z11, planning/TODO.md, site-wide goal) -- a small, dated feed
# confirming every report this player has actually sent, built on the shared
# shared/narrative_log.py component (Continuum's "Chronicle" is that
# component's reference integration; Thaw's scientist's log is the second;
# this is the third). Investigating this task's own L14 line ("let the
# report-button flow show a short 'thanks, noted' confirmation distinct from
# the normal question-feedback flow") found it was already fully satisfied
# by the pre-existing REPORT_SENT_LABEL/PRONUNCIATION_REPORT_SENT_LABEL
# button-label swap defined above (each report button already reads
# "Reported — thanks" and disables itself) -- a genuine cross-round label
# collision with a *different* feature, per planning/TODO.md's own L14 line
# under this game's section, not a narrative-log-shaped gap at all. This
# panel is the actual narrative-log-shaped feature the Z11 task asks to
# build instead: "a dated feed of 'you reported X on this date'
# confirmations from its existing answer-reports feature." "Dated" here
# means `state.current_day` (this game's own no-wall-clock day counter,
# Milestone 2) rather than a real calendar date -- `game.py` is forbidden
# from touching any clock API at all (Milestone 7's own tested constraint,
# `test_nothing_in_the_game_runs_on_a_timer`), the same reason §14.2.4's
# report payload itself never builds its own timestamp.
# ===========================================================================
REPORT_LOG_MAX = 20

# Every one of this game's 10 submit_*_report() functions sends a payload
# whose "topic_type" is either a plot's own topic_type (vocab/grammar/
# phrase/phonetic, from the main/Review/Proficiency "should count" reports)
# or one of these three fixed markers (pronunciation concerns, and Bonus's
# two non-plot-backed report kinds) -- this maps the fixed markers to a
# readable phrase; anything else falls back to a generic "a {topic_type}
# answer" phrase built from the raw value itself.
REPORT_LOG_TOPIC_LABEL = {
    PRONUNCIATION_REPORT_TOPIC_TYPE: "a pronunciation concern",
    BONUS_TILE_REPORT_TOPIC_TYPE: "a bonus-tile translation",
    BONUS_SENTENCE_REPORT_TOPIC_TYPE: "a bonus-sentence translation",
}

report_log = []
report_log_open = False


def _report_log_topic_label(topic_type):
    return REPORT_LOG_TOPIC_LABEL.get(topic_type, f"a {topic_type} answer")


def _record_report_log_entry(payload):
    """Called right after every submit_*_report() function marks its own
    one-shot "sent" flag -- a local confirmation that a report was actually
    sent this session, independent of whether _dispatch_report()'s own
    network call succeeds (the flag it rides alongside is already
    fire-and-forget the same way, and this game has no clock to timestamp
    a network round-trip with regardless)."""
    answers = payload.get("marked_correct_answer") or [""]
    text = f"Reported {_report_log_topic_label(payload['topic_type'])} for “{answers[0]}”."
    narrative_log.add_entry(
        report_log,
        {"day": state.current_day, "topic": payload["topic_type"], "text": text},
        cap=REPORT_LOG_MAX,
    )


def on_toggle_report_log(event=None):
    global report_log_open
    report_log_open = not report_log_open
    render()


def _build_report_log_row(entry):
    # Same one-<p>-per-row idiom render_changelog()/render_dashboard()
    # already use for this game's own panels, rather than the
    # row/row-top/row-name/row-blurb multi-element structure Continuum's
    # own build_row callback uses -- internals are free once you're inside
    # a game, and this keeps the new panel visually consistent with the
    # rest of this game's own dashboard-style panels.
    row = document.createElement("p")
    row.className = "report-log-row"
    row.innerText = f"Day {entry['day'] + 1} — {entry['text']}"
    return row


def render_report_log():
    panel = _element("report-log-panel")
    toggle = _element("report-log-toggle-button")
    count = len(report_log)
    toggle.innerText = f"Hide My Reports ({count})" if report_log_open else f"📨 My Reports ({count})"
    panel.hidden = not report_log_open
    if not report_log_open:
        return
    narrative_log.render(
        "report-log-panel",
        report_log,
        _build_report_log_row,
        empty_text="Nothing reported yet — reports you send from any practice mode will show up here.",
        max_visible=REPORT_LOG_MAX,
    )


def _element(element_id):
    return document.getElementById(element_id)


def _make_plot_handler(plot_id):
    def handler(event=None):
        open_practice(plot_id)
    return handler


def _make_choice_handler(choice):
    def handler(event=None):
        submit_answer(choice)
    return handler


def _make_proficiency_handler(sequence):
    def handler(event=None):
        start_proficiency_test(sequence)
    return handler


def _make_bonus_handler(sequence):
    def handler(event=None):
        start_bonus_section(sequence)
    return handler


def build_farm():
    """Build the grid once. Rows are sequence numbers, running straight from
    FREN151 into FREN152 with only the chapter label marking the join (§4)."""
    global _farm_order_cache
    farm = _element("farm")
    farm.innerHTML = ""
    plot_cells.clear()
    _farm_cell_cache.clear()
    _farm_row_cache.clear()
    _semester_cache.clear()
    _farm_order_cache = None

    # LM-1: one band per semester (course), each holding its own weeks. The
    # sequence underneath stays one continuous list (state.rows is untouched);
    # the band is only a wrapper the rows sit in while the sort is Syllabus order.
    band_rows = {}
    for band in semester_bands():
        band_rows[band["course"]] = _build_semester_band(band, farm)

    for row in state.rows:
        row_element = document.createElement("div")
        row_element.id = f"row-{row.sequence}"
        row_element.className = "row"

        head = document.createElement("div")
        head.className = "row-head"

        label = document.createElement("span")
        label.id = f"row-label-{row.sequence}"
        label.className = "row-label"
        label.innerText = row.label
        head.appendChild(label)

        chapter = document.createElement("span")
        chapter.id = f"row-chapter-{row.sequence}"
        chapter.className = "row-chapter"
        chapter.innerText = row.chapter_label
        head.appendChild(chapter)

        progress = document.createElement("span")
        progress.id = f"row-progress-{row.sequence}"
        progress.className = "row-progress"
        head.appendChild(progress)

        perfect_badge = document.createElement("span")
        perfect_badge.id = f"row-perfect-badge-{row.sequence}"
        perfect_badge.className = "row-perfect-badge"
        perfect_badge.innerText = "⭐ Perfect this session"
        perfect_badge.title = (
            "Every plot in this row answered correctly this session, with no misses along the way."
        )
        perfect_badge.hidden = True
        head.appendChild(perfect_badge)

        due = document.createElement("span")
        due.id = f"row-due-{row.sequence}"
        due.className = "row-due"
        due.hidden = True
        head.appendChild(due)

        lock = document.createElement("span")
        lock.id = f"row-lock-{row.sequence}"
        lock.className = "row-lock"
        lock.innerText = LOCK_NOTE.format(previous=row.sequence - 1)
        lock.hidden = True
        head.appendChild(lock)

        # §14.5: one proficiency test per sequence entry, started right from
        # that week's own row rather than a separate flat list of 23 buttons.
        proficiency_button = document.createElement("button")
        proficiency_button.id = f"row-proficiency-{row.sequence}"
        proficiency_button.className = "row-proficiency-button secondary"
        proficiency_button.innerText = "Proficiency test"
        proficiency_button.addEventListener(
            "click", create_proxy(_make_proficiency_handler(row.sequence))
        )
        head.appendChild(proficiency_button)

        # §14.6: a bonus sentence-building section per week, same row-header
        # placement as the proficiency test button above.
        bonus_button = document.createElement("button")
        bonus_button.id = f"row-bonus-{row.sequence}"
        bonus_button.className = "row-bonus-button secondary"
        bonus_button.innerText = "Bonus sentence"
        bonus_button.addEventListener("click", create_proxy(_make_bonus_handler(row.sequence)))
        head.appendChild(bonus_button)

        plots = document.createElement("div")
        plots.id = f"row-plots-{row.sequence}"
        plots.className = "row-plots"

        for plot_id in row.plot_ids:
            cell = document.createElement("button")
            cell.id = f"plot-{plot_id}"
            cell.className = "plot"
            cell.addEventListener("click", create_proxy(_make_plot_handler(plot_id)))
            plots.appendChild(cell)
            plot_cells[plot_id] = cell

        row_element.appendChild(head)
        row_element.appendChild(plots)
        band_rows[row.course].appendChild(row_element)


def render_legend():
    lines = [f"{STAGE_ICON[stage]} {STAGE_LABEL[stage]}" for stage in STAGE_ORDER]
    lines.append(f"💧 {WILTING_LEGEND}")
    lines.append(f"{WEEDS_ICON} {WEEDS_LEGEND}")
    _element("legend").innerText = "  ·  ".join(lines)


# ===========================================================================
# LM-1: semester bands on the farm
# ===========================================================================
#
# FREN151 and FREN152 are still ONE continuous sequence (state.rows, the review
# order, the unlock chain and the save are all untouched). The bands are only a
# wrapper the weeks sit in while the sort is "Syllabus order": a heading with the
# course name, a divider, a progress line and meter of its own, and a Hide/Show
# weeks button. Which bands there are is read from the rows' own `course`, so a
# new week of either course lands in the right band with no change here (LM-3).
# Collapsed bands are a per-browser preference (like Always multiple choice), never
# part of the save. Any other sort mixes the semesters on purpose ("weakest first"
# across the whole farm), so there the bands step aside and a note says why.

PREF_SEMESTERS_COLLAPSED = "champ-semesters-collapsed"
SEMESTER_SUBTITLE = "{weeks} weeks · {chapters}"
SEMESTER_PROGRESS = "{open} of {weeks} weeks open · {growing} of {total} plots growing · {automated} automated"
SEMESTER_PROGRESS_DUE = " · {due} ready for water"
SEMESTER_CHIP = "{name} · {course}: {percent}% growing · {automated} automated"
SEMESTER_SORTED_NOTE = "Sorted view: weeks from both semesters are mixed. Choose Syllabus order to see the semester bands."
SEMESTER_HIDE_LABEL = "Hide weeks"
SEMESTER_SHOW_LABEL = "Show weeks"
semester_collapsed = set()  # course codes the player folded away; never saved
_semester_cache = {}
_last_row_shown = {}  # sequence -> plots of that row passing the L-24 filter, from render_farm()


def semester_bands():
    """The farm's semesters in syllabus order, read from the rows' own course:
    [{index, course, name, heading, sequences, weeks, chapters}]."""
    order = []
    by_course = {}
    for row in state.rows:
        if row.course not in by_course:
            by_course[row.course] = []
            order.append(row.course)
        by_course[row.course].append(row)
    bands = []
    for index, course in enumerate(order, start=1):
        rows = by_course[course]
        titles = []
        for row in rows:
            if row.chapter_title and row.chapter_title not in titles:
                titles.append(row.chapter_title)
        if len(titles) > 1:
            chapters = f"{titles[0]} to {titles[-1]}"
        else:
            chapters = titles[0] if titles else course
        bands.append({
            "index": index,
            "course": course,
            "name": f"Semester {index}",
            "heading": f"Semester {index} · {course}",
            "sequences": [row.sequence for row in rows],
            "weeks": len(rows),
            "chapters": chapters,
        })
    return bands


def semester_stats(band):
    """Counts for one band, over the whole band whatever the farm filter hides."""
    total = growing = automated = due = open_weeks = 0
    for sequence in band["sequences"]:
        plots = state.row_plots(sequence)
        unlocked = state.is_row_unlocked(sequence)
        open_weeks += 1 if unlocked else 0
        total += len(plots)
        for plot in plots:
            if plot.stage != STAGE_SEED:
                growing += 1
            if plot.stage == STAGE_AUTOMATED:
                automated += 1
            if unlocked and is_due(plot, state.current_day):
                due += 1
    return {
        "weeks": band["weeks"], "open": open_weeks, "total": total,
        "growing": growing, "automated": automated, "due": due,
    }


def semester_progress_text(stats):
    text = SEMESTER_PROGRESS.format(**stats)
    if stats["due"]:
        text += SEMESTER_PROGRESS_DUE.format(due=stats["due"])
    return text


def _make_semester_handler(course):
    def handler(event=None):
        toggle_semester(course)
    return handler


def _build_semester_band(band, farm):
    """One band's markup; returns the element the band's rows are appended to."""
    i = band["index"]
    wrapper = document.createElement("section")
    wrapper.id = f"semester-{i}"
    wrapper.className = "semester"

    head = document.createElement("div")
    head.id = f"semester-head-{i}"
    head.className = "row semester-head"

    top = document.createElement("div")
    top.className = "semester-top"
    title = document.createElement("h2")
    title.id = f"semester-title-{i}"
    title.className = "row-label semester-title"
    title.innerText = band["heading"]
    top.appendChild(title)
    toggle = document.createElement("button")
    toggle.id = f"semester-toggle-{i}"
    toggle.className = "secondary semester-toggle"
    toggle.setAttribute("type", "button")
    toggle.setAttribute("aria-controls", f"semester-rows-{i}")
    toggle.innerText = SEMESTER_HIDE_LABEL
    toggle.addEventListener("click", create_proxy(_make_semester_handler(band["course"])))
    top.appendChild(toggle)
    head.appendChild(top)

    sub = document.createElement("span")
    sub.id = f"semester-sub-{i}"
    sub.className = "row-chapter semester-sub"
    sub.innerText = SEMESTER_SUBTITLE.format(weeks=band["weeks"], chapters=band["chapters"])
    head.appendChild(sub)

    progress = document.createElement("span")
    progress.id = f"semester-progress-{i}"
    progress.className = "row-progress semester-progress"
    head.appendChild(progress)

    meter = document.createElement("div")
    meter.id = f"semester-meter-{i}"
    meter.className = "automated-meter semester-meter"
    meter.setAttribute("role", "img")
    bar = document.createElement("div")
    bar.id = f"semester-bar-{i}"
    bar.className = "automated-bar"
    meter.appendChild(bar)
    head.appendChild(meter)
    wrapper.appendChild(head)

    rows = document.createElement("div")
    rows.id = f"semester-rows-{i}"
    rows.className = "semester-rows"
    rows.setAttribute("role", "group")
    rows.setAttribute("aria-labelledby", f"semester-title-{i}")
    wrapper.appendChild(rows)
    farm.appendChild(wrapper)
    return rows


def toggle_semester(course, collapse=None):
    """Fold or unfold one semester's weeks. Remembered in this browser only."""
    if course not in {band["course"] for band in semester_bands()}:
        return False
    fold = (course not in semester_collapsed) if collapse is None else bool(collapse)
    if fold:
        semester_collapsed.add(course)
    else:
        semester_collapsed.discard(course)
    pref_set(PREF_SEMESTERS_COLLAPSED, ",".join(sorted(semester_collapsed)))
    render_semesters()
    return fold


def _load_semester_prefs():
    known = {band["course"] for band in semester_bands()}
    raw = pref_get(PREF_SEMESTERS_COLLAPSED, "") or ""
    semester_collapsed.clear()
    semester_collapsed.update(code for code in raw.split(",") if code in known)


def render_semesters():
    syllabus = farm_sort == "syllabus"
    chips = []
    for band in semester_bands():
        i = band["index"]
        stats = semester_stats(band)
        shown = any(_last_row_shown.get(sequence, 0) > 0 for sequence in band["sequences"])
        collapsed = band["course"] in semester_collapsed
        percent = round(100 * stats["growing"] / stats["total"]) if stats["total"] else 0
        chips.append(SEMESTER_CHIP.format(
            name=band["name"], course=band["course"], percent=percent, automated=stats["automated"]
        ))
        values = (tuple(stats.values()), syllabus and shown, collapsed)
        if _semester_cache.get(i) == values:
            continue
        _semester_cache[i] = values
        _element(f"semester-{i}").hidden = not (syllabus and shown)
        _element(f"semester-{i}").className = "semester semester--collapsed" if collapsed else "semester"
        _element(f"semester-rows-{i}").hidden = collapsed
        toggle = _element(f"semester-toggle-{i}")
        toggle.innerText = SEMESTER_SHOW_LABEL if collapsed else SEMESTER_HIDE_LABEL
        toggle.setAttribute("aria-expanded", "false" if collapsed else "true")
        toggle.setAttribute(
            "aria-label", f"{SEMESTER_SHOW_LABEL if collapsed else SEMESTER_HIDE_LABEL}: {band['heading']}"
        )
        _element(f"semester-progress-{i}").innerText = semester_progress_text(stats)
        share = stats["growing"] / stats["total"] if stats["total"] else 0.0
        _element(f"semester-bar-{i}").style.width = f"{share * 100:.1f}%"
        meter = _element(f"semester-meter-{i}")
        meter.title = f"{stats['growing']} of {stats['total']} plots growing in {band['heading']}"
        meter.setAttribute("aria-label", meter.title)

    summary_values = (tuple(chips), syllabus)
    if _semester_cache.get("summary") != summary_values:
        _semester_cache["summary"] = summary_values
        summary = _element("semester-summary")
        summary.innerHTML = ""
        for text in chips:
            chip = document.createElement("span")
            chip.className = "semester-chip"
            chip.innerText = text
            summary.appendChild(chip)
        if not syllabus:
            note = document.createElement("span")
            note.className = "semester-note"
            note.innerText = SEMESTER_SORTED_NOTE
            summary.appendChild(note)


# ===========================================================================
# LM-2: "What the colours and icons mean"
# ===========================================================================
#
# One list, legend_indicators(), says what every indicator on the farm means and
# how to draw a sample of it. It is built on each call from the tables the farm
# itself draws from (STAGE_ICON/STAGE_LABEL, WILTING_LEGEND, WEEDS_LEGEND,
# LOCK_NOTE, ROW_DUE_NOTE, FARM_FILTERS, GROWTH_INFO, ...), and a sample is drawn
# with the very same CSS classes the farm uses, so a restyle shows up in the guide
# too and the words cannot drift from the real indicators. The tests check the
# other direction: every class _plot_classes() can emit, every `.plot--*` rule in
# style.css, every row part build_farm() makes and every readout in the status
# area has an entry here.

LEGEND_GROUPS = [
    ("growth", "Growth stages (the picture on a plot)"),
    ("state", "Marks on a plot"),
    ("kind", "Kind of plot (the border)"),
    ("row", "Week rows and semester bands"),
    ("meter", "Meters and tallies"),
    ("tag", "Tags on question screens"),
]
STAGE_LEGEND_EXTRA = {STAGE_AUTOMATED: " A blue dot in the corner is the sprinkler."}
KIND_BORDER_WORDS = {
    "vocab": "A thin solid border: one word.",
    "phrase": "A dotted border: a whole phrase.",
    "grammar": "A dashed border: a grammar rule.",
    "phonetic": "A double border: a sound or a letter.",
}
GROWTH_TAG_MEANING = {
    "none": "Your answers here count toward your practice score, but no plot grows.",
    "apply": "Nothing changes while you answer. Press Apply at the end to sprout the weeks you passed.",
}
GROWTH_TAG_DEFAULT_MEANING = "A right answer waters the real plot it asks about (the first one each day), later ones only nudge it."
legend_open = False
_legend_drawn = False


def _legend_sentence(legend):
    """"Name — a, b" becomes "A: b." so a one-line legend phrase reads as a sentence."""
    rest = legend.partition(" — ")[2].replace(", ", ": ", 1)
    return rest[:1].upper() + rest[1:] + "."


def legend_indicators():
    """[{id, group, name, meaning, sample, classes, icon, text, elements, locked_row}]
    in the order the guide lists them. `classes` are the CSS classes the sample is
    drawn with (and so the ones the coverage tests look for)."""
    items = []

    def add(group, key, name, meaning, sample, classes=(), icon="", text="", elements=(), locked_row=False, growth=""):
        items.append({
            "id": key, "group": group, "name": name, "meaning": meaning, "sample": sample,
            "classes": list(classes), "icon": icon, "text": text, "elements": list(elements),
            "locked_row": locked_row, "growth": growth,
        })

    for stage in STAGE_ORDER:
        name, _sep, rest = STAGE_LABEL[stage].partition(" — ")
        add("growth", f"stage-{stage}", name, rest[:1].upper() + rest[1:] + "." + STAGE_LEGEND_EXTRA.get(stage, ""),
            "plot", ["plot", f"plot--{stage}"], icon=STAGE_ICON[stage])

    seed, sprout = STAGE_ICON[STAGE_SEED], STAGE_ICON[STAGE_SPROUT]
    add("state", "mark-wilting", "Drooping", _legend_sentence(WILTING_LEGEND),
        "plot", ["plot", f"plot--{STAGE_SPROUT}", "plot--wilting"], icon=sprout)
    add("state", "mark-weeds", "Weeds", _legend_sentence(WEEDS_LEGEND) + " A small olive dot sits in the corner.",
        "plot", ["plot", f"plot--{STAGE_SPROUT}", "plot--weeds"], icon=sprout)
    add("state", "mark-due", "Ready for water", "Due today: a thin inner outline. " + DUE_NOTE[:1].upper() + DUE_NOTE[1:] + ".",
        "plot", ["plot", f"plot--{STAGE_SEED}", "plot--due"], icon=seed)
    add("state", "mark-golden", "Golden plot", f"Today's golden plot, a gold ring. A correct answer on it earns {GOLDEN_POINTS} practice points.",
        "plot", ["plot", f"plot--{STAGE_SEED}", "plot--golden"], icon=seed)
    add("state", "mark-leech", "Stubborn weed", f"Missed {LEECH_THRESHOLD} times in a row: a dark corner wedge. A short re-teach card shows before the question.",
        "plot", ["plot", f"plot--{STAGE_SEED}", "plot--leech"], icon=seed)
    add("state", "mark-amis", "False friend", "Its French word looks like an English one but means something else: a dark wedge in the opposite corner.",
        "plot", ["plot", f"plot--{STAGE_SEED}", "plot--amis"], icon=seed)
    add("state", "mark-locked", "Locked", "Faded and greyed out. Its week opens when the week before has all sprouted.",
        "plot", ["plot", f"plot--{STAGE_SEED}", "plot--locked"], icon=seed)
    add("state", "mark-skin", "Plot skin", "A frame from the Farm shop. It changes the ring and corners only, never the marks above.",
        "text", [], icon="🪙", text="Farm shop skin")

    for kind in FARM_TYPE_ORDER:
        add("kind", f"type-{kind}", FARM_FILTERS[kind], KIND_BORDER_WORDS[kind],
            "plot", ["plot", f"plot--{STAGE_SEED}", f"plot--type-{kind}"], icon=seed)

    example = state.rows[0] if state.rows else None
    add("row", "row-label", "Week label", "The week's place in the farm, then its course and its week in that course.",
        "row", ["row-label"], text=example.label if example else "1. FREN151 wk 1")
    add("row", "row-chapter", "Chapter", "The chapter the week belongs to.",
        "row", ["row-chapter"], text=example.chapter_label if example else "Ch. 1")
    add("row", "row-progress", "Growth count", "Plots grown past Seed out of the plots in the week. Hover it to see how many were ever watered.",
        "row", ["row-progress"], text="3/12")
    add("row", "row-due", "Ready count", "How many plots in the week are ready for water.",
        "row", ["row-due"], text=ROW_DUE_NOTE.format(count=5))
    add("row", "row-perfect-badge", "Perfect week", "Every plot in the week answered right this session with no miss. It clears when you close the page.",
        "row", ["row-perfect-badge"], text="⭐ Perfect this session")
    add("row", "row-lock", "Locked week", "A dashed, faded week. It opens when every plot in the week before has at least sprouted.",
        "row", ["row--locked", "row-lock"], text=LOCK_NOTE.format(previous=4), locked_row=True)
    add("row", "semester-head", "Semester band", "One heading per semester, with its own progress line and meter. Hide weeks folds it away; the farm stays one list.",
        "row", ["semester-head", "semester-title"], text="Semester 1 · FREN151")
    add("row", "semester-chip", "Semester summary", "One line per semester above the farm: how much of it is growing and automated.",
        "text", ["semester-chip"], text=SEMESTER_CHIP.format(name="Semester 1", course="FREN151", percent=40, automated=6))

    add("meter", "automated-meter", "Automated meter", "How much of the whole farm is automated, filling left to right.",
        "meter", ["automated-meter", "automated-bar"], text="35", elements=["automated-meter", "automated-bar"])
    add("meter", "semester-meter", "Semester meter", "How much of one semester is growing (past Seed), filling left to right.",
        "meter", ["automated-meter", "semester-meter", "automated-bar"], text="60")
    add("meter", "stage-summary", "Stage tally", "How many plots sit at each growth stage.",
        "text", ["stage-summary"], text=" · ".join(f"{STAGE_ICON[stage]} {count}" for stage, count in zip(STAGE_ORDER, (40, 12, 8, 4, 2))),
        elements=["stage-summary-display"])
    add("meter", "readout-day", "Day", "The farm's own day. It only moves when you press Next day.", "text", [], text="Day 3", elements=["day-display"])
    add("meter", "readout-due", "Plots ready", "How many plots are ready for water today.",
        "text", ["status-line--due"], text=DUE_MESSAGE_MANY.format(count=12), elements=["due-display"])
    add("meter", "readout-progress", "Growing count", "Plots past Seed out of all plots, and how many are automated.",
        "text", [], text="40 of 790 plots growing · 6 automated", elements=["progress-display"])
    add("meter", "readout-rows-open", "Rows open", "How many weeks have opened so far.", "text", [], text="8 of 23 rows open", elements=["row-summary-display"])
    add("meter", "readout-practice-score", "Practice score", "Points from minigames, drills and tests. Every practice answer adds to it.",
        "text", [], text="Practice score: 12", elements=["practice-score-display"])
    add("meter", "readout-title", "Title", "Your title, and the score for the next one.", "text", [], text="Title: Apprenti (next: Jardinier at 25)",
        elements=["player-title-display"])
    add("meter", "readout-exam", "Exam countdown", "Days to your exam date and how much of the farm should be automated by then. Hidden until you set a date.",
        "text", [], text="Exam in 12 days · about 40% automated by then", elements=["exam-countdown-display"])
    add("meter", "readout-golden", "Golden plot line", "Names today's golden plot, or says you have claimed it.",
        "text", [], text=f"Golden plot claimed today: +{GOLDEN_POINTS} practice points.", elements=["golden-display"])
    add("meter", "readout-goals", "Daily goals", "How many of today's three goals are done.", "text", [], text=f"Daily goals: 1 of {QUESTS_PER_DAY} done", elements=["quest-display"])
    add("meter", "readout-coins", "Coins", "One coin for each full watering. Spend them in the Farm shop.", "text", [], text="🪙 7 coins", elements=["coins-display"])
    add("meter", "readout-combo", "Combo", "Shows after two or more right answers in a row. It is a nice moment, not a score to protect.",
        "text", [], text="3 correct in a row — nice pace.", elements=["combo-display"])
    add("meter", "readout-buddy", "Study buddy", "Only with Study buddy on: a suggestion for how long to study today.",
        "text", [], text="Study buddy: a short session is enough today.", elements=["study-buddy-display"])

    seen = set()
    for _key, (kind, text, _tip) in GROWTH_INFO.items():
        if text in seen:
            continue
        seen.add(text)
        add("tag", f"tag-{kind}", text, GROWTH_TAG_MEANING.get(kind, GROWTH_TAG_DEFAULT_MEANING),
            "tag", ["growth-marker"], text=text, growth=kind)
    return items


def _legend_sample(item):
    """The drawn sample for one indicator, using the farm's own CSS classes."""
    kind = item["sample"]
    wrapper = document.createElement("span")
    wrapper.className = "legend-sample"
    wrapper.setAttribute("aria-hidden", "true")
    if kind == "plot":
        cell = document.createElement("span")
        cell.className = " ".join(item["classes"])
        cell.innerText = item["icon"]
        wrapper.appendChild(cell)
    elif kind == "row":
        card = document.createElement("span")
        card.className = "row legend-row-sample" + (" row--locked" if item["locked_row"] else "")
        inner = document.createElement("span")
        inner.className = " ".join(c for c in item["classes"] if c != "row--locked")
        inner.innerText = item["text"]
        card.appendChild(inner)
        wrapper.appendChild(card)
    elif kind == "meter":
        meter = document.createElement("span")
        meter.className = " ".join(c for c in item["classes"] if c != "automated-bar") + " legend-meter"
        bar = document.createElement("span")
        bar.className = "automated-bar"
        bar.style.width = f"{item['text']}%"
        meter.appendChild(bar)
        wrapper.appendChild(meter)
    elif kind == "tag":
        tag = document.createElement("span")
        tag.className = "growth-marker"
        tag.setAttribute("data-growth", item["growth"])
        tag.innerText = item["text"]
        wrapper.appendChild(tag)
    else:
        text = document.createElement("span")
        text.className = "legend-sample-text dashboard-health-row " + " ".join(item["classes"])
        text.innerText = (item["icon"] + " " if item["icon"] else "") + item["text"]
        wrapper.appendChild(text)
    return wrapper


def on_toggle_legend(event=None):
    global legend_open
    legend_open = not legend_open
    render_legend_guide()
    if legend_open:
        try:
            getattr(_element("legend-panel"), "scrollIntoView")()
        except Exception:
            pass


def render_legend_guide():
    global _legend_drawn
    panel = _element("legend-panel")
    toggle = _element("legend-toggle-button")
    toggle.innerText = "Hide colours and icons" if legend_open else "🎨 Colours and icons"
    panel.hidden = not legend_open
    if not legend_open:
        _legend_drawn = False
        return
    if _legend_drawn:
        return
    _legend_drawn = True
    panel.innerHTML = ""
    heading = document.createElement("h2")
    heading.className = "dashboard-heading legend-heading"
    heading.innerText = "What the colours and icons mean"
    panel.appendChild(heading)
    intro = document.createElement("p")
    intro.className = "dashboard-since"
    intro.innerText = "Each sample is drawn the way the farm draws it. Nothing here is a penalty: a plot can droop or tangle, but it never dies."
    panel.appendChild(intro)
    items = legend_indicators()
    for group, title in LEGEND_GROUPS:
        members = [item for item in items if item["group"] == group]
        if not members:
            continue
        group_heading = document.createElement("h3")
        group_heading.className = "legend-group-title dashboard-heading"
        group_heading.innerText = title
        panel.appendChild(group_heading)
        for item in members:
            row = document.createElement("div")
            row.id = f"legend-item-{item['id']}"
            row.className = "legend-item"
            row.appendChild(_legend_sample(item))
            words = document.createElement("span")
            words.className = "legend-words dashboard-health-row"
            name = document.createElement("strong")
            name.className = "legend-name"
            name.innerText = item["name"]
            words.appendChild(name)
            meaning = document.createElement("span")
            meaning.className = "legend-meaning"
            meaning.innerText = " " + item["meaning"]
            words.appendChild(meaning)
            row.appendChild(words)
            panel.appendChild(row)


# Improvement Ideas §4: optional, toggleable cultural/usage notes -- off the
# main screen by default so it adds depth without cluttering the core drill
# for anyone who just wants to water plots. Session-only, like the review
# controls above: no note ever grows a plant or affects unlocking.
cultural_notes_open = False


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


practice_ledger = {mode: _blank_practice_entry() for mode in PRACTICE_MODES}


def practice_score():
    """The player's total practice points across every mode."""
    return sum(entry["points"] for entry in practice_ledger.values())


def record_practice(mode, correct, points=1, count_study=True):
    """Tally one answered question for `mode`; True if it earned a point.
    `points` is how many it is worth (1, or 2 for a golden plot or a finished
    daily goal); the daily and lifetime caps clip it. `count_study` is False
    for a call that rides on an answer already counted as a study answer."""
    entry = practice_ledger.get(mode)
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
study_buddy_enabled = False


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
    global study_buddy_enabled
    study_buddy_enabled = not study_buddy_enabled
    render()


def render_study_buddy():
    button = _element("study-buddy-toggle-button")
    display = _element("study-buddy-display")
    button.innerText = f"Study buddy: {'on' if study_buddy_enabled else 'off'}"
    display.hidden = not study_buddy_enabled
    display.innerText = study_buddy_message() if study_buddy_enabled else ""


def gender_drill_accuracy_text():
    """L10 -- the gender-tagging drill's own running accuracy, read from the
    practice ledger (the same numbers the dashboard's per-mode section shows)."""
    entry = practice_ledger.get("gender")
    if not entry or entry["total"] == 0:
        return ""
    percent = round(100 * entry["correct"] / entry["total"])
    return f"Gender drill so far: {entry['correct']}/{entry['total']} right ({percent}%)"


# L-26 -- player titles that rise with the practice score (derived, never saved).
# The top title needs 600 of the 1,400 points the capped ledger can reach, so
# it stays comfortably reachable.
PLAYER_TITLES = ((0, "Apprenti"), (25, "Jardinier"), (150, "Fermier"), (600, "Maître de Ferme"))


def player_title(score=None):
    """(current title, next title or None, points needed for it or None)."""
    if score is None:
        score = practice_score()
    index = 0
    for i, (needed, _name) in enumerate(PLAYER_TITLES):
        if score >= needed:
            index = i
    name = PLAYER_TITLES[index][1]
    if index + 1 < len(PLAYER_TITLES):
        return name, PLAYER_TITLES[index + 1][1], PLAYER_TITLES[index + 1][0]
    return name, None, None


def player_title_text(score=None):
    name, next_name, next_at = player_title(score)
    if next_name is None:
        return f"Title: {name}"
    return f"Title: {name} (next: {next_name} at {next_at})"


def render_practice_score():
    _element("practice-score-display").innerText = f"Practice score: {practice_score()}"
    _element("player-title-display").innerText = player_title_text()


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

import csv  # noqa: E402
import io  # noqa: E402

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


# --- L-18: stubborn weeds ---------------------------------------------------
# A plot answered wrong LEECH_THRESHOLD times in a row (a correct answer
# resets the run) turns into a stubborn weed: it shows a re-teach card before
# its next question (the answer, chunked into syllable-like pieces, and a
# prompt to make your own memory hook) and offers to rest for a week.
LEECH_THRESHOLD = 4
LEECH_REST_DAYS = 7
LEECH_FAIL_RUN_LIMIT = 1000
leech_rests = 0  # how many times a stubborn plot has been rested (saved)
_VOWELS = "aeiouyàâäéèêëîïôöùûüœæ"


def _validated_fail_run(raw):
    if isinstance(raw, bool) or not isinstance(raw, int):
        return 0
    return max(0, min(raw, LEECH_FAIL_RUN_LIMIT))


def _validated_last_watered(record, plot):
    """The saved day of a plot's last full watering (a save from before the
    2026-10-08 watering rule has no such key, which reads as never: on the day
    of the upgrade those plots can be watered once more, which is harmless)."""
    raw = record.get("last_watered")
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        return None
    return raw


def _validated_leech_rests(raw):
    if isinstance(raw, bool) or not isinstance(raw, int):
        return 0
    return max(0, min(raw, PRACTICE_COUNT_LIMIT))


def is_leech(plot):
    return plot.fail_run >= LEECH_THRESHOLD


def leech_plots():
    return [p for p in state.plots if is_leech(p)]


def chunk_word(word):
    """Split one French word into syllable-like chunks ("bonjour" -> ["bon",
    "jour"]) for the re-teach card. Mechanical: vowel groups are the cores, a
    single consonant between two cores starts the next chunk, and a cluster
    splits after its first consonant unless it ends in l or r after another
    consonant (pl, tr, ...)."""
    lower = word.lower()
    cores = []
    index = 0
    while index < len(lower):
        if lower[index] in _VOWELS:
            start = index
            while index < len(lower) and lower[index] in _VOWELS:
                index += 1
            cores.append((start, index))
        else:
            index += 1
    # A silent ending (-e, -es, -ent) is not a syllable of its own: "madame"
    # is ma-dame, not ma-da-me.
    if len(cores) >= 2:
        last_start, last_end = cores[-1]
        tail = lower[last_start:]
        if lower[last_start:last_end] == "e" and tail in ("e", "es", "ent"):
            cores = cores[:-1]
    if len(cores) < 2:
        return [word]
    cuts = []
    for (_, previous_end), (next_start, _) in zip(cores, cores[1:]):
        gap = next_start - previous_end
        if gap <= 0:
            continue
        if gap == 1:
            cuts.append(previous_end)
        elif lower[next_start - 1] in "lr" and gap >= 2 and lower[next_start - 2] not in "lr":
            cuts.append(next_start - 2)
        else:
            cuts.append(previous_end + 1)
    pieces = []
    last = 0
    for cut in cuts:
        pieces.append(word[last:cut])
        last = cut
    pieces.append(word[last:])
    return [piece for piece in pieces if piece]


def chunk_text(text):
    """Chunk every word of `text`, words separated by three spaces."""
    words = []
    for word in str(text).split():
        letters = word.strip(".,;:!?¡¿()\"«»")
        words.append(" · ".join(chunk_word(letters)) if letters else word)
    return "   ".join(words)


def leech_reteach_lines(plot):
    """The three lines of a stubborn plot's re-teach card."""
    item = plot.items[0]
    fr = item.get("fr") or item.get("prompt") or plot.label
    en = item.get("en") or item.get("answer") or ""
    if plot.topic_type == "grammar":
        head = f"{plot.topic_title}: {fr}" + (f" = {en}" if en else "")
    else:
        head = f"{fr} = {en}" if en else str(fr)
    return [
        f"Stubborn weed: missed {plot.fail_run} times in a row. Here it is once more: {head}",
        "In pieces: " + chunk_text(fr),
        "Make your own hook: picture it, rhyme it or link it to a word you already know, then say it out loud once.",
    ]


def rest_leech(event=None):
    """Put the open stubborn plot aside for LEECH_REST_DAYS and close it."""
    global leech_rests
    if current_question is None:
        return False
    plot = state.plots_by_id.get(current_question["plot_id"])
    if plot is None or not is_leech(plot):
        return False
    plot.next_due = state.current_day + LEECH_REST_DAYS
    plot.fail_run = 0
    leech_rests = min(leech_rests + 1, PRACTICE_COUNT_LIMIT)
    close_practice()
    return True


def leech_summary_text():
    now = len(leech_plots())
    return f"Stubborn weeds: {now} now, {leech_rests} rested so far"


# --- L-19: "that was a slip" -------------------------------------------------
# Once per session, a typed miss that is only a slip of the fingers (a missed
# accent, or one close to the answer) can be forgiven: the plot goes back to
# exactly what it was before the answer, the combo and the error digest are
# put back, and the same plot gets a fresh question. Session state only.
SLIP_PATTERNS = (ERROR_PATTERN_ACCENT, ERROR_PATTERN_CLOSE_TYPO)
slip_used = False
_slip_snapshot = None
slip_note = ""


def _restore_plot(plot, record):
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


def can_forgive_slip():
    return (
        not slip_used
        and _slip_snapshot is not None
        and current_question is not None
        and current_result is False
        and current_question["mode"] == "typed"
        and _slip_snapshot["plot_id"] == current_question["plot_id"]
        and _slip_snapshot["pattern"] in SLIP_PATTERNS
    )


def forgive_slip(event=None):
    global slip_used, combo_count, slip_note, _slip_snapshot
    if not can_forgive_slip():
        return False
    snap = _slip_snapshot
    plot = state.plots_by_id[snap["plot_id"]]
    _restore_plot(plot, snap["record"])
    combo_count = snap["combo"]
    pattern = snap["pattern"]
    if error_pattern_counts.get(pattern, 0) > 1:
        error_pattern_counts[pattern] -= 1
    else:
        error_pattern_counts.pop(pattern, None)
    if snap["confidence"] in confidence_tally:
        confidence_tally[snap["confidence"]][1] = max(0, confidence_tally[snap["confidence"]][1] - 1)
    sequence = plot.sequence
    if snap["spoiled"]:
        row_session_spoiled.add(sequence)
    else:
        row_session_spoiled.discard(sequence)
    if snap["row_correct"]:
        row_session_correct[sequence] = set(snap["row_correct"])
    else:
        row_session_correct.pop(sequence, None)
    quest_state["day"] = snap["quest"]["day"]
    quest_state["progress"] = dict(snap["quest"]["progress"])
    quest_state["done"] = list(snap["quest"]["done"])
    slip_used = True
    _slip_snapshot = None
    open_practice(plot.plot_id)
    slip_note = "Slip forgiven: that answer was not counted. Same plot, fresh question."
    render()
    return True


# --- L-27: session highlights ----------------------------------------------
# What went well this sitting, shown on the Review and Proficiency results and
# in the dashboard. Session state, never saved. (A "quickest answer" is not
# tracked: this file deliberately has no clock.)
session_highlights = {"best_combo": 0, "toughest_label": None, "toughest_misses": 0}


def _note_highlights(plot, correct, prior_fail_run):
    if combo_count > session_highlights["best_combo"]:
        session_highlights["best_combo"] = combo_count
    if correct and prior_fail_run >= 1 and prior_fail_run > session_highlights["toughest_misses"]:
        session_highlights["toughest_label"] = plot.label
        session_highlights["toughest_misses"] = prior_fail_run


def session_highlights_text():
    parts = []
    if session_highlights["best_combo"] >= 2:
        parts.append(f"best combo {session_highlights['best_combo']} in a row")
    if session_highlights["toughest_label"]:
        misses = session_highlights["toughest_misses"]
        parts.append(
            f"toughest word beaten: {session_highlights['toughest_label']} "
            f"(missed {misses} time{'s' if misses != 1 else ''} in a row before)"
        )
    return "Highlights this session: " + "; ".join(parts) + "." if parts else ""


def _with_highlights(message):
    extra = session_highlights_text()
    return f"{message} {extra}" if extra else message


# --- L-29: weak-items export -----------------------------------------------
WEAK_EXPORT_HEADER = ["French", "English", "Topic", "Week", "Why it is here"]


def weak_items():
    """Every fact the farm has flagged: stubborn weeds, known mix-ups, plots
    whose last answer was wrong, and anything saved to the phrasebook."""
    rows = []
    for plot in state.plots:
        reasons = []
        if is_leech(plot):
            reasons.append("stubborn weed")
        if plot.in_weeds:
            reasons.append("known mix-up")
        if plot.last_reviewed is not None and plot.correct_streak == 0 and not is_leech(plot):
            reasons.append("missed last time")
        if plot.plot_id in phrasebook:
            reasons.append("in my phrasebook")
        if not reasons:
            continue
        for item in plot.items:
            fr = item.get("fr") or item.get("prompt") or ""
            en = item.get("en") or item.get("answer") or ""
            if not fr and not en:
                continue
            rows.append(
                {
                    "fr": str(fr),
                    "en": str(en),
                    "topic": plot.topic_title,
                    "week": f"{plot.course} wk {plot.week}",
                    "why": "; ".join(reasons),
                }
            )
    return rows


def weak_items_csv():
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(WEAK_EXPORT_HEADER)
    for row in weak_items():
        writer.writerow([row["fr"], row["en"], row["topic"], row["week"], row["why"]])
    return buffer.getvalue()


def weak_items_anki():
    """Tab-separated text Anki's importer reads (front, back, tags)."""
    lines = ["#separator:tab", "#html:false", "#tags column:3"]
    for row in weak_items():
        tags = " ".join(part.strip().replace(" ", "_") for part in row["why"].split(";"))
        front = row["fr"].replace("\t", " ").replace("\n", " ")
        back = row["en"].replace("\t", " ").replace("\n", " ")
        lines.append(f"{front}\t{back}\t{tags}")
    return "\n".join(lines) + "\n"


_last_download = None


def _download_text(filename, text, mime):
    """Hands a file to the page's own downloader (index.html), the same
    Python-computes/JS-does-the-browser-thing split as the report sender.
    Remembers the last request so a test can read it."""
    global _last_download
    _last_download = {"filename": filename, "text": text, "mime": mime}
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    hook = getattr(window, "championDownload", None)
    if hook is None:
        return False
    hook(filename, text, mime)
    return True


def export_weak_items_csv(event=None):
    return _download_text("champ-de-mots-weak-items.csv", weak_items_csv(), "text/csv")


def export_weak_items_anki(event=None):
    return _download_text("champ-de-mots-weak-items-anki.txt", weak_items_anki(), "text/plain")


# Improvement Ideas §5: a progress dashboard, deliberately its own separate
# screen rather than more numbers crammed into the calm main status line --
# per-row mastery, the weakest touched topics, and how long it's been since
# anything was watered at all. Purely a read-out: nothing here mutates SRS
# state, same posture as the Review tab's own informational pieces.
DASHBOARD_WEAKEST_TOPIC_COUNT = 5
dashboard_open = False


def dashboard_row_mastery(sequence):
    """0-100: how far a row's plots have grown on average, scaled by the
    highest reachable stage rank -- not just "% Automated," so partial
    progress (a row full of Sprouts) still reads as real progress."""
    plots = state.row_plots(sequence)
    if not plots:
        return 0.0
    max_rank = len(STAGE_ORDER) - 1
    return sum(STAGE_RANK[p.stage] for p in plots) / (len(plots) * max_rank) * 100


def dashboard_weakest_topics(limit=DASHBOARD_WEAKEST_TOPIC_COUNT):
    """The lowest-average-stage topics among ones you've actually touched at
    least once -- an untouched topic isn't "weak," it's just not started
    yet, so it's excluded rather than tying every fresh row for last place."""
    scored = []
    for record in state.topic_records:
        if not state.is_row_unlocked(record["sequence"]):
            continue
        plots = _topic_plots(record["topic"])
        touched = [p for p in plots if p.last_reviewed is not None]
        if not touched:
            continue
        avg_rank = sum(STAGE_RANK[p.stage] for p in touched) / len(touched)
        scored.append(
            {
                "topic_id": record["topic"]["id"],
                "title": record["topic"]["title"],
                "sequence": record["sequence"],
                "avg_rank": avg_rank,
            }
        )
    scored.sort(key=lambda entry: entry["avg_rank"])
    return scored[:limit]


def dashboard_days_since_last_touch():
    """None if nothing has ever been watered; otherwise how many in-game
    days have passed since the most recently touched plot."""
    touched_days = [p.last_reviewed for p in state.plots if p.last_reviewed is not None]
    if not touched_days:
        return None
    return state.current_day - max(touched_days)


# ===========================================================================
# L7a/L7b: a real calendar-day concept and a lightweight study calendar.
# `state.current_day` is the SRS's own in-game day counter (advanced by the
# player), so it says nothing about real dates. This records which REAL
# calendar days had any study activity, as {"YYYY-MM-DD": answers}. The date
# itself comes from a JS hook (window.studyToday, in index.html) because this
# file may not touch any clock API (Milestone 7's tested constraint). No
# streak counter, no missed-day marker: the calendar only ever shows what you
# DID, matching this game's no-guilt stance (section 3).
# ===========================================================================
STUDY_DAY_LIMIT = 400  # newest days kept, so the save stays small
STUDY_COUNT_LIMIT = 9999
CALENDAR_MONTHS_BACK = 36
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
study_days = {}
calendar_open = False
calendar_view = None  # (year, month) being shown; None means today's month
_today_override = None  # tests only


def _parse_iso_date(text):
    """(year, month, day) for a real 'YYYY-MM-DD' date, else None."""
    if not isinstance(text, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    year, month, day = int(text[0:4]), int(text[5:7]), int(text[8:10])
    if year < 1970 or year > 2200 or month < 1 or month > 12:
        return None
    if day < 1 or day > _calendar.monthrange(year, month)[1]:
        return None
    return year, month, day


def study_today():
    """Today's real date as 'YYYY-MM-DD', or None when there's no clock."""
    if _today_override is not None:
        return _today_override
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return None
    hook = getattr(window, "studyToday", None)
    if hook is None:
        return None
    value = hook()
    return value if _parse_iso_date(value) else None


def note_study_answer():
    """Count one answered question against today's real date."""
    day = study_today()
    if day is None:
        return
    study_days[day] = min(study_days.get(day, 0) + 1, STUDY_COUNT_LIMIT)
    if len(study_days) > STUDY_DAY_LIMIT:
        for old in sorted(study_days)[: len(study_days) - STUDY_DAY_LIMIT]:
            del study_days[old]


def _validated_study_days(raw):
    if not isinstance(raw, dict):
        return {}
    clean = {}
    for key, count in raw.items():
        if _parse_iso_date(key) is None:
            continue
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            continue
        clean[key] = min(count, STUDY_COUNT_LIMIT)
    for old in sorted(clean)[: max(0, len(clean) - STUDY_DAY_LIMIT)]:
        del clean[old]
    return clean


def calendar_month_days(year, month):
    """Weeks of the month, Monday first: [[day-or-0 x 7], ...]."""
    return _calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)


def calendar_current_view():
    if calendar_view is not None:
        return calendar_view
    today = _parse_iso_date(study_today())
    if today is not None:
        return today[0], today[1]
    if study_days:
        latest = _parse_iso_date(max(study_days))
        return latest[0], latest[1]
    return None


def _shift_month(view, delta):
    year, month = view
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def _calendar_view_allowed(view):
    today = _parse_iso_date(study_today())
    if today is None:
        return True
    now = today[0] * 12 + today[1] - 1
    shown = view[0] * 12 + view[1] - 1
    return now - CALENDAR_MONTHS_BACK <= shown <= now


def on_toggle_calendar(event=None):
    global calendar_open, calendar_view
    calendar_open = not calendar_open
    if not calendar_open:
        calendar_view = None
    render_calendar()


def _on_calendar_shift(delta):
    global calendar_view
    view = calendar_current_view()
    if view is None:
        return
    target = _shift_month(view, delta)
    if _calendar_view_allowed(target):
        calendar_view = target
    render_calendar()


def on_calendar_prev(event=None):
    _on_calendar_shift(-1)


def on_calendar_next(event=None):
    _on_calendar_shift(1)


def render_calendar():
    panel = _element("calendar-panel")
    toggle = _element("calendar-toggle-button")
    toggle.innerText = "Hide study calendar" if calendar_open else "🗓️ Study calendar"
    panel.hidden = not calendar_open
    if not calendar_open:
        return
    grid = _element("calendar-grid")
    grid.innerHTML = ""
    view = calendar_current_view()
    if view is None:
        _element("calendar-month-label").innerText = ""
        _element("calendar-summary").innerText = (
            "Nothing to show yet. Answer a question and today will appear here."
        )
        return
    year, month = view
    _element("calendar-month-label").innerText = f"{MONTH_NAMES[month - 1]} {year}"
    _element("calendar-prev-button").disabled = not _calendar_view_allowed(_shift_month(view, -1))
    _element("calendar-next-button").disabled = not _calendar_view_allowed(_shift_month(view, 1))
    today = _parse_iso_date(study_today())
    for name in WEEKDAY_NAMES:
        head = document.createElement("span")
        head.className = "calendar-weekday"
        head.innerText = name
        grid.appendChild(head)
    studied_here = 0
    for week in calendar_month_days(year, month):
        for day in week:
            cell = document.createElement("span")
            if day == 0:
                cell.className = "calendar-cell calendar-cell--blank"
                grid.appendChild(cell)
                continue
            iso = f"{year:04d}-{month:02d}-{day:02d}"
            answers = study_days.get(iso, 0)
            is_today = today == (year, month, day)
            cell.className = "calendar-cell"
            if answers:
                studied_here += 1
                cell.className += " calendar-cell--studied"
            if is_today:
                cell.className += " calendar-cell--today"
            label = f"{day} {MONTH_NAMES[month - 1]}"
            if answers:
                label += f": {answers} answer{'s' if answers != 1 else ''}"
            if is_today:
                label += " (today)"
            cell.setAttribute("aria-label", label)
            cell.title = label
            number = document.createElement("span")
            number.className = "calendar-day-number"
            number.innerText = str(day)
            cell.appendChild(number)
            if answers:
                count = document.createElement("span")
                count.className = "calendar-day-count"
                count.innerText = f"\u00b7{answers}"
                cell.appendChild(count)
            grid.appendChild(cell)
    if studied_here:
        noun = "day" if studied_here == 1 else "days"
        summary = f"You studied on {studied_here} {noun} this month."
    else:
        summary = "No study days recorded this month. Nothing here ever expires."
    _element("calendar-summary").innerText = summary


# ===========================================================================
# L19: a personal phrasebook -- bookmark any plot into a custom list that
# cuts across the syllabus rows, and practise just that list. Saved as a list
# of plot ids (validated against the real farm on load), newest last.
# ===========================================================================
PHRASEBOOK_LIMIT = 200
PHRASEBOOK_SESSION_MAX = 40
PHRASEBOOK_MODE = "phrasebook"
PHRASEBOOK_EMPTY_MESSAGE = "Your phrasebook is empty. Use the star while you practise to save an item here."
phrasebook = []
phrasebook_open = False
phrasebook_proxies = []


def in_phrasebook(plot_id):
    return plot_id in phrasebook


def toggle_phrasebook(plot_id):
    """Add or remove `plot_id`; returns True if it is now in the phrasebook."""
    if plot_id not in state.plots_by_id:
        return False
    if plot_id in phrasebook:
        phrasebook.remove(plot_id)
        return False
    if len(phrasebook) >= PHRASEBOOK_LIMIT:
        return False
    phrasebook.append(plot_id)
    return True


def _validated_phrasebook(raw):
    if not isinstance(raw, list):
        return []
    clean = []
    for plot_id in raw:
        if isinstance(plot_id, str) and plot_id in state.plots_by_id and plot_id not in clean:
            clean.append(plot_id)
    return clean[:PHRASEBOOK_LIMIT]


def phrasebook_entry_text(plot):
    """One readable line for a saved plot: the French and its meaning."""
    if plot.topic_type == "grammar":
        return f"{plot.label}: {plot.rule}" if plot.rule else str(plot.label)
    return f"{plot.label} \u2014 {plot.items[0]['en']}"


def _destroy_phrasebook_proxies():
    for proxy in phrasebook_proxies:
        proxy.destroy()
    phrasebook_proxies.clear()


def _make_phrasebook_remove_handler(plot_id):
    def handler(event=None):
        if plot_id in phrasebook:
            phrasebook.remove(plot_id)
        render()
    return handler


def on_toggle_phrasebook_panel(event=None):
    global phrasebook_open
    phrasebook_open = not phrasebook_open
    render()


def on_bookmark_practice(event=None):
    if current_question is not None:
        toggle_phrasebook(current_question["plot_id"])
        render()


def on_bookmark_review(event=None):
    if review_question is not None:
        toggle_phrasebook(review_question["plot_id"])
        render()


def on_start_phrasebook_review(event=None):
    start_review(PHRASEBOOK_MODE)


def _render_bookmark_button(button_id, question):
    button = _element(button_id)
    if question is None:
        button.hidden = True
        return
    button.hidden = False
    saved = in_phrasebook(question["plot_id"])
    button.innerText = "\u2605 In your phrasebook (remove)" if saved else "\u2606 Save to phrasebook"
    button.setAttribute("aria-pressed", "true" if saved else "false")


def render_phrasebook():
    _render_bookmark_button("practice-bookmark-button", current_question if practice_open else None)
    _render_bookmark_button("review-bookmark-button", review_question if review_mode is not None else None)
    _destroy_phrasebook_proxies()
    toggle = _element("phrasebook-toggle-button")
    toggle.innerText = (
        "Hide phrasebook" if phrasebook_open else f"\U0001F4D2 My phrasebook ({len(phrasebook)})"
    )
    panel = _element("phrasebook-panel")
    panel.hidden = not phrasebook_open
    if not phrasebook_open:
        return
    listing = _element("phrasebook-list")
    listing.innerHTML = ""
    _element("phrasebook-practice-button").disabled = not phrasebook
    if not phrasebook:
        empty = document.createElement("p")
        empty.className = "row-blurb"
        empty.innerText = PHRASEBOOK_EMPTY_MESSAGE
        listing.appendChild(empty)
        return
    for plot_id in phrasebook:
        plot = state.plots_by_id[plot_id]
        row = document.createElement("div")
        row.className = "phrasebook-row"
        text = document.createElement("span")
        text.className = "phrasebook-text"
        text.innerText = phrasebook_entry_text(plot)
        remove = document.createElement("button")
        remove.className = "secondary phrasebook-remove"
        remove.type = "button"
        remove.innerText = "Remove"
        remove.setAttribute("aria-label", f"Remove {plot.label} from your phrasebook")
        proxy = create_proxy(_make_phrasebook_remove_handler(plot_id))
        phrasebook_proxies.append(proxy)
        remove.addEventListener("click", proxy)
        row.appendChild(text)
        row.appendChild(remove)
        listing.appendChild(row)


# ===========================================================================
# L15: an optional grammar deep-dive for grammar plots -- everything the game
# already knows about a topic, gathered in one place beyond the terse
# in-practice rule. Derived entirely from catalog data and existing helpers
# (no hand-written text to drift): the full rule, every example, the known
# look-alikes it is easy to mix up with, and where the plot stands.
# ===========================================================================
DEEP_DIVE_NO_RULE = "This topic has no written rule yet; the examples below are the pattern."
deepdive_open = False


def grammar_deep_dive(plot):
    """Plain data for the deep-dive panel, or None for a non-grammar plot."""
    if plot is None or plot.topic_type != "grammar":
        return None
    due = ""
    if plot.next_due is not None:
        days = plot.next_due - state.current_day
        due = "due now" if days <= 0 else f"next due in {days} day{'s' if days != 1 else ''}"
    return {
        "title": plot.topic_title,
        "rule": plot.rule or DEEP_DIVE_NO_RULE,
        "has_rule": bool(plot.rule),
        "examples": [(item["fr"], item["en"]) for item in plot.items],
        "confusions": weeds_confusions_for(plot),
        "stage": STAGE_LABEL[plot.stage],
        "due": due,
    }


def on_toggle_deepdive(event=None):
    global deepdive_open
    deepdive_open = not deepdive_open
    render_deepdive()


def render_deepdive():
    toggle = _element("practice-deepdive-button")
    panel = _element("practice-deepdive")
    plot = state.plots_by_id.get(current_question["plot_id"]) if practice_open and current_question else None
    data = grammar_deep_dive(plot)
    if data is None:
        toggle.hidden = True
        panel.hidden = True
        return
    toggle.hidden = False
    toggle.innerText = "Hide grammar deep-dive" if deepdive_open else "\U0001F4D8 Grammar deep-dive"
    toggle.setAttribute("aria-expanded", "true" if deepdive_open else "false")
    panel.hidden = not deepdive_open
    if not deepdive_open:
        return
    panel.innerHTML = ""

    def line(class_name, text):
        node = document.createElement("p")
        node.className = class_name
        node.innerText = text
        panel.appendChild(node)

    line("deepdive-title", data["title"])
    line("deepdive-rule", data["rule"])
    line("deepdive-heading", "Examples")
    for fr, en in data["examples"]:
        line("deepdive-example", f"{fr} \u2014 {en}")
    if data["confusions"]:
        line("deepdive-heading", "Easy to mix up with")
        line("deepdive-confusions", ", ".join(f"\u201c{c}\u201d" for c in data["confusions"]))
    status = data["stage"] + (f" \u00b7 {data['due']}" if data["due"] else "")
    line("deepdive-status", "Where this plot stands: " + status)


def on_toggle_dashboard(event=None):
    global dashboard_open
    dashboard_open = not dashboard_open
    render()


def srs_explanation_lines():
    """L23 -- a plain-language account of the scheduler, built from the real
    constants above so it can never drift from what actually runs."""
    return [
        f"Every plot has a review interval and an ease score (starts at {DEFAULT_EASE}, always kept between {MIN_EASE} and {MAX_EASE}).",
        f"Your first correct answer schedules the next review {FIRST_INTERVAL_DAYS} day out and your second {SECOND_INTERVAL_DAYS} days out.",
        "From the third correct answer on, the interval grows by its ease score each time (and always by at least one day).",
        f"Each correct answer nudges ease up by {EASE_CORRECT_BONUS}; each wrong answer drops it by {EASE_INCORRECT_PENALTY} and sends the plot back to a {RESET_INTERVAL_DAYS}-day interval with its streak reset.",
        f"Combo bonus: each answer in a correct row shortens the wait a little more, {int(COMBO_BONUS_PER_STEP * 100)}% per step, capped at {int(MAX_COMBO_BONUS * 100)}%.",
        f"Confidence: tagging 'Sure' before a wrong answer makes that penalty {CONFIDENT_WRONG_PENALTY_MULTIPLIER}x; tagging 'Not sure' makes it {UNSURE_WRONG_PENALTY_MULTIPLIER}x. It never changes what a correct answer does.",
        f"Growth stages follow the interval: Blooming from {BLOOMING_INTERVAL_DAYS} days, Automated from {AUTOMATION_INTERVAL_DAYS} days. A plot never visibly shrinks back a stage.",
    ]


def render_srs_explainer():
    details = _element("srs-explainer")
    details.hidden = not dashboard_open
    body = _element("srs-explainer-body")
    body.innerHTML = ""
    for line in srs_explanation_lines():
        item = document.createElement("p")
        item.className = "srs-explainer-line"
        item.innerText = line
        body.appendChild(item)


def dashboard_stage_distribution():
    """L27 -- how the whole farm's plots split across the five growth
    stages: [(stage, count, percent)] in STAGE_ORDER. Purely a count of
    existing plot.stage values, no new state."""
    total = len(state.plots)
    counts = {stage: 0 for stage in STAGE_ORDER}
    for plot in state.plots:
        counts[plot.stage] += 1
    return [(stage, counts[stage], (100 * counts[stage] / total) if total else 0.0) for stage in STAGE_ORDER]


dashboard_proxies = []


def _destroy_dashboard_proxies():
    for proxy in dashboard_proxies:
        proxy.destroy()
    dashboard_proxies.clear()


def _dashboard_line(panel, class_name, text):
    line = document.createElement("p")
    line.className = class_name
    line.innerText = text
    panel.appendChild(line)
    return line


def _dashboard_button(panel, label, handler):
    button = document.createElement("button")
    button.className = "secondary dashboard-action"
    button.type = "button"
    button.innerText = label
    proxy = create_proxy(handler)
    button.addEventListener("click", proxy)
    dashboard_proxies.append(proxy)
    panel.appendChild(button)
    return button


def _render_dashboard_extras(panel):
    """Round 3 batch 2: today's daily goals, the stubborn weeds, the weak-items
    export and this session's highlights."""
    _dashboard_line(panel, "dashboard-heading", quest_summary_text())
    for text, progress, target, done in quest_lines():
        mark = "Done" if done else f"{progress} of {target}"
        _dashboard_line(panel, "dashboard-practice-row", f"{text} — {mark}")
    _dashboard_line(
        panel,
        "dashboard-empty",
        f"Each finished goal earns {QUEST_REWARD_POINTS} practice points. Goals change with the in-game day; nothing carries over or runs out.",
    )

    _dashboard_line(panel, "dashboard-heading", "Stubborn weeds and weak items")
    _dashboard_line(panel, "dashboard-practice-row", leech_summary_text())
    for plot in leech_plots()[:5]:
        _dashboard_line(panel, "dashboard-weakest-topic", f"{plot.label} (wk {plot.sequence}), missed {plot.fail_run} in a row")
    weak_count = len(weak_items())
    _dashboard_line(
        panel,
        "dashboard-practice-row",
        f"{weak_count} weak item{'s' if weak_count != 1 else ''} ready to export (stubborn weeds, mix-ups, last-missed and phrasebook plots).",
    )
    _dashboard_button(panel, "Download weak items (CSV)", export_weak_items_csv)
    _dashboard_button(panel, "Download for Anki (tab-separated)", export_weak_items_anki)

    highlights = session_highlights_text()
    if highlights:
        _dashboard_line(panel, "dashboard-heading", "Session highlights")
        _dashboard_line(panel, "dashboard-practice-row", highlights)


def render_dashboard():
    panel = _element("dashboard-panel")
    toggle = _element("dashboard-toggle-button")
    toggle.innerText = "Hide progress dashboard" if dashboard_open else "Progress dashboard"
    panel.hidden = not dashboard_open
    render_srs_explainer()
    if not dashboard_open:
        return

    _destroy_dashboard_proxies()
    panel.innerHTML = ""

    since = dashboard_days_since_last_touch()
    since_line = document.createElement("p")
    since_line.className = "dashboard-since"
    if since is None:
        since_line.innerText = "Nothing watered yet."
    elif since == 0:
        since_line.innerText = "Last watered something today."
    elif since == 1:
        since_line.innerText = "Last watered something 1 day ago."
    else:
        since_line.innerText = f"Last watered something {since} days ago."
    panel.appendChild(since_line)

    health_heading = document.createElement("p")
    health_heading.className = "dashboard-heading"
    health_heading.innerText = "Farm health"
    panel.appendChild(health_heading)
    for stage, count, percent in dashboard_stage_distribution():
        health_row = document.createElement("p")
        health_row.className = "dashboard-health-row"
        health_row.innerText = f"{STAGE_ICON[stage]} {STAGE_LABEL[stage].split(' — ')[0]}: {count} ({percent:.0f}%)"
        health_bar = document.createElement("span")
        health_bar.className = "dashboard-health-bar"
        health_bar.style.width = f"{percent:.1f}%"
        health_row.appendChild(health_bar)
        panel.appendChild(health_row)

    mastery_heading = document.createElement("p")
    mastery_heading.className = "dashboard-heading"
    mastery_heading.innerText = "Mastery by week"
    panel.appendChild(mastery_heading)
    mastery_list = document.createElement("div")
    mastery_list.className = "dashboard-mastery-list"
    for row in state.rows:
        if not state.is_row_unlocked(row.sequence):
            continue
        line = document.createElement("p")
        line.className = "dashboard-mastery-row"
        line.innerText = f"{row.label} — {dashboard_row_mastery(row.sequence):.0f}%"
        mastery_list.appendChild(line)
    panel.appendChild(mastery_list)

    weakest_heading = document.createElement("p")
    weakest_heading.className = "dashboard-heading"
    weakest_heading.innerText = "Could use more water"
    panel.appendChild(weakest_heading)
    weakest = dashboard_weakest_topics()
    if not weakest:
        empty = document.createElement("p")
        empty.className = "dashboard-empty"
        empty.innerText = "Nothing stands out yet — water a few plots first."
        panel.appendChild(empty)
    else:
        weakest_list = document.createElement("div")
        weakest_list.className = "dashboard-weakest-list"
        for entry in weakest:
            line = document.createElement("p")
            line.className = "dashboard-weakest-topic"
            line.innerText = f"{entry['title']} (wk {entry['sequence']})"
            weakest_list.appendChild(line)
        panel.appendChild(weakest_list)

    practice_heading = document.createElement("p")
    practice_heading.className = "dashboard-heading"
    practice_heading.innerText = f"Practice progress — {practice_score()} {'point' if practice_score() == 1 else 'points'}"
    panel.appendChild(practice_heading)
    practice_list = document.createElement("div")
    practice_list.className = "dashboard-practice-list"
    for mode, label in PRACTICE_MODES.items():
        entry = practice_ledger[mode]
        line = document.createElement("p")
        line.className = "dashboard-practice-row"
        if entry["total"]:
            accuracy = round(entry["correct"] / entry["total"] * 100)
            line.innerText = (
                f"{label} — {entry['correct']} of {entry['total']} correct ({accuracy}%) · "
                f"{entry['points']}/{PRACTICE_MODE_CAP} points"
            )
        else:
            line.innerText = f"{label} — not played yet"
        practice_list.appendChild(line)
    panel.appendChild(practice_list)

    _render_dashboard_extras(panel)

    patterns_heading = document.createElement("p")
    patterns_heading.className = "dashboard-heading"
    patterns_heading.innerText = "Common patterns"
    panel.appendChild(patterns_heading)
    present_patterns = [p for p in ERROR_PATTERN_ORDER if error_pattern_counts.get(p)]
    if not present_patterns:
        empty = document.createElement("p")
        empty.className = "dashboard-empty"
        empty.innerText = "No wrong typed answers yet — nothing to spot a pattern in."
        panel.appendChild(empty)
    else:
        patterns_list = document.createElement("div")
        patterns_list.className = "dashboard-patterns-list"
        for pattern in present_patterns:
            line = document.createElement("p")
            line.className = "dashboard-pattern-row"
            count = error_pattern_counts[pattern]
            times = "time" if count == 1 else "times"
            line.innerText = f"{ERROR_PATTERN_LABELS[pattern]} — {count} {times}"
            patterns_list.appendChild(line)
        panel.appendChild(patterns_list)


def on_toggle_cultural_notes(event=None):
    global cultural_notes_open
    cultural_notes_open = not cultural_notes_open
    render()


def render_cultural_notes():
    panel = _element("cultural-notes-panel")
    toggle = _element("cultural-notes-toggle-button")
    toggle.innerText = "Hide cultural notes" if cultural_notes_open else "Cultural notes"
    panel.hidden = not cultural_notes_open
    if not cultural_notes_open:
        return

    panel.innerHTML = ""
    # Only rows already unlocked -- same spoiler-avoidance posture as
    # proficiency tests and bonus sections, which are also gated to
    # unlocked weeks rather than previewing content the syllabus hasn't
    # reached yet.
    visible = [
        (row, CULTURAL_NOTES_BY_SEQUENCE[row.sequence])
        for row in state.rows
        if row.sequence in CULTURAL_NOTES_BY_SEQUENCE and state.is_row_unlocked(row.sequence)
    ]
    if not visible:
        empty = document.createElement("p")
        empty.className = "cultural-note-empty"
        empty.innerText = "No cultural notes for the weeks you've unlocked yet."
        panel.appendChild(empty)
        return

    for row, note in visible:
        entry = document.createElement("div")
        entry.className = "cultural-note"
        heading = document.createElement("p")
        heading.className = "cultural-note-week"
        heading.innerText = row.label
        body = document.createElement("p")
        body.className = "cultural-note-text"
        body.innerText = note
        entry.appendChild(heading)
        entry.appendChild(body)
        panel.appendChild(entry)


# ===========================================================================
# Improvement Ideas addendum -- liaison/elision practice ("Liaison practice")
# ===========================================================================
#
# A short, fixed-length multiple-choice quiz over the hand-authored questions
# in LIAISON_DRILL_QUESTIONS above. Entirely stateless with respect to SRS
# and row-unlock caching -- same posture as the proficiency test and bonus
# sections (see their own build notes): no state.review(), no nudge, nothing
# written back to a plot. Gated to unlocked weeks only, same spoiler-avoidance
# rule cultural notes and the dashboard already use.

LIAISON_INSTRUCTION = "Pick the correct answer."
LIAISON_SUMMARY_MESSAGE = "{correct} of {total} correct."
# Its own feedback wording, not the farm's FEEDBACK dict -- "this plot is
# growing" makes no sense for a quiz that never touches a plot.
LIAISON_FEEDBACK = {
    "correct": "Yes — {answer}.",
    "incorrect": "Not quite — it was {answer}.",
}

liaison_mode = False
liaison_questions = []
liaison_index = 0
liaison_result = None
liaison_score = {"correct": 0, "total": 0}
liaison_choice_proxies = []
LIAISON_RNG = random.Random()


def _destroy_liaison_choice_proxies():
    global liaison_choice_proxies
    for proxy in liaison_choice_proxies:
        proxy.destroy()
    liaison_choice_proxies = []


def liaison_drill_available():
    return any(state.is_row_unlocked(entry["sequence"]) for entry in LIAISON_DRILL_QUESTIONS)


def build_liaison_drill(rng=None):
    rng = LIAISON_RNG if rng is None else rng
    eligible = [
        entry for entry in LIAISON_DRILL_QUESTIONS if state.is_row_unlocked(entry["sequence"])
    ]
    rng.shuffle(eligible)
    return eligible


def start_liaison_drill(event=None):
    global liaison_mode, liaison_questions, liaison_index, liaison_result, liaison_score

    liaison_questions = build_liaison_drill()
    if not liaison_questions:
        return None
    liaison_index = 0
    liaison_result = None
    liaison_score = {"correct": 0, "total": 0}
    liaison_mode = True
    render()
    return liaison_questions


def submit_liaison_answer(given):
    global liaison_result

    if liaison_index >= len(liaison_questions) or liaison_result is not None:
        return None
    entry = liaison_questions[liaison_index]
    liaison_result = given == entry["answer"]
    liaison_score["total"] += 1
    if liaison_result:
        liaison_score["correct"] += 1
    record_practice("liaison", liaison_result)
    render()
    return liaison_result


def next_liaison_question(event=None):
    global liaison_index, liaison_result

    if not liaison_mode:
        return None
    liaison_index += 1
    liaison_result = None
    render()
    return liaison_index


def close_liaison_drill(event=None):
    global liaison_mode, liaison_questions, liaison_index, liaison_result, liaison_score

    liaison_mode = False
    liaison_questions = []
    liaison_index = 0
    liaison_result = None
    liaison_score = {"correct": 0, "total": 0}
    render()


def on_toggle_liaison_drill(event=None):
    if liaison_mode:
        close_liaison_drill()
    else:
        start_liaison_drill()


def _make_liaison_choice_handler(choice):
    def handler(event=None):
        submit_liaison_answer(choice)
    return handler


# L26 -- a small sound legend for the bracketed sounds a liaison/elision
# question mentions ("[z]"). Data-driven: it lists only the symbols that
# actually appear in the current question's text, described with plain
# English comparisons, so a future question using [t] or [n] needs no code.
LIAISON_SOUND_LEGEND = {
    "z": "the 'z' sound, as in English 'zoo'",
    "t": "the 't' sound, as in English 'tea'",
    "n": "the 'n' sound, as in English 'no'",
    "ʁ": "the French 'r', made at the back of the throat",
    "p": "the 'p' sound, as in English 'pea'",
}


def liaison_legend_text(entry):
    import re  # noqa: PLC0415 -- only needed here

    text = " ".join([entry.get("prompt", ""), entry.get("explanation", ""), *entry.get("choices", [])])
    seen = []
    for symbol in re.findall(r"\[([^\]\s]{1,3})\]", text):
        if symbol in LIAISON_SOUND_LEGEND and symbol not in seen:
            seen.append(symbol)
    if not seen:
        return ""
    return "Sounds: " + "; ".join(f"[{s}] = {LIAISON_SOUND_LEGEND[s]}" for s in seen)


def render_liaison_drill():
    panel = _element("liaison-panel")
    toggle = _element("liaison-toggle-button")
    choices_box = _element("liaison-choices")

    _destroy_liaison_choice_proxies()

    toggle.disabled = not liaison_mode and not liaison_drill_available()
    toggle.innerText = "Close liaison practice" if liaison_mode else "🗣️ Liaison practice"

    if not liaison_mode:
        panel.hidden = True
        choices_box.innerHTML = ""
        return

    panel.hidden = False
    complete = liaison_index >= len(liaison_questions)
    summary = _element("liaison-summary")
    explanation = _element("liaison-explanation")

    if complete:
        choices_box.innerHTML = ""
        summary.hidden = False
        summary.innerText = LIAISON_SUMMARY_MESSAGE.format(**liaison_score)
        _element("liaison-progress").innerText = ""
        _element("liaison-context").innerText = ""
        _element("liaison-instruction").innerText = ""
        _element("liaison-prompt").innerText = ""
        _element("liaison-legend").hidden = True
        explanation.hidden = True
        _element("liaison-next-button").hidden = True
        _element("liaison-feedback").innerText = ""
        return

    summary.hidden = True
    entry = liaison_questions[liaison_index]

    _element("liaison-progress").innerText = f"{liaison_index + 1} of {len(liaison_questions)}"
    _element("liaison-context").innerText = entry["item"]
    _element("liaison-instruction").innerText = LIAISON_INSTRUCTION
    _element("liaison-prompt").innerText = entry["prompt"]
    legend = liaison_legend_text(entry)
    _element("liaison-legend").innerText = legend
    _element("liaison-legend").hidden = not legend

    answered = liaison_result is not None
    next_button = _element("liaison-next-button")

    choices_box.innerHTML = ""
    for index, choice in enumerate(entry["choices"]):
        button = document.createElement("button")
        button.id = f"liaison-choice-{index}"
        button.innerText = choice
        button.disabled = answered
        button.className = "choice"
        if answered and choice == entry["answer"]:
            button.className = "choice choice--answer"
        proxy = create_proxy(_make_liaison_choice_handler(choice))
        button.addEventListener("click", proxy)
        liaison_choice_proxies.append(proxy)
        choices_box.appendChild(button)

    next_button.hidden = not answered

    if answered:
        template = LIAISON_FEEDBACK["correct" if liaison_result else "incorrect"]
        _element("liaison-feedback").innerText = template.format(answer=entry["answer"])
        explanation.innerText = entry.get("explanation", "")
        explanation.hidden = not entry.get("explanation")
    else:
        _element("liaison-feedback").innerText = ""
        explanation.hidden = True


# ===========================================================================
# Achievements (planning/ACHIEVEMENTS-SYSTEM-DESIGN.md) -- retrofit of this
# game's own Milestone 23 slice into the cross-game pattern (per
# planning/TODO.md's "roll achievements out everywhere" checklist). SOL is
# the framework's reference integration; this game is the retrofit case
# the design doc itself calls out, since Milestone 23 shipped a game-local
# achievements slice *before* the cross-game framework existed.
# ===========================================================================
#
# Every one of this section's actual unlock conditions is unchanged from
# Milestone 23: two independent tiers, total plots automated and full
# syllabus weeks fully automated. What's reshaped is *where the catalog
# lives* (achievements.json, the cross-game single source of truth for
# label/description -- §2 -- instead of a hardcoded ACHIEVEMENT_ROW_LABELS
# dict) and *what this file exposes* (achievement_ids_earned() as a
# write-only save-state projection, an unlock toast, and a link to the
# hub-wide dashboard). Needs no new tracked state at all, same as before:
# since §3/Milestone 2 already made plot stages monotonic (a stage never
# regresses), "currently Automated" and "ever reached Automated" are the
# same count, so automated_plot_count()/fully_automated_row_count() are
# plain reads of the farm that already exists.

ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    return _read_json_asset(ACHIEVEMENTS_FILENAME, "ACHIEVEMENTS_JSON")


# Defensive, same posture as SUPPLEMENTARY_NOTES above: a missing/broken
# catalog degrades to "no achievements" rather than taking down the whole
# module import -- achievements are a layer on top of the real farm, not
# core gameplay.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError):
    ACHIEVEMENTS = []

ACHIEVEMENTS_BY_ID = {entry["id"]: entry for entry in ACHIEVEMENTS}

ACHIEVEMENT_AUTOMATED_THRESHOLDS = [25, 50, 100, 250, 500, 750]
ACHIEVEMENT_ROW_THRESHOLDS = [1, 5, 11, 23]


def automated_achievement_id(threshold):
    return f"automated_{threshold}"


def row_achievement_id(threshold):
    return f"row_{threshold}"


def automated_plot_count():
    return sum(1 for plot in state.plots if plot.stage == STAGE_AUTOMATED)


def fully_automated_row_count():
    count = 0
    for row in state.rows:
        plots = state.row_plots(row.sequence)
        if plots and all(plot.stage == STAGE_AUTOMATED for plot in plots):
            count += 1
    return count


ACHIEVEMENT_CHECKS = {
    **{
        automated_achievement_id(t): (lambda t=t: automated_plot_count() >= t)
        for t in ACHIEVEMENT_AUTOMATED_THRESHOLDS
    },
    **{
        row_achievement_id(t): (lambda t=t: fully_automated_row_count() >= t)
        for t in ACHIEVEMENT_ROW_THRESHOLDS
    },
}

# Every achievement in this game's catalog has a genuine numeric scale-up
# (a plot count or a row count against a fixed threshold), so every id gets
# a progress readout -- unlike SOL's mix of one-shot milestones and
# numeric ones (ACHIEVEMENTS-SYSTEM-DESIGN.md §3).
ACHIEVEMENT_PROGRESS = {
    **{
        automated_achievement_id(t): (lambda t=t: (automated_plot_count(), t))
        for t in ACHIEVEMENT_AUTOMATED_THRESHOLDS
    },
    **{
        row_achievement_id(t): (lambda t=t: (fully_automated_row_count(), t))
        for t in ACHIEVEMENT_ROW_THRESHOLDS
    },
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order -- the
    cross-game "achievements_earned" save field (ACHIEVEMENTS-SYSTEM-
    DESIGN.md §1). Always recomputed, never itself tracked state."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


def _tier_progress(thresholds, id_for):
    """Every crossed threshold (earned, most recent first) plus the next
    one still ahead (with a plain "x of y" progress read-out), or None for
    "next" once every threshold is already cleared. Labels now come from
    the achievements.json catalog -- the single source of truth (§2) --
    rather than being hardcoded here."""
    earned_thresholds = [t for t in thresholds if ACHIEVEMENT_CHECKS[id_for(t)]()]
    remaining_thresholds = [t for t in thresholds if not ACHIEVEMENT_CHECKS[id_for(t)]()]
    next_entry = None
    if remaining_thresholds:
        next_id = id_for(remaining_thresholds[0])
        next_entry = {
            "id": next_id,
            "label": ACHIEVEMENTS_BY_ID[next_id]["label"],
            "current": ACHIEVEMENT_PROGRESS[next_id]()[0],
            "target": remaining_thresholds[0],
        }
    return {
        "earned": [
            {"id": id_for(t), "label": ACHIEVEMENTS_BY_ID[id_for(t)]["label"]}
            for t in reversed(earned_thresholds)
        ],
        "next": next_entry,
    }


def achievements_summary():
    """Game-facing tiered view for the in-game panel -- kept as its own
    shape per ACHIEVEMENTS-SYSTEM-DESIGN.md §3's documented judgment call:
    this game's achievements are naturally tiered (unlike SOL's flat
    checklist), so its panel groups each tier into "earned so far (most
    recent first) + next target" rather than being forced into a flat
    card layout. Both tiers now read their labels from the ACHIEVEMENTS
    catalog instead of a hardcoded dict."""
    return {
        "automated": _tier_progress(ACHIEVEMENT_AUTOMATED_THRESHOLDS, automated_achievement_id),
        "rows": _tier_progress(ACHIEVEMENT_ROW_THRESHOLDS, row_achievement_id),
    }


achievements_open = False

# Tracks the earned-id set as of the last time it was checked, so a fresh
# unlock (one that wasn't in this set last time) can trigger a toast
# without re-toasting every already-earned achievement on every render.
# Session-only, same category as ACCENT_SENSITIVE -- a fresh page load or
# a save/load round-trip starts from an empty baseline rather than
# spamming toasts for achievements that were already satisfied before.
_achievement_ids_seen = set()

ACHIEVEMENT_TOAST_DURATION_MS = 4000


def _schedule_achievement_toast_hide(ms):
    """The auto-hide delay is scheduled from JS, not Python. This game's
    own no-timer wellbeing constraint (Milestone 7's
    test_nothing_in_the_game_runs_on_a_timer, a literal substring scan of
    this file's own source for the browser's clock-driven timer APIs) bans
    a real timer call from ever appearing here -- the same constraint that
    already pushed the arcade minigame family's real 1-second tick out into
    index.html's own boot script rather than into game.py or minigames.py
    (see CLAUDE.md's Milestone 27 build note). Safe to call from plain
    CPython (this file's own test harness): a missing `js.window` or
    sender function is simply a no-op, the same defensive-import pattern
    `_dispatch_report()` above already uses for its network call."""
    try:
        from js import window  # noqa: PLC0415 — Pyodide-only, deliberately lazy
    except ImportError:
        return
    scheduler = getattr(window, "scheduleAchievementToastHide", None)
    if scheduler is not None:
        scheduler(ms)


def show_achievement_toast(message):
    toast = _element("achievement-toast")
    toast.innerText = message
    toast.hidden = False
    toast.classList.add("achievement-toast--visible")
    _schedule_achievement_toast_hide(ACHIEVEMENT_TOAST_DURATION_MS)


def _story_reach_all(earned_ids):
    """W1: unlocks the story chapter for every earned achievement (and the
    opening one) via the shared story-chapters.js. Idempotent and silent: no
    story script, or a chapter id it does not know, simply does nothing.
    Never touches the save, and there is no missing-chapter callout (this
    game's no-guilt stance): unreached chapters are simply not shown."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    story = getattr(window, "NoyvjStory", None)
    if story is None:
        return
    story.reach("begin")
    for achievement_id in sorted(earned_ids):
        story.reach(achievement_id)


def _maybe_toast_new_achievements():
    """Diffs the currently-earned set against what's already been seen this
    session and toasts anything newly crossed. Called from
    render_achievements(), which already runs on every render() pass, so
    there's no need for a separate call site wired into every place a
    plot can reach Automated (the main practice panel, Review's nudge,
    etc.)."""
    global _achievement_ids_seen
    earned_ids = set(achievement_ids_earned())
    _story_reach_all(earned_ids)  # W1: also brings a loaded save's chapters back
    newly_earned_ids = earned_ids - _achievement_ids_seen
    _achievement_ids_seen = earned_ids
    if not newly_earned_ids:
        return
    newly_earned = [entry for entry in ACHIEVEMENTS if entry["id"] in newly_earned_ids]
    if len(newly_earned) == 1:
        message = f"\U0001F3C6 Achievement unlocked: {newly_earned[0]['label']}"
    else:
        labels = ", ".join(entry["label"] for entry in newly_earned)
        message = f"\U0001F3C6 {len(newly_earned)} achievements unlocked: {labels}"
    show_achievement_toast(message)


def on_toggle_achievements(event=None):
    global achievements_open
    achievements_open = not achievements_open
    render()


def _render_achievement_group(container, group):
    for entry in group["earned"]:
        line = document.createElement("p")
        line.className = "achievement-earned"
        line.innerText = "🏆 "
        label = document.createElement("span")
        label.className = "achievement-card-label"  # shared/achievement-share.js reads the name from here
        label.innerText = entry["label"]
        line.appendChild(label)
        line.dataset.achievementId = entry["id"]
        container.appendChild(line)
    if group["next"] is not None:
        line = document.createElement("p")
        line.className = "achievement-next"
        line.innerText = (
            f"Next: {group['next']['label']} ({group['next']['current']} of {group['next']['target']})"
        )
        line.dataset.achievementId = group["next"]["id"]
        container.appendChild(line)
    if not group["earned"] and group["next"] is None:
        line = document.createElement("p")
        line.className = "achievement-empty"
        line.innerText = "Nothing here yet."
        container.appendChild(line)


def render_achievements():
    _maybe_toast_new_achievements()

    panel = _element("achievements-panel")
    toggle = _element("achievements-toggle-button")
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if achievements_open
        else f"\U0001F3C6 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not achievements_open
    if not achievements_open:
        return

    panel.innerHTML = ""
    summary = achievements_summary()

    automated_heading = document.createElement("p")
    automated_heading.className = "achievement-heading"
    automated_heading.innerText = "Plots automated"
    panel.appendChild(automated_heading)
    _render_achievement_group(panel, summary["automated"])

    rows_heading = document.createElement("p")
    rows_heading.className = "achievement-heading"
    rows_heading.innerText = "Full weeks automated"
    panel.appendChild(rows_heading)
    _render_achievement_group(panel, summary["rows"])

    # A link out to the hub-wide achievements dashboard (planning/
    # ACHIEVEMENTS-SYSTEM-DESIGN.md §5, and the "roll achievements out
    # everywhere" section of planning/TODO.md). Hub-side script.js
    # registration (GAMES_WITH_ACHIEVEMENTS/GAME_DISPLAY_NAMES) is a
    # separate, shared-file change tracked outside this game's own dispatch.
    hub_link = document.createElement("a")
    hub_link.className = "achievements-hub-link"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.innerText = "View achievements across every game →"
    panel.appendChild(hub_link)

    _request_achievement_stats()


def _request_achievement_stats():
    """Z27b: asks the page's optional JS hook (window.applyAchievementStats,
    shared/achievement-stats.js) to fill in each visible achievement row's
    own "Earned by N% of players" line from the cross-player stats endpoint
    (planning/TODO.md Z1). Unlike the other 11 games' full card grid, this
    game's panel only ever shows each tier's earned entries plus its one
    "next" target -- see _render_achievement_group() above -- so most
    achievement ids never appear in the DOM at all here, which is fine:
    the shared hook only ever touches rows it can find via
    data-achievement-id. Absent hook (pytest, or a page without the shared
    script) leaves the rows exactly as rendered above -- same fails-soft
    shape as Grid's C15 window.gridCompare."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "applyAchievementStats", None)
    if hook is not None:
        hook()


# ===========================================================================
# "What's New" changelog panel (site-wide goal, planning/TODO.md, origin
# K16: "Per-game in-game changelog panel, for every game"). A quick
# highlights view, not a full duplicate of CLAUDE.md -- same loading
# contract as ACHIEVEMENTS above, reusing the shared _read_json_asset()
# helper this game already uses for the catalog/supplementary-notes files.
# Unlike ACHIEVEMENTS, this is a flat list (no wrapping key) -- see
# changelog.json itself.
# ===========================================================================
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    return _read_json_asset(CHANGELOG_FILENAME, "CHANGELOG_JSON")


# Degrades to an empty list rather than crashing this module's whole
# import -- the changelog panel is purely informational, not core to this
# game's gameplay.
try:
    CHANGELOG = json.loads(_read_changelog_json())
except (ValueError, OSError, NameError):
    CHANGELOG = []

changelog_open = False


def on_toggle_changelog(event=None):
    global changelog_open
    changelog_open = not changelog_open
    render()


def render_changelog():
    # Reuses .dashboard-panel's card and the same one-<p>-per-row idiom the
    # progress dashboard's own mastery/weakest/pattern lists already use
    # (see render_dashboard() above), rather than the two-part
    # "changelog-entry" card the rest of the hub's own K16 dispatches use --
    # internals are free once you're inside a game, and this game already
    # has its own established row idiom worth staying consistent with.
    panel = _element("changelog-panel")
    toggle = _element("changelog-toggle-button")
    toggle.innerText = "Hide What's New" if changelog_open else "📋 What's New"
    panel.hidden = not changelog_open
    if not changelog_open:
        return

    panel.innerHTML = ""
    # Newest first -- entries are authored newest-first in changelog.json
    # already, but sort defensively so a future out-of-order edit can't
    # silently invert the panel.
    for entry in sorted(CHANGELOG, key=lambda e: e["date"], reverse=True):
        line = document.createElement("p")
        line.className = "changelog-row"
        line.innerText = f"{entry['date']} — {entry['entry']}"
        panel.appendChild(line)


# ===========================================================================
# L-24: filter and sort for the farm grid
# ===========================================================================
#
# A "show" filter hides the plots that do not match (and any week left with
# nothing to show), and a "sort" re-orders the weeks and the plots inside each
# week. Both are plain DOM moves on the grid build_farm() already made: cells
# are re-appended in the new order (a real DOM append MOVES a node), so the
# tab order always matches what the eye sees. Session-only, like the review
# controls: nothing here reaches get_state(), and nothing changes any plot.
# The order is applied when a control changes, when the day moves on, when a
# save loads and at boot -- not after every answer, so a plot never slides out
# from under the cursor mid-session. The filter, being a cheap hide/show, does
# follow every repaint.
FARM_FILTERS = {
    "all": "All plots",
    "due": "Due today",
    "weeds": "In the weeds",
    "unwatered": "Never watered",
    "vocab": "Vocabulary",
    "phrase": "Phrases",
    "grammar": "Grammar",
    "phonetic": "Phonetics",
}
FARM_SORTS = {
    "syllabus": "Syllabus order",
    "weakest": "Weakest first",
    "overdue": "Most overdue first",
    "type": "By type",
}
FARM_TYPE_ORDER = ["vocab", "phrase", "grammar", "phonetic"]
farm_filter = "all"
farm_sort = "syllabus"
_farm_order_cache = None  # (sort, tuple of row sequences, tuple of per-row plot-id tuples)


def plot_matches_filter(plot, key):
    if key == "all" or key not in FARM_FILTERS:
        return True
    if key == "due":
        return is_due(plot, state.current_day)
    if key == "weeds":
        return plot.in_weeds
    if key == "unwatered":
        return plot.last_reviewed is None
    return plot.topic_type == key


def _plot_sort_key(plot, key, position):
    if key == "weakest":
        return (STAGE_RANK[plot.stage], plot.ease_factor, position)
    if key == "overdue":
        if is_due(plot, state.current_day):
            if plot.last_reviewed is not None and plot.next_due is not None:
                return (0, plot.next_due, position)
            return (1, 0, position)
        return (2, 0, position)
    if key == "type":
        kind = plot.topic_type
        return (FARM_TYPE_ORDER.index(kind) if kind in FARM_TYPE_ORDER else len(FARM_TYPE_ORDER), 0, position)
    return (0, 0, position)


def farm_row_order(key):
    """[(sequence, [plot ids in display order])] for the chosen sort."""
    rows = []
    for index, row in enumerate(state.rows):
        plots = state.row_plots(row.sequence)
        ordered = sorted(
            enumerate(plots), key=lambda pair: _plot_sort_key(pair[1], key, pair[0])
        )
        if key == "weakest":
            row_key = (dashboard_row_mastery(row.sequence), index)
        elif key == "overdue":
            row_key = (-sum(1 for p in plots if is_due(p, state.current_day) and p.last_reviewed is not None), index)
        else:
            row_key = (0, index)
        rows.append((row_key, row.sequence, [p.plot_id for _i, p in ordered]))
    rows.sort(key=lambda entry: entry[0])
    return [(sequence, ids) for _key, sequence, ids in rows]


def apply_farm_arrangement(force=False):
    """Re-order the weeks and each week's plots for the current sort."""
    global _farm_order_cache
    order = farm_row_order(farm_sort)
    signature = (farm_sort, tuple((seq, tuple(ids)) for seq, ids in order))
    if not force and signature == _farm_order_cache:
        return False
    _farm_order_cache = signature
    farm = _element("farm")
    # LM-1: in Syllabus order every week sits inside its semester's band; any other
    # sort mixes the semesters, so the weeks come out of the bands (which hide).
    bands = semester_bands()
    for band in bands:
        farm.appendChild(_element(f"semester-{band['index']}"))
    band_of = {band["course"]: band["index"] for band in bands}
    course_of = {row.sequence: row.course for row in state.rows}
    in_bands = farm_sort == "syllabus"
    for sequence, ids in order:
        home = _element(f"semester-rows-{band_of[course_of[sequence]]}") if in_bands else farm
        home.appendChild(_element(f"row-{sequence}"))
        container = _element(f"row-plots-{sequence}")
        for plot_id in ids:
            cell = plot_cells.get(plot_id)
            if cell is not None:
                container.appendChild(cell)
    return True


def set_farm_filter(key):
    global farm_filter
    farm_filter = key if key in FARM_FILTERS else "all"
    _element("farm-filter-select").value = farm_filter
    render()
    return farm_filter


def set_farm_sort(key):
    global farm_sort
    farm_sort = key if key in FARM_SORTS else "syllabus"
    _element("farm-sort-select").value = farm_sort
    apply_farm_arrangement(force=True)
    render()
    return farm_sort


def on_farm_filter_change(event=None):
    set_farm_filter(_element("farm-filter-select").value)


def on_farm_sort_change(event=None):
    set_farm_sort(_element("farm-sort-select").value)


def farm_filter_count_text():
    total = len(state.plots)
    if farm_filter == "all":
        return ""
    shown = sum(1 for p in state.plots if plot_matches_filter(p, farm_filter))
    return f"Showing {shown} of {total} plots"


def _plot_classes(plot):
    classes = ["plot", f"plot--{plot.stage}"]
    # L16 -- a non-colour cue for the topic type (border style, see style.css).
    classes.append(f"plot--type-{plot.topic_type}")
    # Weeds takes the place ordinary wilting would otherwise show for this
    # specific plot -- a known mix-up is more informative than a generic
    # "overdue" droop, so it's checked first and wilting is skipped when
    # weeds already applies.
    if plot.in_weeds:
        classes.append("plot--weeds")
    elif is_wilting(plot, state.current_day):
        classes.append("plot--wilting")
    if is_due(plot, state.current_day):
        classes.append("plot--due")
    # L-17 / L-18: the golden plot of the day and a stubborn weed.
    if is_golden(plot):
        classes.append("plot--golden")
    if is_leech(plot):
        classes.append("plot--leech")
    # L-16: a false-friend badge when the live list (Faux Amis) names this plot's French word.
    if minigames.amis_for_plot(plot) is not None:
        classes.append("plot--amis")
    if not state.is_row_unlocked(plot.sequence):
        classes.append("plot--locked")
    return " ".join(classes)


def weeds_confusions_for(plot):
    """L18 -- the specific look-alike(s) a weeds plot is likely being mixed
    up with, from the same WEED_CONFUSIONS table that put it in the weeds.
    Sorted so the note is stable; empty when the table has no entry."""
    found = set()
    for item in plot.items:
        for key in ("fr", "en"):
            text = item.get(key)
            if text:
                found |= WEED_CONFUSIONS.get(normalize_answer(str(text), fold_accents=False), set())
    return sorted(found)


def _plot_title(plot):
    parts = [f"{plot.label} — {plot.topic_title}", STAGE_LABEL[plot.stage].split(" — ")[0]]
    if plot.stage == STAGE_AUTOMATED:
        parts.append(AUTOMATED_TOOLTIP_NOTE)
        # L12 -- how long until this automated plot next wants water.
        if plot.next_due is not None and plot.next_due > state.current_day:
            days = plot.next_due - state.current_day
            parts.append(f"next review in {days} day{'s' if days != 1 else ''}")
    if plot.in_weeds:
        parts.append(WEEDS_TOOLTIP_NOTE)
        confusions = weeds_confusions_for(plot)
        if confusions:
            parts.append("Easy to mix up with: " + ", ".join(f"\u201c{c}\u201d" for c in confusions))
    if is_golden(plot):
        parts.append(f"golden plot of the day: a correct answer earns {GOLDEN_POINTS} practice points")
    if is_leech(plot):
        parts.append(
            f"stubborn weed: missed {plot.fail_run} times in a row, so a short re-teach card shows first"
        )
    amis_note = minigames.amis_plot_note(plot)
    if amis_note:
        parts.append(amis_note)
    if is_due(plot, state.current_day):
        parts.append(DUE_NOTE)
    return " · ".join(parts)


# U14: render_farm() used to rewrite five DOM properties on every plot cell on
# every render (about 20ms, the single biggest cost in this game). Each cell's
# and row's last-written values are remembered here and a property is only
# written when it actually changed; a rebuilt grid clears both caches.
_farm_cell_cache = {}
_farm_row_cache = {}


def render_farm():
    ensure_golden()
    row_shown = {}  # sequence -> how many of its plots pass the L-24 filter
    for plot in state.plots:
        cell = plot_cells.get(plot.plot_id)
        if cell is None:
            continue
        classes = _plot_classes(plot)
        icon = STAGE_ICON[plot.stage]
        title = _plot_title(plot)
        disabled = not state.is_row_unlocked(plot.sequence)
        shown = plot_matches_filter(plot, farm_filter)
        row_shown[plot.sequence] = row_shown.get(plot.sequence, 0) + (1 if shown else 0)
        values = (classes, icon, title, disabled, shown)
        if _farm_cell_cache.get(plot.plot_id) == values:
            continue
        _farm_cell_cache[plot.plot_id] = values
        cell.className = classes
        cell.innerText = icon
        cell.title = title
        cell.hidden = not shown
        # The sprite carries the meaning visually; screen readers get the same
        # sentence the tooltip does.
        cell.setAttribute("aria-label", title)
        cell.disabled = disabled

    _last_row_shown.clear()
    _last_row_shown.update(row_shown)
    for row in state.rows:
        plots = state.row_plots(row.sequence)
        grown = sum(1 for p in plots if p.stage != STAGE_SEED)
        # L20 -- separate "watered at least once" from "never watered yet"
        # (a wrong answer counts as watered but leaves the plot a seed, so
        # the grown/total number above can understate real catch-up).
        watered = sum(1 for p in plots if p.last_reviewed is not None)
        unlocked = state.is_row_unlocked(row.sequence)
        row_due = sum(1 for p in plots if is_due(p, state.current_day)) if unlocked else 0
        badge_hidden = row.sequence not in row_session_perfect_badge
        row_hidden = row_shown.get(row.sequence, 0) == 0
        row_values = (grown, len(plots), watered, unlocked, row_due, badge_hidden, row_hidden)
        if _farm_row_cache.get(row.sequence) == row_values:
            continue
        _farm_row_cache[row.sequence] = row_values
        _element(f"row-{row.sequence}").hidden = row_hidden

        _element(f"row-progress-{row.sequence}").innerText = f"{grown}/{len(plots)}"
        _element(f"row-progress-{row.sequence}").title = (
            f"{watered} of {len(plots)} plots watered at least once, {len(plots) - watered} never watered yet"
        )
        _element(f"row-lock-{row.sequence}").hidden = unlocked
        _element(f"row-{row.sequence}").className = "row" if unlocked else "row row--locked"
        _element(f"row-perfect-badge-{row.sequence}").hidden = badge_hidden

        due_element = _element(f"row-due-{row.sequence}")
        due_element.hidden = not row_due
        due_element.innerText = ROW_DUE_NOTE.format(count=row_due) if row_due else ""

        _element(f"row-proficiency-{row.sequence}").disabled = not unlocked
        _element(f"row-bonus-{row.sequence}").disabled = not unlocked

    render_semesters()


def render_status():
    due = state.due_plots()
    _element("day-display").innerText = f"Day {state.current_day + 1}"
    if not due:
        message = NOTHING_DUE_MESSAGE
    elif len(due) == 1:
        message = DUE_MESSAGE_ONE
    else:
        message = DUE_MESSAGE_MANY.format(count=len(due))
    _element("due-display").innerText = message
    _element("pace-display").innerText = PACE_NOTE

    # A tally rather than a score: how much of the farm is at each stage, with
    # no notion of how much of it "should" be further along by now.
    counts = {stage: 0 for stage in STAGE_ORDER}
    for plot in state.plots:
        counts[plot.stage] += 1
    _element("stage-summary-display").innerText = " · ".join(
        f"{STAGE_ICON[stage]} {counts[stage]}" for stage in STAGE_ORDER
    )

    # Audit note: the numerator here is scoped to available_plots() (rows
    # unlocked so far) while the denominator is len(state.plots) (all 722,
    # locked or not) -- an inconsistent scope on its face. It reads correctly
    # today only because a locked plot can never be anything but STAGE_SEED
    # during live play: open_practice() refuses to open a plot outside
    # is_row_unlocked(), which is the only path that ever advances a stage
    # (schedule_after_review()), so filtering the numerator down to
    # available_plots() can never actually exclude a non-seed plot -- the
    # count would come out identical scoped over state.plots directly.
    # That said, load_state() sets plot.stage straight from a save record
    # per plot_id, independent of that plot's row's current unlock status;
    # a save that is missing or resets an earlier row's records (an old/
    # edited/incompatible save code) while still recording a later row's
    # plot as grown could in principle reload into exactly the locked-but-
    # growing state this scope mismatch assumes can't happen -- the same
    # general class of stale-save-reload skew audited and fixed elsewhere
    # in this repo (see Aftermath's highest-awarded-run guard). Left as-is
    # rather than silently changed, since which scope is "correct" for the
    # player-facing number here isn't a confident call either way; flagging
    # for whoever next touches save compatibility for this game.
    available = state.available_plots()
    growing = sum(1 for p in available if p.stage != STAGE_SEED)
    automated = sum(1 for p in available if p.stage == STAGE_AUTOMATED)
    _element("progress-display").innerText = (
        f"{growing} of {len(state.plots)} plots growing · {automated} automated"
    )
    # L8 -- an always-visible bar for how much of the whole farm is automated.
    automated_share = automated / len(state.plots) if state.plots else 0.0
    _element("automated-bar").style.width = f"{automated_share * 100:.1f}%"
    _element("automated-meter").title = f"{automated} of {len(state.plots)} plots automated"

    render_practice_score()
    render_study_buddy()
    _element("golden-display").innerText = golden_text()
    _element("quest-display").innerText = quest_summary_text()
    _element("farm-filter-count").innerText = farm_filter_count_text()

    unlocked = sum(1 for r in state.rows if state.is_row_unlocked(r.sequence))
    _element("row-summary-display").innerText = f"{unlocked} of {len(state.rows)} rows open"

    # Combo bonus (Improvement Ideas §2): only worth a line once it's an
    # actual moment, not a running scoreboard -- a fresh session or one that
    # just broke its combo shows nothing here, matching the farm's existing
    # "calm, not a scoreboard" stance rather than a 0-in-a-row counter.
    combo_display = _element("combo-display")
    if combo_count >= 2:
        combo_display.innerText = f"{combo_count} correct in a row — nice pace."
        combo_display.hidden = False
    else:
        combo_display.innerText = ""
        combo_display.hidden = True

    water_next = _element("water-next-button")
    water_next.disabled = not due
    water_next.innerText = "Water the next plot" if due else "All watered"


def render_practice():
    panel = _element("practice-panel")
    choices_box = _element("practice-choices")
    answer_input = _element("practice-answer-input")
    submit = _element("practice-submit-button")

    # The previous batch of choice-button proxies belongs to whatever was on
    # screen before this repaint, closed panel or otherwise — destroy it here
    # so every path through this function (including the early return below)
    # retires its predecessors before anything new can replace it.
    _destroy_practice_choice_proxies()

    # L24: a static watering-can cursor over the farm while a plot is open.
    farm_el = _element("farm")
    if practice_open and current_question is not None:
        farm_el.classList.add("farm--watering")
    else:
        farm_el.classList.remove("farm--watering")

    if not practice_open or current_question is None:
        panel.hidden = True
        choices_box.innerHTML = ""
        _element("practice-report-button").hidden = True
        _element("practice-blurb").hidden = True
        _element("practice-pronunciation-note").hidden = True
        _element("practice-pronunciation-report-button").hidden = True
        _element("practice-next-button").hidden = True
        _element("practice-slip-button").hidden = True
        _element("practice-slip-note").hidden = True
        _element("practice-leech").hidden = True
        return

    panel.hidden = False
    _element("practice-context").innerText = current_question["context"]
    _element("practice-instruction").innerText = current_question["instruction"]
    _element("practice-prompt").innerText = current_question["prompt"]

    note = _element("practice-note")
    note.innerText = current_question["note"] or ""
    note.hidden = not current_question["note"]

    answered = current_result is not None

    # Optional pre-answer confidence tag. Hidden once answered -- it has
    # nothing left to weigh at that point (submit_answer() already read it).
    confidence_box = _element("practice-confidence")
    confidence_box.hidden = answered
    gender_text = gender_drill_accuracy_text() if current_question.get("variant") == V_GENDER_TAG else ""
    _element("gender-accuracy-display").innerText = gender_text
    _element("gender-accuracy-display").hidden = not gender_text
    stats_text = confidence_stats_text()
    _element("practice-confidence-stats").innerText = stats_text
    _element("practice-confidence-stats").hidden = not stats_text
    sure_button = _element("practice-confidence-sure-button")
    unsure_button = _element("practice-confidence-unsure-button")
    sure_button.className = "secondary" + (" selected" if current_confidence == "sure" else "")
    unsure_button.className = "secondary" + (" selected" if current_confidence == "unsure" else "")

    choices_box.innerHTML = ""
    if current_question["mode"] == "choice":
        answer_input.hidden = True
        submit.hidden = True
        for index, choice in enumerate(current_question["choices"]):
            button = document.createElement("button")
            button.id = f"practice-choice-{index}"
            button.innerText = choice
            button.disabled = answered
            button.className = "choice"
            if answered and choice == current_question["answer"]:
                button.className = "choice choice--answer"
            proxy = create_proxy(_make_choice_handler(choice))
            button.addEventListener("click", proxy)
            practice_choice_proxies.append(proxy)
            choices_box.appendChild(button)
    else:
        answer_input.hidden = False
        submit.hidden = False
        submit.disabled = answered

    if answered:
        template = FEEDBACK["correct" if current_result else "incorrect"]
        _element("practice-feedback").innerText = template.format(
            answer=current_question["answer"]
        )
    else:
        _element("practice-feedback").innerText = ""
    water_note = _element("practice-water-note")
    note_text = water_result_text(current_water_kind, plot_for_note=state.plots_by_id.get(current_question["plot_id"])) if (answered and current_result) else ""
    water_note.innerText = note_text
    water_note.hidden = not note_text

    # Direct user request: continuing to the next due plot used to mean
    # Close, then scroll back up to the farm-level "water next plot" button
    # -- real friction doing several plots in a row. Same visibility gating
    # as the report buttons below (answered = current_result is not None).
    _element("practice-next-button").hidden = not answered

    # §14.2.4: the report button only ever appears once a *written* answer
    # (typed, never multiple choice) has been marked wrong -- a wrong choice
    # isn't ambiguous the way a wrong typed answer can be.
    report_button = _element("practice-report-button")
    show_report = answered and current_result is False and current_question["mode"] == "typed"
    report_button.hidden = not show_report
    if show_report:
        report_button.disabled = report_sent
        report_button.innerText = REPORT_SENT_LABEL if report_sent else REPORT_BUTTON_LABEL

    # Milestone 24: independent of the above -- available for the whole
    # time a question is open, not gated by right/wrong or typed/choice,
    # since a pronunciation concern is about the catalog text itself, not
    # about how this attempt went. The note only shows for the handful of
    # items the TTS watchlist actually flags by name (see
    # PRONUNCIATION_RISK_NOTES); the report button is always available.
    pronunciation_note = _element("practice-pronunciation-note")
    pronunciation_button = _element("practice-pronunciation-report-button")
    plot = state.plots_by_id.get(current_question["plot_id"])
    risk_note = PRONUNCIATION_RISK_NOTES.get(plot.items[0]["fr"]) if plot else None
    pronunciation_note.hidden = risk_note is None
    if risk_note is not None:
        pronunciation_note.innerText = f"⚠ Known pronunciation risk: {risk_note}"
    pronunciation_button.hidden = False
    pronunciation_button.disabled = pronunciation_report_sent
    pronunciation_button.innerText = (
        PRONUNCIATION_REPORT_SENT_LABEL
        if pronunciation_report_sent
        else PRONUNCIATION_REPORT_BUTTON_LABEL
    )

    # §14.3: the failure blurb shows on *any* wrong answer, choice or typed
    # (unlike the report button above, which is written-answer-only).
    blurb_panel = _element("practice-blurb")
    show_blurb = answered and current_result is False
    blurb = build_failure_blurb(current_question) if show_blurb else None
    blurb_panel.hidden = blurb is None
    if blurb is not None:
        _element("practice-blurb-what").innerText = blurb["what_it_is"]
        _element("practice-blurb-tip").innerText = blurb["memory_tip"]
        _element("practice-blurb-why").innerText = blurb["why_it_matters"]

    # L-19: the once-a-session "that was a slip" button, and its confirmation.
    _element("practice-slip-button").hidden = not can_forgive_slip()
    slip_note_line = _element("practice-slip-note")
    slip_note_line.innerText = slip_note
    slip_note_line.hidden = not slip_note

    # L-18: a stubborn weed shows its re-teach card until it is answered.
    leech_box = _element("practice-leech")
    show_leech = (not answered) and plot is not None and is_leech(plot)
    leech_box.hidden = not show_leech
    if show_leech:
        what_line, pieces_line, hook_line = leech_reteach_lines(plot)
        _element("practice-leech-what").innerText = what_line
        _element("practice-leech-pieces").innerText = pieces_line
        _element("practice-leech-hook").innerText = hook_line
        _element("practice-leech-rest-button").innerText = f"Rest this plot for {LEECH_REST_DAYS} days"


def render():
    render_deepdive()
    render_calendar()
    render_phrasebook()
    render_farm()
    render_status()
    render_practice()
    render_review()
    render_proficiency()
    render_bonus()
    render_builder()
    render_conversation()
    render_listening()
    render_placement()
    render_cultural_notes()
    render_dashboard()
    render_liaison_drill()
    render_achievements()
    render_changelog()
    render_legend_guide()
    render_report_log()
    render_planner()
    render_accent_bars()
    render_water_options()
    render_shop()
    minigames.render()


# --- interactions ----------------------------------------------------------


def open_practice(plot_id, variant=None):
    """Water a plot: roll a fresh question for it (§5) and show the panel."""
    global current_question, current_result, current_submitted_answer, practice_open, report_sent, pronunciation_report_sent, current_confidence, deepdive_open, slip_note
    global current_water_kind

    plot = state.plots_by_id.get(plot_id)
    if plot is None or not state.is_row_unlocked(plot.sequence):
        return None
    slip_note = ""

    current_question = generate_question(
        plot, QUESTION_RNG, variant=variant, exclude=getattr(plot, "last_variant", None)
    )
    plot.last_variant = current_question["variant"]
    current_result = None
    current_submitted_answer = None
    current_confidence = None
    current_water_kind = None
    report_sent = False
    pronunciation_report_sent = False
    practice_open = True
    deepdive_open = False
    _element("practice-answer-input").value = ""
    render()
    return current_question


def set_confidence(value):
    """Optional pre-answer confidence tag ("sure"/"unsure"), toggleable --
    clicking the already-selected one clears it back to unset rather than
    forcing a choice. Never blocks answering either way."""
    global current_confidence
    if current_question is None or current_result is not None:
        return current_confidence
    current_confidence = None if current_confidence == value else value
    render()
    return current_confidence


def submit_answer(given):
    global current_result, current_submitted_answer, combo_count, _slip_snapshot, slip_note
    global current_water_kind

    if current_question is None or current_result is not None:
        return None
    typed_mode = current_question["mode"] == "typed"
    current_submitted_answer = str(given).strip() if typed_mode else given
    # §14.2: the tier is decided from the answer's own shape, only for typed
    # answers -- multiple choice is always an exact match regardless.
    tier = grading_tier(current_question["answer"]) if typed_mode else None
    plot = state.plots_by_id.get(current_question["plot_id"])
    ensure_quests()
    # L-19: what to put back if the player forgives this answer as a slip.
    slip_note = ""
    _slip_snapshot = None
    if plot is not None:
        _slip_snapshot = {
            "plot_id": plot.plot_id,
            "record": _plot_record(plot),
            "combo": combo_count,
            "confidence": current_confidence,
            "pattern": None,
            "spoiled": plot.sequence in row_session_spoiled,
            "row_correct": set(row_session_correct.get(plot.sequence, ())),
            "quest": {
                "day": quest_state["day"],
                "progress": dict(quest_state["progress"]),
                "done": list(quest_state["done"]),
            },
        }
    prior_fail_run = plot.fail_run if plot is not None else 0
    current_result = check_answer(
        current_question, given, tier=tier, accent_sensitive=ACCENT_SENSITIVE
    )
    combo_count = combo_count + 1 if current_result else 0
    if current_confidence in confidence_tally:
        confidence_tally[current_confidence][1] += 1
        confidence_tally[current_confidence][0] += 1 if current_result else 0
    if current_question.get("variant") == V_GENDER_TAG:
        record_practice("gender", current_result)  # also counts the study day
    else:
        note_study_answer()
    _quest_note("water")
    if plot is not None and plot.topic_type == "grammar":
        _quest_note("grammar")
    _quest_note("combo", combo_count, absolute=True)
    if plot is not None:
        if current_result:
            plot.in_weeds = False
            plot.fail_run = 0
        else:
            plot.fail_run = min(plot.fail_run + 1, LEECH_FAIL_RUN_LIMIT)
            if typed_mode and is_weed_confusion(current_question["answer"], given):
                plot.in_weeds = True
        _track_row_session_answer(plot, current_result)
        _claim_golden(plot.plot_id, current_result)
        _note_highlights(plot, current_result, prior_fail_run)
    if not current_result and typed_mode:
        pattern = classify_wrong_typed_answer(current_question, given, tier)
        record_error_pattern(pattern)
        if _slip_snapshot is not None:
            _slip_snapshot["pattern"] = pattern
    if current_result:
        # Watering rule: the first correct answer for a plot each day is a
        # full watering, a later one the same day only a nudge.
        current_water_kind = water_plot(plot, combo=combo_count, confidence=current_confidence)
    else:
        current_water_kind = None
        state.review(
            current_question["plot_id"],
            current_result,
            combo=combo_count,
            confidence=current_confidence,
        )
    render()
    return current_result


def close_practice(event=None):
    global current_question, current_result, current_submitted_answer, practice_open, report_sent, pronunciation_report_sent, current_confidence, deepdive_open
    global current_water_kind

    current_question = None
    current_water_kind = None
    current_result = None
    current_submitted_answer = None
    current_confidence = None
    report_sent = False
    pronunciation_report_sent = False
    practice_open = False
    deepdive_open = False
    render()


def _typed_wrong_report_payload(question, submitted_answer):
    """Shared §14.2.4 payload shape behind every mode's own "I think this
    should count" report button. Originally just `_report_payload()`'s own
    body; factored out at Milestone 26 once Review, Proficiency, and Bonus's
    tile/sentence tasks all needed the identical shape for a plot-backed
    `question` dict (one produced by `generate_question()`, carrying its own
    "plot_id"/"topic_type"/"answer"). Bonus's hand-authored sentences aren't
    plot-backed, so Bonus builds its payload directly instead of calling
    this — see `_bonus_tile_report_payload()`/`_bonus_sentence_report_payload()`.
    The caller is responsible for the "answered, wrong, typed" gate; that
    part differs in variable name per mode, not in meaning."""
    accepted = _lookup_accepted(question) or []
    marked_correct_answer = [question["answer"]]
    for alt in accepted:
        if alt not in marked_correct_answer:
            marked_correct_answer.append(alt)
    return {
        "game_id": REPORT_GAME_ID,
        "item_id": question["plot_id"],
        "submitted_answer": submitted_answer or "",
        "marked_correct_answer": marked_correct_answer,
        "topic_type": question["topic_type"],
    }


def _plot_pronunciation_report_payload(question):
    """Shared Milestone 24 payload shape for a plot-backed question — the
    main practice panel, Review, and Proficiency all generate their
    questions from a real plot via `generate_question()`. Bonus's
    hand-authored sentences aren't plot-backed, so Bonus builds its own
    version instead of calling this one (see
    `_bonus_tile_pronunciation_report_payload()`/
    `_bonus_sentence_pronunciation_report_payload()`)."""
    if question is None:
        return None
    plot = state.plots_by_id.get(question.get("plot_id"))
    if plot is None:
        return None
    return {
        "game_id": REPORT_GAME_ID,
        "item_id": question["plot_id"],
        "submitted_answer": PRONUNCIATION_REPORT_MARKER,
        "marked_correct_answer": [plot.items[0]["fr"]],
        "topic_type": PRONUNCIATION_REPORT_TOPIC_TYPE,
    }


def _report_payload():
    """The §14.2.4 payload for the currently-open question, or None if
    there's nothing to report (no question, not yet answered, or answered
    correctly). The timestamp is deliberately not built here — the backend's
    own `created_at` covers it, keeping this file free of the wall-clock
    dependency the Milestone 7 audit forbids (see CLAUDE.md's Milestone 9
    build note)."""
    if current_question is None or current_result is not False:
        return None
    if current_question["mode"] != "typed":
        return None
    return _typed_wrong_report_payload(current_question, current_submitted_answer)


def _notify_visual_style_context(context):
    """L2 (planning/TODO.md): tells visual-style.js which per-context
    preset (farm/review) should be live, whenever that context actually
    changes. Same Python-computes/JS-owns-the-one-external-thing split as
    _dispatch_report() below -- a no-op under the pytest harness (no
    js.window) or a page without visual-style.js loaded."""
    try:
        from js import window  # noqa: PLC0415 — Pyodide-only, deliberately lazy
    except ImportError:
        return
    api = getattr(window, "ChampDeMotsVisualStyle", None)
    if api is not None:
        api.setContext(context)


def _dispatch_report(payload):
    """Hands the payload to a JS-side sender, same split as the shared save
    widget: Python computes state, JS owns the actual fetch() call (see
    index.html). Safe to call from plain CPython (this file's own test
    harness, or any future non-browser context) since a missing `js.window`
    or sender function is simply a no-op rather than a crash — the same
    defensive-import pattern `_read_catalog_json()` already uses."""
    try:
        from js import window  # noqa: PLC0415 — Pyodide-only, deliberately lazy
    except ImportError:
        return
    sender = getattr(window, "submitAnswerReport", None)
    if sender is not None:
        sender(json.dumps(payload))


def submit_report(event=None):
    """Send the currently-open question's report, once. A second click (or
    a call with nothing to report) is a no-op — there is nothing new to say."""
    global report_sent

    if report_sent:
        return None
    payload = _report_payload()
    if payload is None:
        return None
    report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _pronunciation_report_payload():
    """The Milestone 24 payload for the currently-open question's own item,
    or None if there's no question open. Unlike `_report_payload()`, this
    doesn't care whether the answer was right or wrong, typed or chosen --
    a pronunciation concern is about the catalog text itself, not about how
    this particular attempt went."""
    return _plot_pronunciation_report_payload(current_question)


def submit_pronunciation_report(event=None):
    """Send a pronunciation-concern report for the currently-open question's
    item, once. Reuses `_dispatch_report()` unchanged -- same endpoint, same
    payload shape, just a different `topic_type` for a human triaging the
    queue to filter on."""
    global pronunciation_report_sent

    if pronunciation_report_sent:
        return None
    payload = _pronunciation_report_payload()
    if payload is None:
        return None
    pronunciation_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def on_submit_typed(event=None):
    submit_answer(_element("practice-answer-input").value)


def on_answer_keydown(event=None):
    if event is not None and getattr(event, "key", None) == "Enter":
        event.preventDefault()
        on_submit_typed()


def on_water_next(event=None):
    plot = state.next_due_plot()
    if plot is not None:
        open_practice(plot.plot_id)


def on_next_practice_plot(event=None):
    """The practice panel's own "Next plot" button, added on direct user
    request so watering several plots in a row doesn't mean Close, then
    scroll back up to the farm-level "water next plot" button each time.
    Reuses on_water_next()'s exact plot-selection logic (state.next_due_plot())
    rather than re-deriving it -- the only new behaviour is the fallback:
    on_water_next() simply does nothing when there's no next plot, which
    would leave this button visible over a stale answered question with a
    click that does nothing, so this closes the panel instead."""
    plot = state.next_due_plot()
    if plot is None:
        close_practice()
        return
    open_practice(plot.plot_id)


def on_next_day(event=None):
    state.advance_day()
    apply_farm_arrangement()
    render()


# ===========================================================================
# Milestone 11 — the Review tab (design doc §14.4)
# ===========================================================================
#
# Two opt-in cross-section modes, reusing Milestone 3's own generator rather
# than inventing a second one: Random Word Review samples vocab/phrase plots
# from any unlocked week, Grammar Review the same but grammar-only and
# biased toward fill-in-the-blank/conjugation prompts. Neither ever grows a
# plot's stage or touches row-unlock state — only the daily watering loop
# does that — so Review can't be used to route around §7's pacing gate. A
# correct answer still nudges that plot's interval a little further out
# rather than being untracked entirely (§14.4's own wording).

DEFAULT_REVIEW_COUNT = 10
MIN_REVIEW_COUNT = 1
MAX_REVIEW_COUNT = 25
REVIEW_NUDGE_DAYS = 1

GRAMMAR_REVIEW_PREFERRED_VARIANTS = (V_BLANK_WORD, V_CONJUGATION_SWAP, V_BLANK_ENDING)

# L17 -- the mixed review marathon: a long session across the whole farm
# (every topic type, any row), pulling plots that are due. Plots that have
# been watered before come first, most overdue at the top; plots that were
# never watered fill any remaining slots, so a mature farm gets a genuine
# catch-up session and a brand-new farm still gets something to do.
MARATHON_MODE = "marathon"
MARATHON_COUNT = 40
MARATHON_EMPTY_MESSAGE = (
    "Nothing is due for a marathon right now — come back once more plots are ready "
    "for water, or use a Random Word or Grammar Review."
)


def marathon_candidates(farm=None, day=None):
    farm = state if farm is None else farm
    day = farm.current_day if day is None else day
    due = [p for p in farm.plots if is_due(p, day)]
    watered = sorted((p for p in due if p.last_reviewed is not None), key=lambda p: p.next_due)
    never = [p for p in due if p.last_reviewed is None]
    return (watered + never)[:MARATHON_COUNT]


# L29 -- "quick water": the lightest possible session, ONE question on the
# single most overdue plot, for a very short study break. It is an ordinary
# review under the hood (a correct answer waters the plot exactly as any Review
# does), and every answer also lands in the practice ledger as "quick", so it
# always visibly counts toward the headline practice score and the study streak.
QUICK_WATER_MODE = "quick"
QUICK_WATER_EMPTY_MESSAGE = (
    "Nothing is due for a quick water right now. Come back once a plot is ready "
    "for water, or use a Random Word or Grammar Review."
)


# L3: weak-spot drill -- a session built only from what the game already
# flags as shaky: plots sitting in the weeds (known mix-ups the error-pattern
# digest classifies) and the touched plots of the dashboard's weakest topics.
WEAK_SPOT_MODE = "weakspots"
WEAK_SPOT_SESSION_MAX = 20
WEAK_SPOT_TOPIC_COUNT = 5
WEAK_SPOT_EMPTY_MESSAGE = (
    "Nothing is flagged as a weak spot yet. Mix-ups and low-growth topics show up "
    "here once you have practised a little."
)


def weak_spot_candidates(farm=None):
    """Weeds first (the known mix-ups), then the lowest-ease touched plots of
    the weakest topics that are not already Automated. At most
    WEAK_SPOT_SESSION_MAX, no duplicates."""
    farm = state if farm is None else farm
    chosen, seen = [], set()
    for plot in farm.plots:
        if plot.in_weeds and plot.plot_id not in seen:
            chosen.append(plot)
            seen.add(plot.plot_id)
    for entry in dashboard_weakest_topics(WEAK_SPOT_TOPIC_COUNT):
        record = farm.topic_records[farm.topic_pos[entry["topic_id"]]]
        shaky = [
            p for p in _topic_plots(record["topic"])
            if p.last_reviewed is not None and p.stage != STAGE_AUTOMATED and p.plot_id not in seen
        ]
        shaky.sort(key=lambda p: (p.ease_factor, STAGE_RANK[p.stage]))
        for plot in shaky:
            chosen.append(plot)
            seen.add(plot.plot_id)
    return chosen[:WEAK_SPOT_SESSION_MAX]


def on_start_weak_spot_review(event=None):
    start_review(WEAK_SPOT_MODE)


# L25: exam cram -- a dense session over a chosen range of weeks (say, the
# chapters an exam covers), weakest material first, whatever its schedule.
CRAM_MODE = "cram"
CRAM_SESSION_MAX = 60


def cram_range(first, last):
    """(low, high) week sequence numbers, in order, clamped to the farm."""
    sequences = [row.sequence for row in state.rows]
    low_bound, high_bound = min(sequences), max(sequences)
    try:
        a, b = int(first), int(last)
    except (TypeError, ValueError):
        a, b = low_bound, high_bound
    a, b = max(low_bound, min(high_bound, a)), max(low_bound, min(high_bound, b))
    return (a, b) if a <= b else (b, a)


def cram_candidates(first, last, farm=None):
    """Every plot in weeks first..last, weakest (lowest stage, lowest ease)
    first, capped at CRAM_SESSION_MAX, then interleaved by stage so the
    session doesn't run as one blocked stretch of a single stage."""
    farm = state if farm is None else farm
    low, high = cram_range(first, last)
    pool = [p for p in farm.plots if low <= p.sequence <= high]
    # Shuffle first so the stable sort below breaks ties at random: on a fresh
    # farm everything is a Seed at default ease, and a plot-id tie-break would
    # fill the whole cap from the earliest weeks of the range.
    REVIEW_RNG.shuffle(pool)
    pool.sort(key=lambda p: (STAGE_RANK[p.stage], p.ease_factor))
    return _interleave_by_stage(pool[:CRAM_SESSION_MAX], REVIEW_RNG)


def _populate_cram_selects():
    for select_id, default_last in (("review-cram-from-select", False), ("review-cram-to-select", True)):
        select = _element(select_id)
        select.innerHTML = ""
        rows = state.rows
        for row in rows:
            option = document.createElement("option")
            option.value = str(row.sequence)
            title = f": {row.chapter_title}" if row.chapter_title else ""
            option.innerText = f"Week {row.sequence}{title}"
            select.appendChild(option)
        select.value = str(rows[-1].sequence if default_last else rows[0].sequence)


def on_start_cram_review(event=None):
    start_review(CRAM_MODE)


REVIEW_SUMMARY_MESSAGE = "Review complete — {correct}/{total} correct."
REVIEW_EMPTY_MESSAGE = (
    "Nothing matches those filters yet — try a lower minimum stage, "
    "or check back once more plots have grown."
)


def review_candidates(topic_types, min_stage=STAGE_SEED, farm=None):
    """Every plot eligible for a Review session: the right `topic_type`, in
    an unlocked row (locked rows are off-limits to Review exactly as they
    are to the farm itself), at or above the minimum growth stage."""
    farm = state if farm is None else farm
    threshold = STAGE_RANK[min_stage]
    return [
        p
        for p in farm.plots
        if p.topic_type in topic_types
        and farm.is_row_unlocked(p.sequence)
        and STAGE_RANK[p.stage] >= threshold
    ]


def _interleave_by_stage(candidates, rng):
    """Improvement Ideas §3: deliberate interleaving, not a default newest-
    first (or, here, a plain shuffle that could still cluster by chance) --
    review sessions should mix old (well-established) and new (recently
    planted) material throughout, since interleaved practice beats blocked
    practice for retention. Groups candidates by growth stage, shuffles
    within each stage bucket, then round-robins across buckets so the
    resulting order alternates stage-to-stage rather than leaving the mix
    to chance. Once the game has many more mature plots than fresh ones (the
    common case later in a session), a plain random sample would still be
    dominated by whichever stage has the most candidates; round-robining
    guarantees every present stage gets an early turn instead."""
    buckets = {stage: [] for stage in STAGE_ORDER}
    for plot in candidates:
        buckets[plot.stage].append(plot)
    for bucket in buckets.values():
        rng.shuffle(bucket)
    present = [stage for stage in STAGE_ORDER if buckets[stage]]
    interleaved = []
    cursors = {stage: 0 for stage in present}
    while True:
        progressed = False
        for stage in present:
            i = cursors[stage]
            if i < len(buckets[stage]):
                interleaved.append(buckets[stage][i])
                cursors[stage] = i + 1
                progressed = True
        if not progressed:
            break
    return interleaved


def nudge_review_correct(plot, day):
    """A nudge is the small, second kind of credit a correct answer can give:
    it pushes the interval a little further out and records that the plot was
    seen today (so a save doesn't silently drop the nudge -- see get_state()'s
    "touched" rule), but never touches `correct_streak`, `ease_factor` or
    `stage`. See water_plot() for when an answer is a watering and when it is
    only a nudge."""
    plot.interval_days = max(1, plot.interval_days) + REVIEW_NUDGE_DAYS
    plot.next_due = day + plot.interval_days
    plot.last_reviewed = day


# ---------------------------------------------------------------------------
# Watering versus nudging (the single rule behind every plot-linked activity)
# ---------------------------------------------------------------------------
# WATER = a full SRS review of the plot: the interval ladder moves up one rung
# (1 day, 3 days, then interval x ease), the ease factor and the correct
# streak go up, and the plot may climb a visible growth stage.
# NUDGE = only the next review date moves a little (one day later): no growth
# stage, no streak, no ease change.
# Until 2026-10-08 only watering a plot on the farm (and the first correct
# Review or proficiency answer for a plot each day) was a watering; the arcade
# games could only nudge a plot that had already been watered. Now the FIRST
# correct answer for a plot on an in-game day, from ANY plot-linked activity
# (the farm, Review and every review-style mode, the proficiency tests and
# every arcade minigame), is a real watering, so a never-watered plot can be
# watered by a game and nothing is locked behind "Water the next plot". A later
# correct answer for the same plot the same day is a nudge (at most one nudge
# per plot per day, so a fast game cannot pile up days). A wrong answer in any
# of these activities changes nothing, and a stage never goes down. (Watering a
# plot on the farm keeps its older rule that a wrong answer there reschedules
# the plot for tomorrow, as section 6 of the design doc always said.)
WATER_FULL = "full"
WATER_NUDGE = "nudge"

# Plots watered / nudged on the current in-game day, by any activity. Session
# state only (it is recomputed from nothing after a reload, which is harmless:
# the saved `last_watered` day is what actually stops a double watering).
water_today = {"day": -1, "watered": set(), "nudged": set()}


def _water_today_tally():
    if water_today["day"] != state.current_day:
        water_today["day"] = state.current_day
        water_today["watered"] = set()
        water_today["nudged"] = set()
    return water_today


def water_today_text():
    tally = _water_today_tally()
    watered, nudged = len(tally["watered"]), len(tally["nudged"])
    if not watered and not nudged:
        return "Nothing watered yet today."
    parts = []
    if watered:
        parts.append(f"watered {watered} plot{'s' if watered != 1 else ''}")
    if nudged:
        parts.append(f"nudged {nudged}")
    return "Today: " + ", ".join(parts) + "."


def water_result_text(kind, plot_for_note=None):
    """One plain sentence saying what a correct answer just did to its plot."""
    if kind == WATER_FULL:
        suffix = f" Stage: {plot_for_note.stage.capitalize()}." if plot_for_note is not None else ""
        coin = f" +{COINS_PER_WATERING} coin."
        return "Watered: this plot's schedule and growth were updated." + suffix + coin
    if kind == WATER_NUDGE:
        return "Nudged: this plot was already watered today, so its next review just moved a day later."
    return "Already watered and nudged today, so nothing more changes for this plot."


# ---------------------------------------------------------------------------
# Farm shop: coins and plot skins (TODO L-1, the part the owner said yes to on
# 2026-10-08: coins earned from watering that unlock cosmetic skins)
# ---------------------------------------------------------------------------
# One coin source, spelled out in the shop panel: a FULL watering (the first
# correct answer for a plot each in-game day, from any plot-linked activity).
# A nudge, a wrong answer and every hand-written activity earn nothing, so the
# coin counter is exactly "plots watered, ever". Coins never touch the
# scheduler, and a skin only changes how the plot cells are framed: the stage
# sprite, its colour and every state cue (due, weeds, golden, stubborn) stay
# as they were. Saved as "coins" only once something has been earned.
COINS_PER_WATERING = 1
PLOT_SKINS = (
    ("clay", "Terracotta pots", 15, "Round clay pots around every plot."),
    ("stone", "Stone tiles", 30, "Square slabs of grey stone."),
    ("crate", "Wooden crates", 45, "Brown wooden frames."),
    ("lantern", "Lantern glow", 60, "A warm, lamp-lit edge."),
    ("hedge", "Berry hedge", 80, "A purple hedge border."),
    ("gilt", "Gilded frames", 120, "Gold frames with a pale inner ring."),
)
SKIN_IDS = {skin[0] for skin in PLOT_SKINS}
coins_state = {"earned": 0, "spent": 0, "owned": [], "equipped": ""}
shop_open = False
shop_proxies = []
COIN_SOURCE_TEXT = (
    "Where coins come from: one coin for every full watering, which is the first correct answer for a plot "
    "each in-game day (watering it on the farm, Review, a proficiency test or any minigame). Nudges, wrong "
    "answers and the hand-written activities earn nothing. Coins never change how a plot is scheduled, and "
    "skins are cosmetic only: they frame the plots differently and nothing else."
)


def coin_balance():
    return max(0, coins_state["earned"] - coins_state["spent"])


def coins_text():
    balance = coin_balance()
    return f"🪙 {balance} coin{'s' if balance != 1 else ''}"


def coins_earned_today():
    return len(_water_today_tally()["watered"]) * COINS_PER_WATERING


def skin_info(skin_id):
    for skin in PLOT_SKINS:
        if skin[0] == skin_id:
            return skin
    return None


def earn_coins(amount=COINS_PER_WATERING):
    coins_state["earned"] += int(amount)


def buy_skin(skin_id):
    """"bought", "owned", "poor" (not enough coins) or "unknown"."""
    skin = skin_info(skin_id)
    if skin is None:
        return "unknown"
    if skin_id in coins_state["owned"]:
        return "owned"
    if coin_balance() < skin[2]:
        return "poor"
    coins_state["spent"] += skin[2]
    coins_state["owned"].append(skin_id)
    coins_state["equipped"] = skin_id
    return "bought"


def equip_skin(skin_id):
    """Use an owned skin, or "" for the plain plots. False when not owned."""
    if skin_id and skin_id not in coins_state["owned"]:
        return False
    coins_state["equipped"] = skin_id
    return True


def apply_skin():
    _element("farm").setAttribute("data-skin", coins_state["equipped"] or "none")


def _validated_coins(raw):
    """A saved "coins" record, or a blank one for anything that is not valid:
    non-negative whole numbers, only known skins, spent never above earned,
    the equipped skin one that is owned."""
    blank = {"earned": 0, "spent": 0, "owned": [], "equipped": ""}
    if not isinstance(raw, dict):
        return blank

    def whole(value):
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0

    earned = whole(raw.get("earned"))
    spent = min(whole(raw.get("spent")), earned)
    owned = []
    for skin_id in raw.get("owned") if isinstance(raw.get("owned"), list) else []:
        if isinstance(skin_id, str) and skin_id in SKIN_IDS and skin_id not in owned:
            owned.append(skin_id)
    equipped = raw.get("equipped")
    if not isinstance(equipped, str) or equipped not in owned:
        equipped = ""
    return {"earned": earned, "spent": spent, "owned": owned, "equipped": equipped}


def _destroy_shop_proxies():
    for proxy in shop_proxies:
        proxy.destroy()
    shop_proxies.clear()


def on_toggle_shop(event=None):
    global shop_open
    shop_open = not shop_open
    render()


def _make_shop_handler(action, skin_id):
    def handler(event=None):
        if action == "buy":
            buy_skin(skin_id)
        else:
            equip_skin(skin_id)
        apply_skin()
        render()
    return handler


def _shop_row(name, note, button_text, disabled, action, skin_id, button_id):
    line = document.createElement("div")
    line.className = "water-option"
    text = document.createElement("div")
    text.className = "water-option-text dashboard-practice-row"
    title = document.createElement("strong")
    title.innerText = name
    detail = document.createElement("span")
    detail.className = "water-option-count dashboard-practice-row"
    detail.innerText = note
    text.appendChild(title)
    text.appendChild(detail)
    button = document.createElement("button")
    button.id = button_id
    button.className = "secondary"
    button.innerText = button_text
    button.disabled = disabled
    proxy = create_proxy(_make_shop_handler(action, skin_id))
    button.addEventListener("click", proxy)
    shop_proxies.append(proxy)
    line.appendChild(text)
    line.appendChild(button)
    return line


def render_shop():
    toggle = _element("shop-toggle-button")
    panel = _element("shop-panel")
    toggle.innerText = "Close farm shop" if shop_open else "🪙 Farm shop"
    _element("coins-display").innerText = coins_text()
    _destroy_shop_proxies()
    apply_skin()
    if not shop_open:
        panel.hidden = True
        return
    panel.hidden = False
    today = coins_earned_today()
    _element("shop-coins-line").innerText = (
        f"You have {coin_balance()} coin{'s' if coin_balance() != 1 else ''} "
        f"({coins_state['earned']} earned in all, {coins_state['spent']} spent). "
        f"Earned today: {today}."
    )
    _element("shop-source-line").innerText = COIN_SOURCE_TEXT
    box = _element("shop-list")
    box.innerHTML = ""
    plain_in_use = not coins_state["equipped"]
    box.appendChild(_shop_row(
        "Plain plots", "The farm's own look.",
        "In use" if plain_in_use else "Use", plain_in_use, "equip", "", "shop-use-none-button",
    ))
    for skin_id, name, price, note in PLOT_SKINS:
        if skin_id in coins_state["owned"]:
            in_use = coins_state["equipped"] == skin_id
            box.appendChild(_shop_row(
                name, f"{note} Owned.", "In use" if in_use else "Use", in_use, "equip", skin_id,
                f"shop-use-{skin_id}-button",
            ))
        else:
            affordable = coin_balance() >= price
            need = "" if affordable else f" {price - coin_balance()} more coins needed."
            box.appendChild(_shop_row(
                name, f"{note} {price} coins.{need}", f"Buy for {price}", not affordable, "buy", skin_id,
                f"shop-buy-{skin_id}-button",
            ))
    owned = len(coins_state["owned"])
    _element("shop-progress-line").innerText = f"Skins collected: {owned} of {len(PLOT_SKINS)}."


def can_water_now(plot):
    """True while the plot has not had its full watering on the current day."""
    return plot.last_watered != state.current_day


def water_plot(plot, combo=0, confidence=None):
    """A CORRECT answer on a real plot, from any plot-linked activity.
    Returns WATER_FULL for the day's first one, WATER_NUDGE for a later one
    (once per plot per day), None when the plot has already been watered and
    nudged today (nothing more to add). `combo` and `confidence` only matter
    for the farm's own practice panel and feed the same scheduler arguments
    they always did."""
    if plot is None:
        return None
    day = state.current_day
    tally = _water_today_tally()
    plot.in_weeds = False
    plot.fail_run = 0
    if plot.last_watered != day:
        state.review(plot.plot_id, True, combo=combo, confidence=confidence)
        plot.last_watered = day
        plot.nudged_day = None
        tally["watered"].add(plot.plot_id)
        earn_coins()
        return WATER_FULL
    if plot.nudged_day != day:
        nudge_review_correct(plot, day)
        plot.nudged_day = day
        tally["nudged"].add(plot.plot_id)
        return WATER_NUDGE
    return None


def water_from_review(plot):
    """Kept for the Review code and its tests: True when the answer was the
    day's full watering, False when it was only a nudge (or nothing)."""
    return water_plot(plot) == WATER_FULL


# ---------------------------------------------------------------------------
# Which activities grow plots
# ---------------------------------------------------------------------------
# Every question screen says, in a small text marker, whether it grows plots
# and how, and every activity that credits plots says what it credited at the
# end of a session ("watered N plots, nudged M"). A game score never grows a
# plot by itself: crediting goes through water_plot() only, a plot's stage
# never goes down, and a wrong answer changes nothing.
_RULE_TIP = (
    "The first correct answer for a plot each in-game day waters it fully: its interval, ease, "
    "streak and growth stage all update, exactly like watering it on the farm. Later correct "
    "answers for the same plot that day only nudge its next review a day later. A wrong answer "
    "changes nothing, and a stage never goes down."
)
_WATERS = ("review", "Grows plots: waters, then nudges")
GROWTH_INFO = {
    "practice": ("full", "Grows plots: waters, then nudges", _RULE_TIP),
    "review": (_WATERS[0], _WATERS[1], _RULE_TIP),
    "proficiency": (
        _WATERS[0],
        _WATERS[1],
        "The test asks about real plots, so it counts like Review. " + _RULE_TIP,
    ),
    "placement": (
        "apply",
        "Grows plots only if you apply the result",
        "Answering changes no plot. If you press Apply, plots in the weeks you passed that were never watered become Sprouts (never higher, and nothing is lowered).",
    ),
    "blitz": (
        _WATERS[0],
        _WATERS[1],
        "Each question is about one real plot from weeks 1-11; the line under the question names it. " + _RULE_TIP,
    ),
    "racer": (
        _WATERS[0],
        _WATERS[1],
        "Each question is about one real grammar plot from weeks 12-15; the line under the question names it. " + _RULE_TIP,
    ),
    "sprint": (
        _WATERS[0],
        _WATERS[1],
        "Each question is about one real passé composé plot (weeks 21-23); the line under the question names it. " + _RULE_TIP,
    ),
    "boutique": (
        _WATERS[0],
        _WATERS[1],
        "A correct sale waters the plots for the garment and the colour you picked. " + _RULE_TIP,
    ),
    "cafe": (
        _WATERS[0],
        _WATERS[1],
        "A correct order waters the plot for that dish (and the passé composé plot in a twist round). " + _RULE_TIP,
    ),
    "pairs": (
        _WATERS[0],
        _WATERS[1],
        "Every correct pair waters the plot behind that word or phrase (weeks 12-23). " + _RULE_TIP,
    ),
    "gaps": (
        _WATERS[0],
        _WATERS[1],
        "Each gap is about one real grammar plot (weeks 1-11 and 16-20); the line under it names the plot. " + _RULE_TIP,
    ),
    "listenpick": (
        _WATERS[0],
        _WATERS[1],
        "Each sound is one real vocabulary, phrase or pronunciation plot; the line under the question names it. " + _RULE_TIP,
    ),
    "wordorder": (
        _WATERS[0],
        _WATERS[1],
        "Each sentence is an example from one real grammar plot; a correct order waters that plot. " + _RULE_TIP,
    ),
    "amis": (
        "none",
        "Does not grow plots",
        "The words come from a live list of false friends, not from your farm, so there is no plot to grow. Your answers still count toward your practice score. Plots whose French word is on the list carry a small false-friend badge on the farm.",
    ),
    "bonus": (
        "none",
        "Does not grow plots",
        "These sentences are hand-written, so they are not plots on the farm and there is nothing to grow. Your answers still count toward your practice score.",
    ),
    "builder": (
        "none",
        "Does not grow plots",
        "These sentences are hand-written, so they are not plots on the farm and there is nothing to grow. Your answers still count toward your practice score.",
    ),
    "conversation": (
        "none",
        "Does not grow plots",
        "These dialogue lines are hand-written, so they are not plots on the farm and there is nothing to grow. Your answers still count toward your practice score.",
    ),
    "listening": (
        "none",
        "Does not grow plots",
        "These sentences are hand-written, so they are not plots on the farm and there is nothing to grow. Your answers still count toward your practice score.",
    ),
    "liaison": (
        "none",
        "Does not grow plots",
        "These sound-rule questions are hand-written and are not tied to any plot, so there is nothing to grow. Your answers still count toward your practice score.",
    ),
}
GROWTH_SURFACES = (
    "review", "proficiency", "blitz", "racer", "boutique", "cafe", "sprint",
    "pairs", "gaps", "listenpick", "wordorder",
)
growth_credit = {surface: {"full": 0, "nudge": 0} for surface in GROWTH_SURFACES}
_credit_seen = {surface: {} for surface in GROWTH_SURFACES}


def growth_marker(key):
    """(kind, text, tooltip) for an activity's marker."""
    return GROWTH_INFO[key]


def render_growth_markers():
    for key, (kind, text, tip) in GROWTH_INFO.items():
        element = _element(f"growth-marker-{key}")
        element.innerText = text
        element.title = tip
        element.setAttribute("aria-label", f"{text}. {tip}")
        element.setAttribute("data-growth", kind)


def reset_growth_credit(surface):
    if surface in growth_credit:
        growth_credit[surface] = {"full": 0, "nudge": 0}
        _credit_seen[surface] = {}


def _note_credit(surface, plot, kind):
    """Count a plot once per session: 'watered N plots, nudged M' are distinct
    plots, not answers."""
    if surface not in growth_credit or kind not in growth_credit[surface]:
        return
    seen = _credit_seen[surface]
    if plot.plot_id in seen:
        return
    seen[plot.plot_id] = kind
    growth_credit[surface][kind] += 1


def credit_correct(plot, surface):
    """A correct answer on a real plot in a review-style session, a proficiency
    test or an arcade game: water it (or nudge it), and remember which for the
    end-of-session line. Returns WATER_FULL, WATER_NUDGE or None."""
    kind = water_plot(plot)
    if kind is not None:
        _note_credit(surface, plot, kind)
    return kind


def credit_review_plot(plot, surface):
    """A correct answer on a real plot in Review or a proficiency test."""
    return credit_correct(plot, surface)


def credit_game_plot(plot, surface):
    """An arcade game's correct answer on a real plot (it waters, or nudges)."""
    return credit_correct(plot, surface)


def credit_game_plot_id(plot_id, surface):
    return credit_game_plot(state.plots_by_id.get(plot_id), surface)


_plot_by_fr_index = None


def _plot_by_fr():
    """Lowercased French text (parentheses dropped, each side of a slash) ->
    the vocab plot that holds it, for the shop games' item orders."""
    global _plot_by_fr_index
    if _plot_by_fr_index is None:
        index = {}
        for plot in state.plots:
            if plot.topic_type == "grammar":
                continue
            for item in plot.items:
                fr = item.get("fr")
                if not fr:
                    continue
                for part in re.sub(r"\([^)]*\)", "", fr).split(" / "):
                    key = " ".join(part.split()).lower()
                    if key:
                        index.setdefault(key, plot)
        _plot_by_fr_index = index
    return _plot_by_fr_index


def plot_for_fr(fr):
    """The plot behind a French text; a "a / b" pair (two names for one dish,
    say) finds the plot of either side."""
    index = _plot_by_fr()
    key = " ".join(str(fr).split()).lower()
    if key in index:
        return index[key]
    for part in re.sub(r"\([^)]*\)", "", str(fr)).split(" / "):
        found = index.get(" ".join(part.split()).lower())
        if found is not None:
            return found
    return None


def credit_game_item(fr, surface):
    """Credit the plot behind a shop-game item's French text, if there is one."""
    return credit_game_plot(plot_for_fr(fr), surface)


def growth_credit_text(surface):
    counts = growth_credit.get(surface)
    if counts is None:
        return ""
    parts = []
    if counts["full"]:
        parts.append(f"watered {counts['full']} plot{'s' if counts['full'] != 1 else ''}")
    if counts["nudge"]:
        parts.append(
            f"nudged {counts['nudge']}" if counts["full"] else
            f"nudged {counts['nudge']} plot{'s' if counts['nudge'] != 1 else ''}"
        )
    if parts:
        return "Plot growth credited: " + ", ".join(parts) + "."
    return "Plot growth credited: none this session."


def _with_growth(message, surface):
    return f"{message} {growth_credit_text(surface)}"


def _review_count_setting():
    raw = _element("review-count-input").value
    try:
        count = int(str(raw).strip())
    except (TypeError, ValueError):
        count = DEFAULT_REVIEW_COUNT
    return max(MIN_REVIEW_COUNT, min(MAX_REVIEW_COUNT, count))


def _review_min_stage_setting():
    raw = _element("review-min-stage-select").value
    return raw if raw in STAGE_RANK else STAGE_SEED


def _review_variant_for(plot, mode):
    """Grammar Review's bias (§14.4: "biased toward fill-in-the-blank/
    conjugation prompts"): if the plot can produce one of those variants,
    roll among just those; otherwise (word review, or a grammar plot that
    can't offer one) let generate_question() pick from its full pool."""
    if mode == WATER_LISTEN_MODE:
        heard = [v for v in variants_for(plot) if v in WATER_LISTEN_VARIANTS]
        return QUESTION_RNG.choice(heard) if heard else None
    if mode == WATER_TYPED_MODE:
        typed = [v for v in variants_for(plot) if v in TYPED_VARIANTS or v in TYPED_BLANK_VARIANTS]
        return QUESTION_RNG.choice(typed) if typed else None
    if mode != "grammar" and not (
        mode in (MARATHON_MODE, PHRASEBOOK_MODE, CRAM_MODE, WEAK_SPOT_MODE, QUICK_WATER_MODE)
        and plot.topic_type == "grammar"
    ):
        return None
    preferred = [v for v in variants_for(plot) if v in GRAMMAR_REVIEW_PREFERRED_VARIANTS]
    return QUESTION_RNG.choice(preferred) if preferred else None


def _advance_review_question():
    global review_question, review_result, review_water_kind, review_listen_revealed
    global review_submitted_answer, review_report_sent, review_pronunciation_report_sent

    # Both report flags and the submitted-answer text are per-question, so
    # every path onto a new question (a fresh session via start_review(), or
    # next_review_question() mid-session) resets them here in one place.
    review_submitted_answer = None
    review_report_sent = False
    review_pronunciation_report_sent = False

    if review_index >= len(review_queue):
        review_question = None
        review_result = None
        return
    plot = state.plots_by_id[review_queue[review_index]]
    review_question = generate_question(
        plot,
        QUESTION_RNG,
        variant=_review_variant_for(plot, review_mode),
        format=WATER_MODE_FORMAT.get(review_mode),
    )
    review_result = None
    review_water_kind = None
    if review_mode == WATER_LISTEN_MODE:
        review_listen_revealed = False
        speak_french(review_question["prompt"])


def start_review(mode, event=None):
    """Roll a fresh Review session: mode is "word" (vocab/phrase) or
    "grammar", the count and minimum-stage filter come from the session's
    own in-page controls (§14.4: both configurable, not fixed)."""
    global review_mode, review_queue, review_index, review_score

    if mode == WEAK_SPOT_MODE:
        review_mode = mode
        queue = [p.plot_id for p in weak_spot_candidates()]
        REVIEW_RNG.shuffle(queue)
        review_queue = queue
    elif mode == CRAM_MODE:
        review_mode = mode
        review_queue = [
            p.plot_id
            for p in cram_candidates(
                _element("review-cram-from-select").value, _element("review-cram-to-select").value
            )
        ]
    elif mode == PHRASEBOOK_MODE:
        # L19: just the saved items, shuffled, whatever their stage or row.
        review_mode = mode
        queue = list(phrasebook)
        REVIEW_RNG.shuffle(queue)
        review_queue = queue[:PHRASEBOOK_SESSION_MAX]
    elif mode == QUICK_WATER_MODE:
        # L29: just the one most overdue plot (marathon_candidates() is already
        # ordered most overdue first, watered plots before never-watered ones).
        review_mode = mode
        review_queue = [p.plot_id for p in marathon_candidates()[:1]]
    elif mode in WATER_MODES:
        # The water chooser's sessions: only plots that can still be watered
        # today, picked by water_session_plots() for the chosen option.
        review_mode = mode
        review_queue = [p.plot_id for p in water_session_plots(mode, water_mode_arg)]
    elif mode == MARATHON_MODE:
        # Ignores the count and minimum-stage controls on purpose: the point
        # is "everything that's due", ordered by how overdue it is.
        review_mode = mode
        review_queue = [p.plot_id for p in marathon_candidates()]
    else:
        topic_types = {"vocab", "phrase"} if mode == "word" else {"grammar"}
        candidates = review_candidates(topic_types, _review_min_stage_setting())
        candidates = _interleave_by_stage(candidates, REVIEW_RNG)

        review_mode = mode
        review_queue = [p.plot_id for p in candidates[: _review_count_setting()]]
    review_index = 0
    review_score = {"correct": 0, "total": 0}
    reset_growth_credit("review")
    _advance_review_question()
    _element("review-answer-input").value = ""
    render()


def submit_review_answer(given):
    global review_result, review_submitted_answer, review_water_kind

    if review_question is None or review_result is not None:
        return None
    typed_mode = review_question["mode"] == "typed"
    review_submitted_answer = str(given).strip() if typed_mode else given
    tier = grading_tier(review_question["answer"]) if typed_mode else None
    review_result = check_answer(
        review_question, given, tier=tier, accent_sensitive=ACCENT_SENSITIVE
    )
    review_score["total"] += 1
    _quest_note("review")
    if review_question.get("variant") == V_GENDER_TAG:
        record_practice("gender", review_result)  # also counts the study day
    elif review_mode == QUICK_WATER_MODE:
        record_practice("quick", review_result)  # L29; also counts the study day
    elif review_mode in WATER_MODES:
        record_practice("wateropts", review_result)  # also counts the study day
    else:
        note_study_answer()
    review_water_kind = None
    if review_result:
        review_score["correct"] += 1
        plot = state.plots_by_id.get(review_question["plot_id"])
        if plot is not None:
            review_water_kind = credit_review_plot(plot, "review")
    render()
    return review_result


def next_review_question(event=None):
    global review_index

    if review_mode is None:
        return None
    review_index += 1
    _advance_review_question()
    _element("review-answer-input").value = ""
    render()
    return review_question


def close_review(event=None):
    global review_mode, review_queue, review_index, review_question, review_result, review_score
    global review_submitted_answer, review_report_sent, review_pronunciation_report_sent

    review_mode = None
    review_queue = []
    review_index = 0
    review_question = None
    review_result = None
    review_score = {"correct": 0, "total": 0}
    review_submitted_answer = None
    review_report_sent = False
    review_pronunciation_report_sent = False
    render()


# --- Milestone 26: report buttons, extended into Review --------------------
#
# Same two mechanisms as the main practice panel (Milestone 9's correctness
# report, Milestone 24's pronunciation-concern report), reusing the exact
# same backend contract and `_dispatch_report()` sender — just reading from
# Review's own `review_question`/`review_result`/`review_submitted_answer`
# instead of the main panel's `current_*` globals. See CLAUDE.md's
# Milestone 26 build note for why this was originally scoped out (Milestone
# 11) and why that scope call was revisited.


def _review_report_payload():
    if review_question is None or review_result is not False:
        return None
    if review_question["mode"] != "typed":
        return None
    return _typed_wrong_report_payload(review_question, review_submitted_answer)


def submit_review_report(event=None):
    global review_report_sent

    if review_report_sent:
        return None
    payload = _review_report_payload()
    if payload is None:
        return None
    review_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _review_pronunciation_report_payload():
    return _plot_pronunciation_report_payload(review_question)


def submit_review_pronunciation_report(event=None):
    global review_pronunciation_report_sent

    if review_pronunciation_report_sent:
        return None
    payload = _review_pronunciation_report_payload()
    if payload is None:
        return None
    review_pronunciation_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def on_toggle_review(event=None):
    global review_controls_open
    review_controls_open = not review_controls_open
    render()


def on_start_word_review(event=None):
    start_review("word")


def on_start_grammar_review(event=None):
    start_review("grammar")


def on_start_marathon_review(event=None):
    start_review(MARATHON_MODE)


def on_quick_water(event=None):
    """L29: one-click, one-question session on the most overdue plot."""
    start_review(QUICK_WATER_MODE)


# ===========================================================================
# Water options (2026-10-08): more ways to water than "Water the next plot"
# ===========================================================================
# A short chooser (the "Water options" button next to "Water the next plot")
# lists every way to pick what to water, each with how many plots it can water
# RIGHT NOW (a plot that has already had its full watering today is not
# counted: it can only be nudged). Every option uses the one watering rule
# (water_plot): the first correct answer for a plot each in-game day waters it,
# a later one nudges it, a wrong answer changes nothing.
#
#   Water next plot            the farm's own most-overdue-first button
#   Water a chosen week        any one row of the farm
#   Water by topic             vocabulary / phrases / grammar / pronunciation
#   Water the wilting plots    the plots that are most overdue, longest first
#   Quick multiple-choice      5 plots, multiple choice only, low effort
#   Typing water               5 plots, typed answers only
#   Listening water            5 plots, hear the French and pick the English
#   Water by minigame          each arcade game, saying which plots it waters
#
# The sessions run in the Review panel (same grading, report buttons and
# end-of-session "watered N plots, nudged M" line).
WATER_ROW_MODE = "waterrow"
WATER_TOPIC_MODE = "watertopic"
WATER_WILTING_MODE = "waterwilting"
WATER_MC_MODE = "watermc"
WATER_TYPED_MODE = "watertyped"
WATER_LISTEN_MODE = "waterlisten"
WATER_MODES = (
    WATER_ROW_MODE, WATER_TOPIC_MODE, WATER_WILTING_MODE, WATER_MC_MODE, WATER_TYPED_MODE, WATER_LISTEN_MODE,
)
WATER_MODE_FORMAT = {WATER_MC_MODE: "choice", WATER_TYPED_MODE: "typed", WATER_LISTEN_MODE: "choice"}
WATER_LISTEN_VARIANTS = (V_FR_EN_CHOICE, V_SYMBOL_NAME_CHOICE)
WATER_SESSION_MAX = 10
WATER_QUICK_COUNT = 5
WATER_TOPICS = (
    ("vocab", "Vocabulary"),
    ("phrase", "Phrases"),
    ("grammar", "Grammar"),
    ("pronunciation", "Pronunciation (letters and accents)"),
)
WATER_EMPTY_MESSAGE = (
    "Nothing in that group can be watered right now: every plot in it has already been watered "
    "today (or there is nothing of that kind). Move the day on, or try another option."
)
LISTEN_HIDDEN_PROMPT = "🔊 Listen, then pick what it means."
water_options_open = False
water_mode_arg = None  # the row number or topic key of the running chooser session
water_row_choice = 1
water_topic_choice = "vocab"
water_option_proxies = []


def _water_order(plots):
    """Most overdue watered plots first, then plots never watered, then watered
    plots that are not due yet; ties keep farm order."""
    day = state.current_day

    def key(plot):
        if plot.next_due is None:
            return (1, 0)
        if plot.next_due <= day:
            return (0, plot.next_due)
        return (2, plot.next_due)

    return sorted(plots, key=key)


def _is_typed_capable(plot):
    return any(v in TYPED_VARIANTS or v in TYPED_BLANK_VARIANTS for v in variants_for(plot))


def _is_listen_capable(plot):
    return plot.topic_type != "grammar" and any(v in WATER_LISTEN_VARIANTS for v in variants_for(plot))


def _topic_match(plot, topic):
    if topic == "pronunciation":
        return plot.topic_type == "phonetic"
    return plot.topic_type == topic


def water_pool(kind, arg=None):
    """Every plot an option could water right now (not yet watered today), in
    the order a session would ask about them. `kind` is "next", "row",
    "topic", "wilting", "mc", "typed" or "listen"."""
    day = state.current_day
    plots = [p for p in state.available_plots() if can_water_now(p)]
    if kind == "next":
        return _water_order([p for p in plots if is_due(p, day)])
    if kind == "row":
        try:
            sequence = int(arg)
        except (TypeError, ValueError):
            return []
        return _water_order([p for p in plots if p.sequence == sequence])
    if kind == "topic":
        return _water_order([p for p in plots if _topic_match(p, arg)])
    if kind == "wilting":
        return sorted((p for p in plots if is_wilting(p, day)), key=lambda p: p.next_due)
    if kind == "mc":
        return _water_order(plots)
    if kind == "typed":
        return _water_order([p for p in plots if _is_typed_capable(p)])
    if kind == "listen":
        return _water_order([p for p in plots if _is_listen_capable(p)])
    return []


_WATER_MODE_KIND = {
    WATER_ROW_MODE: "row",
    WATER_TOPIC_MODE: "topic",
    WATER_WILTING_MODE: "wilting",
    WATER_MC_MODE: "mc",
    WATER_TYPED_MODE: "typed",
    WATER_LISTEN_MODE: "listen",
}
_WATER_MODE_LIMIT = {
    WATER_ROW_MODE: WATER_SESSION_MAX,
    WATER_TOPIC_MODE: WATER_SESSION_MAX,
    WATER_WILTING_MODE: WATER_SESSION_MAX,
    WATER_MC_MODE: WATER_QUICK_COUNT,
    WATER_TYPED_MODE: WATER_QUICK_COUNT,
    WATER_LISTEN_MODE: WATER_QUICK_COUNT,
}


def water_session_plots(mode, arg=None):
    """The plots one chooser session asks about (capped: 10, or 5 for the
    quick options)."""
    return water_pool(_WATER_MODE_KIND[mode], arg)[: _WATER_MODE_LIMIT[mode]]


def water_option_counts():
    """How many plots each option can water right now (uncapped)."""
    return {
        "next": len(water_pool("next")),
        "row": len(water_pool("row", water_row_choice)),
        "topic": len(water_pool("topic", water_topic_choice)),
        "wilting": len(water_pool("wilting")),
        "mc": len(water_pool("mc")),
        "typed": len(water_pool("typed")),
        "listen": len(water_pool("listen")) if speech_available() else 0,
    }


def start_water_session(mode, arg=None, event=None):
    """Begin a chooser session in the Review panel; returns how many plots it
    holds (0 shows the friendly empty message)."""
    global water_mode_arg, water_options_open
    water_mode_arg = arg
    water_options_open = False
    start_review(mode)
    try:
        # Classic: the Review panel is further down the page than the chooser.
        getattr(_element("review-panel"), "scrollIntoView")()
    except Exception:
        pass
    return len(review_queue)


def on_toggle_water_options(event=None):
    global water_options_open
    water_options_open = not water_options_open
    render()


def on_water_row_change(event=None):
    global water_row_choice
    try:
        water_row_choice = int(_element("water-row-select").value)
    except (TypeError, ValueError):
        water_row_choice = 1
    render()


def on_water_topic_change(event=None):
    global water_topic_choice
    value = _element("water-topic-select").value
    if value in {key for key, _ in WATER_TOPICS}:
        water_topic_choice = value
    render()


def on_water_next_option(event=None):
    global water_options_open
    water_options_open = False
    on_water_next()
    render()


def on_water_row_start(event=None):
    start_water_session(WATER_ROW_MODE, water_row_choice)


def on_water_topic_start(event=None):
    start_water_session(WATER_TOPIC_MODE, water_topic_choice)


def on_water_wilting_start(event=None):
    start_water_session(WATER_WILTING_MODE)


def on_water_mc_start(event=None):
    start_water_session(WATER_MC_MODE)


def on_water_typed_start(event=None):
    start_water_session(WATER_TYPED_MODE)


def on_water_listen_start(event=None):
    start_water_session(WATER_LISTEN_MODE)


def on_review_listen(event=None):
    if review_question is not None and review_mode == WATER_LISTEN_MODE:
        speak_french(review_question["prompt"])


def on_review_listen_show(event=None):
    global review_listen_revealed
    review_listen_revealed = True
    render()


def _populate_water_selects():
    row_select = _element("water-row-select")
    row_select.innerHTML = ""
    for row in state.rows:
        option = document.createElement("option")
        option.value = str(row.sequence)
        title = f": {row.chapter_title}" if row.chapter_title else ""
        option.innerText = f"Week {row.sequence}{title}"
        row_select.appendChild(option)
    row_select.value = str(water_row_choice)
    topic_select = _element("water-topic-select")
    topic_select.innerHTML = ""
    for key, label in WATER_TOPICS:
        option = document.createElement("option")
        option.value = key
        option.innerText = label
        topic_select.appendChild(option)
    topic_select.value = water_topic_choice


def _water_count_text(count, unit="plot"):
    if count == 1:
        return f"1 {unit} can be watered now"
    return f"{count} {unit}s can be watered now"


def _destroy_water_option_proxies():
    for proxy in water_option_proxies:
        proxy.destroy()
    water_option_proxies.clear()


def _make_open_game_handler(key):
    def handler(event=None):
        global water_options_open
        water_options_open = False
        minigames.open_game(key)
        render()
    return handler


def render_water_options():
    panel = _element("water-options-panel")
    toggle = _element("water-options-toggle-button")
    toggle.innerText = "Close water options" if water_options_open else "🚿 Water options"
    _destroy_water_option_proxies()
    if not water_options_open:
        panel.hidden = True
        return
    panel.hidden = False
    _element("water-today-line").innerText = water_today_text()
    counts = water_option_counts()
    for key, count in counts.items():
        _element(f"water-opt-{key}-count").innerText = _water_count_text(count)
        _element(f"water-opt-{key}-button").disabled = count == 0
    if not speech_available():
        _element("water-opt-listen-count").innerText = "needs speech synthesis (not available here)"
    games_box = _element("water-games-list")
    games_box.innerHTML = ""
    for row in minigames.water_game_rows():
        line = document.createElement("div")
        line.className = "water-game-row"
        label = document.createElement("span")
        label.className = "water-game-label dashboard-practice-row"
        label.innerText = f"{row['title']} — waters {row['note']}"
        count = document.createElement("span")
        count.className = "water-game-count dashboard-practice-row"
        count.innerText = _water_count_text(row["count"]) if row["available"] else "locked"
        button = document.createElement("button")
        button.className = "secondary"
        button.innerText = "Play"
        button.id = f"water-game-{row['key']}-button"
        button.disabled = not row["available"]
        proxy = create_proxy(_make_open_game_handler(row["key"]))
        button.addEventListener("click", proxy)
        water_option_proxies.append(proxy)
        line.appendChild(label)
        line.appendChild(count)
        line.appendChild(button)
        games_box.appendChild(line)


def _make_review_choice_handler(choice):
    def handler(event=None):
        submit_review_answer(choice)
    return handler


def on_review_submit_typed(event=None):
    submit_review_answer(_element("review-answer-input").value)


def on_review_answer_keydown(event=None):
    if event is not None and getattr(event, "key", None) == "Enter":
        event.preventDefault()
        on_review_submit_typed()


def share_result():
    """JSON for shared/copy-result.js (Z-20): the figures a player would
    paste after a review session -- the session score, plots automated and
    the practice score. No seed text: this game has no seeds."""
    total = review_score["total"]
    stats = []
    if total:
        stats.append(f"{review_score['correct']}/{total} right")
    automated = automated_plot_count()
    stats.append({"n": automated, "one": "plot automated", "many": "plots automated"})
    stats.append(f"{practice_score()} practice points")
    return json.dumps({
        "game": "Le Champ de Mots",
        "score": f"day {state.current_day}",
        "stats": stats,
    })


def render_review():
    _notify_visual_style_context("review" if review_mode is not None else "farm")

    controls = _element("review-controls")
    controls.hidden = not review_controls_open

    panel = _element("review-panel")
    empty_message = _element("review-empty-message")
    summary = _element("review-summary")
    choices_box = _element("review-choices")

    _destroy_review_choice_proxies()
    _element("review-listen-button").hidden = True
    _element("review-listen-show-button").hidden = True
    _element("review-water-note").hidden = True

    # The Copy result button (Z-20) only belongs under the finished summary.
    _element("result-copy-review").hidden = True

    if review_mode is None:
        panel.hidden = True
        empty_message.hidden = True
        summary.hidden = True
        choices_box.innerHTML = ""
        _element("review-report-button").hidden = True
        _element("review-pronunciation-report-button").hidden = True
        return

    if review_question is None:
        choices_box.innerHTML = ""
        _element("review-report-button").hidden = True
        _element("review-pronunciation-report-button").hidden = True
        if not review_queue and review_score["total"] == 0:
            # Session started, but nothing matched the filters.
            panel.hidden = True
            empty_message.hidden = False
            empty_message.innerText = (
                MARATHON_EMPTY_MESSAGE if review_mode == MARATHON_MODE
                else QUICK_WATER_EMPTY_MESSAGE if review_mode == QUICK_WATER_MODE
                else PHRASEBOOK_EMPTY_MESSAGE if review_mode == PHRASEBOOK_MODE
                else WEAK_SPOT_EMPTY_MESSAGE if review_mode == WEAK_SPOT_MODE
                else WATER_EMPTY_MESSAGE if review_mode in WATER_MODES
                else REVIEW_EMPTY_MESSAGE
            )
            summary.hidden = True
            return
        # Queue exhausted -- show the score, nothing else.
        panel.hidden = False
        empty_message.hidden = True
        summary.hidden = False
        summary.innerText = _with_growth(_with_highlights(REVIEW_SUMMARY_MESSAGE.format(**review_score)), "review")
        _element("result-copy-review").hidden = False
        _element("review-progress").innerText = ""
        _element("review-context").innerText = ""
        _element("review-instruction").innerText = ""
        _element("review-prompt").innerText = ""
        _element("review-note").hidden = True
        _element("review-answer-input").hidden = True
        _element("review-submit-button").hidden = True
        _element("review-next-button").hidden = True
        _element("review-feedback").innerText = ""
        return

    panel.hidden = False
    empty_message.hidden = True
    summary.hidden = True
    _element("review-progress").innerText = f"{review_index + 1} of {len(review_queue)}"
    _element("review-context").innerText = review_question["context"]
    _element("review-instruction").innerText = review_question["instruction"]
    listening_hidden = (
        review_mode == WATER_LISTEN_MODE
        and speech_available()
        and not review_listen_revealed
        and review_result is None
    )
    _element("review-prompt").innerText = LISTEN_HIDDEN_PROMPT if listening_hidden else review_question["prompt"]
    listen_button = _element("review-listen-button")
    listen_button.hidden = review_mode != WATER_LISTEN_MODE or not speech_available()
    show_text_button = _element("review-listen-show-button")
    show_text_button.hidden = not listening_hidden

    note = _element("review-note")
    note.innerText = review_question["note"] or ""
    note.hidden = not review_question["note"]

    answered = review_result is not None
    answer_input = _element("review-answer-input")
    submit = _element("review-submit-button")
    next_button = _element("review-next-button")

    choices_box.innerHTML = ""
    if review_question["mode"] == "choice":
        answer_input.hidden = True
        submit.hidden = True
        for index, choice in enumerate(review_question["choices"]):
            button = document.createElement("button")
            button.id = f"review-choice-{index}"
            button.innerText = choice
            button.disabled = answered
            button.className = "choice"
            if answered and choice == review_question["answer"]:
                button.className = "choice choice--answer"
            proxy = create_proxy(_make_review_choice_handler(choice))
            button.addEventListener("click", proxy)
            review_choice_proxies.append(proxy)
            choices_box.appendChild(button)
    else:
        answer_input.hidden = False
        submit.hidden = False
        submit.disabled = answered

    next_button.hidden = not answered

    if answered:
        template = FEEDBACK["correct" if review_result else "incorrect"]
        _element("review-feedback").innerText = template.format(answer=review_question["answer"])
    else:
        _element("review-feedback").innerText = ""
    review_note = water_result_text(review_water_kind, state.plots_by_id.get(review_question["plot_id"])) if (answered and review_result) else ""
    _element("review-water-note").innerText = review_note
    _element("review-water-note").hidden = not review_note

    # Milestone 26: same gating as the main practice panel's own two report
    # buttons -- correctness report only for a wrong typed answer,
    # pronunciation-concern report available the whole time a question is
    # open, regardless of right/wrong or typed/choice.
    report_button = _element("review-report-button")
    show_report = answered and review_result is False and review_question["mode"] == "typed"
    report_button.hidden = not show_report
    if show_report:
        report_button.disabled = review_report_sent
        report_button.innerText = REPORT_SENT_LABEL if review_report_sent else REPORT_BUTTON_LABEL

    pronunciation_button = _element("review-pronunciation-report-button")
    pronunciation_button.hidden = False
    pronunciation_button.disabled = review_pronunciation_report_sent
    pronunciation_button.innerText = (
        PRONUNCIATION_REPORT_SENT_LABEL
        if review_pronunciation_report_sent
        else PRONUNCIATION_REPORT_BUTTON_LABEL
    )


def on_toggle_accent_sensitivity(event=None):
    """§14.2: one global toggle, default ON. Flips on every click rather than
    reading a `checked` property, so the fake-DOM harness (which has no real
    checkbox semantics) can drive it the same way a real click would."""
    global ACCENT_SENSITIVE
    ACCENT_SENSITIVE = not ACCENT_SENSITIVE
    _element("accent-toggle-checkbox").checked = ACCENT_SENSITIVE
    render()


# --- per-browser preferences (remembered, not part of the save code) -------
# index.html defines window.champPrefGet/champPrefSet over localStorage. They
# do not exist under pytest (there is no js.window in the fake module), so both
# helpers quietly do nothing there. Used for the "Always multiple choice"
# setting and every minigame's difficulty.


def pref_get(key, default=None):
    try:
        from js import window

        getter = getattr(window, "champPrefGet", None)
        if getter is None:
            return default
        value = getter(key)
        return default if value is None else str(value)
    except Exception:
        return default


def pref_set(key, value):
    try:
        from js import window

        setter = getattr(window, "champPrefSet", None)
        if setter is not None:
            setter(key, str(value))
    except Exception:
        pass


PREF_ALWAYS_MC = "champ-always-multiple-choice"


def on_toggle_always_mc(event=None):
    """Progressive format off-switch: with this on, every question is multiple
    choice wherever the plot has one (see question_format_percent())."""
    global ALWAYS_MULTIPLE_CHOICE
    ALWAYS_MULTIPLE_CHOICE = not ALWAYS_MULTIPLE_CHOICE
    _element("always-mc-checkbox").checked = ALWAYS_MULTIPLE_CHOICE
    pref_set(PREF_ALWAYS_MC, "1" if ALWAYS_MULTIPLE_CHOICE else "0")
    render()


def format_schedule_lines():
    """The plain-words schedule shown in Settings."""
    return [
        "Seed (never watered): multiple choice only.",
        "Sprout: about 1 question in 5 is typed. Budding: about 2 in 5.",
        "Blooming: about 7 in 10. Automated: about 9 in 10.",
        "A longer run of correct answers and a higher ease nudge the share up; a plot you just missed leans back toward multiple choice.",
    ]


# ===========================================================================
# Milestone 12 — weekly proficiency tests (design doc §14.5)
# ===========================================================================
#
# One test per `sequence` entry (per taught week), covering every topic in
# that week regardless of any plot's current SRS state, purely informational
# — score plus a per-topic breakdown, no gating of anything. Unlike Review
# (Milestone 11), a proficiency test never touches a plot's schedule at all;
# it only reads the catalog and reuses generate_question().


def proficiency_test_topics(sequence):
    """Every topic in one week entry, catalog order, regardless of any
    plot's current SRS state (§14.5, literally)."""
    for week in CATALOG["weeks"]:
        if week["sequence"] == sequence:
            return week["topics"]
    return []


def _topic_plots(topic):
    """Every plot that belongs to one catalog topic. A grammar topic is a
    single plot (Milestone 2's granularity call); everything else is one
    plot per item, so this is every item's plot in catalog order."""
    if topic["topic_type"] == "grammar":
        plot = state.plots_by_id.get(topic["id"])
        return [plot] if plot is not None else []
    plots = []
    for index in range(len(topic["items"])):
        plot = state.plots_by_id.get(f"{topic['id']}-i{index:02d}")
        if plot is not None:
            plots.append(plot)
    return plots


def is_proficiency_test_available(sequence):
    """A proficiency test is only offered for an unlocked week — §14.5 says
    nothing about bypassing §7's row-unlock gate, and letting a test preview
    a locked week's content would do exactly that even though the test
    itself doesn't gate anything (see CLAUDE.md's Milestone 12 build note)."""
    return state.is_row_unlocked(sequence)


def build_proficiency_test(sequence, rng=None, length=PROFICIENCY_TEST_LENGTH):
    """A fixed-length (~15-20 question) session covering every topic in the
    week at least once, then filling the rest of the target length by
    cycling back through the topics. If a week has more topics than the
    target length (none currently do), full topic coverage wins over the
    soft length target."""
    rng = PROFICIENCY_RNG if rng is None else rng
    topic_plots = [
        (topic, plots)
        for topic in proficiency_test_topics(sequence)
        for plots in [_topic_plots(topic)]
        if plots
    ]
    if not topic_plots:
        return []

    target_length = max(length, len(topic_plots))
    entries = [(topic, rng.choice(plots)) for topic, plots in topic_plots]
    cursor = 0
    while len(entries) < target_length:
        topic, plots = topic_plots[cursor % len(topic_plots)]
        entries.append((topic, rng.choice(plots)))
        cursor += 1

    return [
        {
            "topic_id": topic["id"],
            "topic_title": topic["title"],
            "topic_type": topic["topic_type"],
            "question": generate_question(plot, rng),
        }
        for topic, plot in entries[:target_length]
    ]


def start_proficiency_test(sequence, event=None):
    global proficiency_mode, proficiency_sequence, proficiency_questions
    global proficiency_index, proficiency_result, proficiency_score, proficiency_topic_scores
    global proficiency_submitted_answer, proficiency_report_sent, proficiency_pronunciation_report_sent

    if not is_proficiency_test_available(sequence):
        return None

    proficiency_sequence = sequence
    proficiency_questions = build_proficiency_test(sequence, PROFICIENCY_RNG)
    proficiency_index = 0
    proficiency_result = None
    proficiency_score = {"correct": 0, "total": 0}
    proficiency_topic_scores = {
        topic["id"]: {"title": topic["title"], "correct": 0, "total": 0}
        for topic in proficiency_test_topics(sequence)
    }
    proficiency_mode = True
    proficiency_submitted_answer = None
    proficiency_report_sent = False
    proficiency_pronunciation_report_sent = False
    reset_growth_credit("proficiency")
    _element("proficiency-answer-input").value = ""
    render()
    return proficiency_questions


def submit_proficiency_answer(given):
    global proficiency_result, proficiency_submitted_answer

    if proficiency_index >= len(proficiency_questions) or proficiency_result is not None:
        return None
    entry = proficiency_questions[proficiency_index]
    question = entry["question"]
    typed_mode = question["mode"] == "typed"
    proficiency_submitted_answer = str(given).strip() if typed_mode else given
    tier = grading_tier(question["answer"]) if typed_mode else None
    proficiency_result = check_answer(
        question, given, tier=tier, accent_sensitive=ACCENT_SENSITIVE
    )
    proficiency_score["total"] += 1
    record_practice("proficiency", proficiency_result)
    topic_score = proficiency_topic_scores[entry["topic_id"]]
    topic_score["total"] += 1
    if proficiency_result:
        proficiency_score["correct"] += 1
        topic_score["correct"] += 1
        plot = state.plots_by_id.get(question.get("plot_id"))
        if plot is not None:
            credit_review_plot(plot, "proficiency")
    render()
    return proficiency_result


def next_proficiency_question(event=None):
    global proficiency_index, proficiency_result
    global proficiency_submitted_answer, proficiency_report_sent, proficiency_pronunciation_report_sent

    if not proficiency_mode:
        return None
    proficiency_index += 1
    proficiency_result = None
    proficiency_submitted_answer = None
    proficiency_report_sent = False
    proficiency_pronunciation_report_sent = False
    _element("proficiency-answer-input").value = ""
    render()
    return proficiency_index


def close_proficiency_test(event=None):
    global proficiency_mode, proficiency_sequence, proficiency_questions
    global proficiency_index, proficiency_result, proficiency_score, proficiency_topic_scores
    global proficiency_submitted_answer, proficiency_report_sent, proficiency_pronunciation_report_sent

    proficiency_mode = False
    proficiency_sequence = None
    proficiency_questions = []
    proficiency_index = 0
    proficiency_result = None
    proficiency_score = {"correct": 0, "total": 0}
    proficiency_topic_scores = {}
    proficiency_submitted_answer = None
    proficiency_report_sent = False
    proficiency_pronunciation_report_sent = False
    render()


def _current_proficiency_question():
    if proficiency_index >= len(proficiency_questions):
        return None
    return proficiency_questions[proficiency_index]["question"]


# --- Milestone 26: report buttons, extended into Proficiency ---------------
#
# Same reasoning and mechanism as Review's own copy above -- Proficiency's
# questions come from generate_question() the same way Review's do, so they
# carry the same "plot_id"/"topic_type" shape _typed_wrong_report_payload()/
# _plot_pronunciation_report_payload() already expect.


def _proficiency_report_payload():
    question = _current_proficiency_question()
    if question is None or proficiency_result is not False:
        return None
    if question["mode"] != "typed":
        return None
    return _typed_wrong_report_payload(question, proficiency_submitted_answer)


def submit_proficiency_report(event=None):
    global proficiency_report_sent

    if proficiency_report_sent:
        return None
    payload = _proficiency_report_payload()
    if payload is None:
        return None
    proficiency_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _proficiency_pronunciation_report_payload():
    return _plot_pronunciation_report_payload(_current_proficiency_question())


def submit_proficiency_pronunciation_report(event=None):
    global proficiency_pronunciation_report_sent

    if proficiency_pronunciation_report_sent:
        return None
    payload = _proficiency_pronunciation_report_payload()
    if payload is None:
        return None
    proficiency_pronunciation_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _make_proficiency_choice_handler(choice):
    def handler(event=None):
        submit_proficiency_answer(choice)
    return handler


def on_proficiency_submit_typed(event=None):
    submit_proficiency_answer(_element("proficiency-answer-input").value)


def on_proficiency_answer_keydown(event=None):
    if event is not None and getattr(event, "key", None) == "Enter":
        event.preventDefault()
        on_proficiency_submit_typed()


def render_proficiency():
    panel = _element("proficiency-panel")
    choices_box = _element("proficiency-choices")

    _destroy_proficiency_choice_proxies()

    if not proficiency_mode:
        panel.hidden = True
        choices_box.innerHTML = ""
        _element("proficiency-report-button").hidden = True
        _element("proficiency-pronunciation-report-button").hidden = True
        return

    panel.hidden = False
    complete = proficiency_index >= len(proficiency_questions)
    summary = _element("proficiency-summary")
    breakdown = _element("proficiency-topic-breakdown")

    if complete:
        choices_box.innerHTML = ""
        summary.hidden = False
        summary.innerText = _with_growth(_with_highlights(PROFICIENCY_SUMMARY_MESSAGE.format(**proficiency_score)), "proficiency")
        breakdown.innerHTML = ""
        for topic_score in proficiency_topic_scores.values():
            line = document.createElement("p")
            line.className = "proficiency-topic-line"
            line.innerText = PROFICIENCY_TOPIC_LINE.format(**topic_score)
            breakdown.appendChild(line)
        _element("proficiency-progress").innerText = ""
        _element("proficiency-context").innerText = ""
        _element("proficiency-instruction").innerText = ""
        _element("proficiency-prompt").innerText = ""
        _element("proficiency-note").hidden = True
        _element("proficiency-answer-input").hidden = True
        _element("proficiency-submit-button").hidden = True
        _element("proficiency-next-button").hidden = True
        _element("proficiency-feedback").innerText = ""
        _element("proficiency-report-button").hidden = True
        _element("proficiency-pronunciation-report-button").hidden = True
        return

    summary.hidden = True
    breakdown.innerHTML = ""
    entry = proficiency_questions[proficiency_index]
    question = entry["question"]

    _element("proficiency-progress").innerText = (
        f"{proficiency_index + 1} of {len(proficiency_questions)}"
    )
    _element("proficiency-context").innerText = question["context"]
    _element("proficiency-instruction").innerText = question["instruction"]
    _element("proficiency-prompt").innerText = question["prompt"]

    note = _element("proficiency-note")
    note.innerText = question["note"] or ""
    note.hidden = not question["note"]

    answered = proficiency_result is not None
    answer_input = _element("proficiency-answer-input")
    submit = _element("proficiency-submit-button")
    next_button = _element("proficiency-next-button")

    choices_box.innerHTML = ""
    if question["mode"] == "choice":
        answer_input.hidden = True
        submit.hidden = True
        for index, choice in enumerate(question["choices"]):
            button = document.createElement("button")
            button.id = f"proficiency-choice-{index}"
            button.innerText = choice
            button.disabled = answered
            button.className = "choice"
            if answered and choice == question["answer"]:
                button.className = "choice choice--answer"
            proxy = create_proxy(_make_proficiency_choice_handler(choice))
            button.addEventListener("click", proxy)
            proficiency_choice_proxies.append(proxy)
            choices_box.appendChild(button)
    else:
        answer_input.hidden = False
        submit.hidden = False
        submit.disabled = answered

    next_button.hidden = not answered

    if answered:
        template = FEEDBACK["correct" if proficiency_result else "incorrect"]
        _element("proficiency-feedback").innerText = template.format(answer=question["answer"])
    else:
        _element("proficiency-feedback").innerText = ""

    # Milestone 26: same two-button pattern as the main practice panel and
    # Review, above.
    report_button = _element("proficiency-report-button")
    show_report = answered and proficiency_result is False and question["mode"] == "typed"
    report_button.hidden = not show_report
    if show_report:
        report_button.disabled = proficiency_report_sent
        report_button.innerText = (
            REPORT_SENT_LABEL if proficiency_report_sent else REPORT_BUTTON_LABEL
        )

    pronunciation_button = _element("proficiency-pronunciation-report-button")
    pronunciation_button.hidden = False
    pronunciation_button.disabled = proficiency_pronunciation_report_sent
    pronunciation_button.innerText = (
        PRONUNCIATION_REPORT_SENT_LABEL
        if proficiency_pronunciation_report_sent
        else PRONUNCIATION_REPORT_BUTTON_LABEL
    )


# ===========================================================================
# Milestone 13 — bonus sentence-building sections (design doc §14.6)
# ===========================================================================
#
# One original sentence per week (built only from that week's own vocab and
# grammar — see CLAUDE.md's Milestone 13 build note for the exact sourcing
# policy), three tasks each: order the word tiles, translate each tile on
# its own (STRICT — an explicit per-task tier assignment from §14.6, not the
# auto-decided grading_tier() the main farm/Review/proficiency paths use),
# then translate the whole assembled sentence (LENIENT). Purely informational
# like Milestones 11-12: nothing here ever touches a plot's SRS state.

bonus_pool_proxies = []


def _destroy_bonus_pool_proxies():
    for proxy in bonus_pool_proxies:
        proxy.destroy()
    bonus_pool_proxies.clear()


def bonus_sentences_for(sequence):
    for week in CATALOG["weeks"]:
        if week["sequence"] == sequence:
            return week.get("bonus_sentences", [])
    return []


def is_bonus_section_available(sequence):
    """Same posture as the proficiency test (§14.5's build note): only
    offered for an already-unlocked week, so it can't preview a week's
    content ahead of §7's pacing gate."""
    return state.is_row_unlocked(sequence) and bool(bonus_sentences_for(sequence))


def _current_bonus_sentence():
    if bonus_index >= len(bonus_queue):
        return None
    return bonus_queue[bonus_index]


def _begin_bonus_sentence():
    """Reset every per-sentence tracking field and roll a fresh shuffled tile
    pool for whichever sentence `bonus_index` now points at (or close the
    session out if the queue is exhausted)."""
    global bonus_task, bonus_tile_pool, bonus_placed, bonus_order_correct
    global bonus_tile_index, bonus_tile_result, bonus_tile_score, bonus_sentence_result
    global bonus_tile_submitted_answer, bonus_tile_report_sent, bonus_tile_pronunciation_report_sent
    global bonus_sentence_submitted_answer, bonus_sentence_report_sent
    global bonus_sentence_pronunciation_report_sent

    sentence = _current_bonus_sentence()
    bonus_placed = []
    bonus_order_correct = None
    bonus_tile_index = 0
    bonus_tile_result = None
    bonus_tile_score = {"correct": 0, "total": 0}
    bonus_sentence_result = None
    # Both tasks' report state (correctness report + pronunciation report,
    # Milestone 26) is per-sentence just like the typed-answer inputs below,
    # so it's reset here in the same shared spot rather than separately at
    # each task's own entry point.
    bonus_tile_submitted_answer = None
    bonus_tile_report_sent = False
    bonus_tile_pronunciation_report_sent = False
    bonus_sentence_submitted_answer = None
    bonus_sentence_report_sent = False
    bonus_sentence_pronunciation_report_sent = False
    # A fresh sentence starts at the "order" task, but both typed-answer
    # inputs further along (task 2's tile box, task 3's sentence box) can
    # still be holding text from a *previous* sentence's session — cleared
    # here, once, rather than only when each task is separately entered.
    _element("bonus-tile-answer-input").value = ""
    _element("bonus-sentence-answer-input").value = ""

    if sentence is None:
        bonus_task = None
        bonus_tile_pool = []
        return

    pool = list(sentence["tiles"])
    BONUS_RNG.shuffle(pool)
    # A shuffle landing back on the original order would make the ordering
    # task trivially already-solved; nudge it once if that happens.
    if len(pool) > 1 and [t["fr"] for t in pool] == [t["fr"] for t in sentence["tiles"]]:
        pool.reverse()
    bonus_tile_pool = pool
    bonus_task = "order"


def start_bonus_section(sequence, event=None):
    global bonus_mode, bonus_sequence, bonus_queue, bonus_index, bonus_score

    if not is_bonus_section_available(sequence):
        return None

    bonus_sequence = sequence
    bonus_queue = bonus_sentences_for(sequence)
    bonus_index = 0
    bonus_score = {"correct": 0, "total": 0}
    bonus_mode = True
    _begin_bonus_sentence()
    render()
    return bonus_queue


def place_bonus_tile(pool_index):
    """Task 1: move one tile from the pool to the end of the placed list.
    Once the pool empties, the placed order is checked against the
    sentence's real order — a whole-sentence pass/fail, not per-tile."""
    global bonus_order_correct

    if bonus_task != "order" or not (0 <= pool_index < len(bonus_tile_pool)):
        return None
    tile = bonus_tile_pool.pop(pool_index)
    bonus_placed.append(tile)
    if not bonus_tile_pool:
        sentence = _current_bonus_sentence()
        bonus_order_correct = [t["fr"] for t in bonus_placed] == [
            t["fr"] for t in sentence["tiles"]
        ]
        bonus_score["total"] += 1
        if bonus_order_correct:
            bonus_score["correct"] += 1
        record_practice("bonus", bonus_order_correct)
    render()
    return bonus_order_correct


def advance_from_order(event=None):
    """Move on to task 2 once task 1 has a result — right or wrong, §3's
    no-punishment stance means an incorrect order still lets you continue
    (and the correct order becomes obvious once task 2 shows each tile in
    its real place)."""
    global bonus_task

    if bonus_task != "order" or bonus_order_correct is None:
        return None
    bonus_task = "translate_tiles"
    render()


def submit_bonus_tile_translation(given):
    """Task 2, one tile at a time, in the sentence's real order. STRICT by
    explicit task assignment (§14.6) — not decided by grading_tier()."""
    global bonus_tile_result, bonus_tile_submitted_answer

    if bonus_task != "translate_tiles" or bonus_tile_result is not None:
        return None
    sentence = _current_bonus_sentence()
    if sentence is None or bonus_tile_index >= len(sentence["tiles"]):
        return None
    tile = sentence["tiles"][bonus_tile_index]
    bonus_tile_submitted_answer = str(given).strip()
    question = {
        "mode": "typed", "answer": tile["en"], "choices": [],
        "lang": "en", "accepted": tile.get("accepted_en") or [],
    }
    bonus_tile_result = check_answer(
        question, given, tier=TIER_STRICT, accent_sensitive=ACCENT_SENSITIVE
    )
    bonus_tile_score["total"] += 1
    bonus_score["total"] += 1
    record_practice("bonus", bonus_tile_result)
    if bonus_tile_result:
        bonus_tile_score["correct"] += 1
        bonus_score["correct"] += 1
    render()
    return bonus_tile_result


def next_bonus_tile(event=None):
    """Advance to the next tile, or into task 3 once every tile has been
    translated."""
    global bonus_tile_index, bonus_tile_result, bonus_task
    global bonus_tile_submitted_answer, bonus_tile_report_sent, bonus_tile_pronunciation_report_sent

    if bonus_task != "translate_tiles":
        return None
    sentence = _current_bonus_sentence()
    bonus_tile_index += 1
    bonus_tile_result = None
    bonus_tile_submitted_answer = None
    bonus_tile_report_sent = False
    bonus_tile_pronunciation_report_sent = False
    _element("bonus-tile-answer-input").value = ""
    if sentence is None or bonus_tile_index >= len(sentence["tiles"]):
        bonus_task = "translate_sentence"
    render()


def submit_bonus_sentence_translation(given):
    """Task 3: the whole sentence, LENIENT — explicit task assignment (§14.6),
    same reasoning as task 2's STRICT."""
    global bonus_sentence_result, bonus_sentence_submitted_answer

    if bonus_task != "translate_sentence" or bonus_sentence_result is not None:
        return None
    sentence = _current_bonus_sentence()
    if sentence is None:
        return None
    bonus_sentence_submitted_answer = str(given).strip()
    question = {
        "mode": "typed", "answer": sentence["en"], "choices": [],
        "lang": "en", "accepted": sentence.get("accepted_en") or [],
    }
    bonus_sentence_result = check_answer(
        question, given, tier=TIER_LENIENT, accent_sensitive=ACCENT_SENSITIVE
    )
    bonus_score["total"] += 1
    if bonus_sentence_result:
        bonus_score["correct"] += 1
    record_practice("bonus", bonus_sentence_result)
    render()
    return bonus_sentence_result


def next_bonus_sentence(event=None):
    """Move to the next sentence in this week's queue, or end the session
    (bonus_task becomes None) once the queue is exhausted."""
    global bonus_index

    if bonus_task != "translate_sentence" or bonus_sentence_result is None:
        return None
    bonus_index += 1
    _begin_bonus_sentence()
    render()


def close_bonus_section(event=None):
    global bonus_mode, bonus_sequence, bonus_queue, bonus_index, bonus_task
    global bonus_tile_pool, bonus_placed, bonus_order_correct
    global bonus_tile_index, bonus_tile_result, bonus_tile_score
    global bonus_sentence_result, bonus_score
    global bonus_tile_submitted_answer, bonus_tile_report_sent, bonus_tile_pronunciation_report_sent
    global bonus_sentence_submitted_answer, bonus_sentence_report_sent
    global bonus_sentence_pronunciation_report_sent

    bonus_mode = False
    bonus_sequence = None
    bonus_queue = []
    bonus_index = 0
    bonus_task = None
    bonus_tile_pool = []
    bonus_placed = []
    bonus_order_correct = None
    bonus_tile_index = 0
    bonus_tile_result = None
    bonus_tile_score = {"correct": 0, "total": 0}
    bonus_sentence_result = None
    bonus_score = {"correct": 0, "total": 0}
    bonus_tile_submitted_answer = None
    bonus_tile_report_sent = False
    bonus_tile_pronunciation_report_sent = False
    bonus_sentence_submitted_answer = None
    bonus_sentence_report_sent = False
    bonus_sentence_pronunciation_report_sent = False
    render()


# --- Milestone 26: report buttons, extended into Bonus's tasks 2 and 3 -----
#
# Task 1 (tile ordering) has no typed answer and gets neither button, same
# rule that already keeps a wrong multiple-choice pick report-free elsewhere.
# Bonus sentences are hand-authored (§14.6), not plot-backed, so these build
# their own payload shape rather than calling `_typed_wrong_report_payload()`/
# `_plot_pronunciation_report_payload()` — there is no plot or catalog item
# behind a bonus sentence for those to look up. `item_id` instead names the
# sentence (and, for a tile, which tile within it); `topic_type` is a fixed
# marker (`BONUS_TILE_REPORT_TOPIC_TYPE`/`BONUS_SENTENCE_REPORT_TOPIC_TYPE`)
# so a human triaging the queue can tell these apart from plot-backed reports,
# same idea as Milestone 24's "pronunciation" topic_type marker.


def _bonus_tile_report_payload():
    if bonus_task != "translate_tiles" or bonus_tile_result is not False:
        return None
    sentence = _current_bonus_sentence()
    if sentence is None or bonus_tile_index >= len(sentence["tiles"]):
        return None
    tile = sentence["tiles"][bonus_tile_index]
    return {
        "game_id": REPORT_GAME_ID,
        "item_id": f"{sentence['id']}-tile-{bonus_tile_index}",
        "submitted_answer": bonus_tile_submitted_answer or "",
        "marked_correct_answer": generate_accepted_variants(tile["en"]) + [
            e for e in (tile.get("accepted_en") or []) if e not in generate_accepted_variants(tile["en"])
        ],
        "topic_type": BONUS_TILE_REPORT_TOPIC_TYPE,
    }


def submit_bonus_tile_report(event=None):
    global bonus_tile_report_sent

    if bonus_tile_report_sent:
        return None
    payload = _bonus_tile_report_payload()
    if payload is None:
        return None
    bonus_tile_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _bonus_tile_pronunciation_report_payload():
    if bonus_task != "translate_tiles":
        return None
    sentence = _current_bonus_sentence()
    if sentence is None or bonus_tile_index >= len(sentence["tiles"]):
        return None
    tile = sentence["tiles"][bonus_tile_index]
    return {
        "game_id": REPORT_GAME_ID,
        "item_id": f"{sentence['id']}-tile-{bonus_tile_index}",
        "submitted_answer": PRONUNCIATION_REPORT_MARKER,
        "marked_correct_answer": [tile["fr"]],
        "topic_type": PRONUNCIATION_REPORT_TOPIC_TYPE,
    }


def submit_bonus_tile_pronunciation_report(event=None):
    global bonus_tile_pronunciation_report_sent

    if bonus_tile_pronunciation_report_sent:
        return None
    payload = _bonus_tile_pronunciation_report_payload()
    if payload is None:
        return None
    bonus_tile_pronunciation_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _bonus_sentence_report_payload():
    if bonus_task != "translate_sentence" or bonus_sentence_result is not False:
        return None
    sentence = _current_bonus_sentence()
    if sentence is None:
        return None
    return {
        "game_id": REPORT_GAME_ID,
        "item_id": sentence["id"],
        "submitted_answer": bonus_sentence_submitted_answer or "",
        "marked_correct_answer": generate_accepted_variants(sentence["en"]),
        "topic_type": BONUS_SENTENCE_REPORT_TOPIC_TYPE,
    }


def submit_bonus_sentence_report(event=None):
    global bonus_sentence_report_sent

    if bonus_sentence_report_sent:
        return None
    payload = _bonus_sentence_report_payload()
    if payload is None:
        return None
    bonus_sentence_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _bonus_sentence_pronunciation_report_payload():
    if bonus_task != "translate_sentence":
        return None
    sentence = _current_bonus_sentence()
    if sentence is None:
        return None
    return {
        "game_id": REPORT_GAME_ID,
        "item_id": sentence["id"],
        "submitted_answer": PRONUNCIATION_REPORT_MARKER,
        "marked_correct_answer": [sentence["fr"]],
        "topic_type": PRONUNCIATION_REPORT_TOPIC_TYPE,
    }


def submit_bonus_sentence_pronunciation_report(event=None):
    global bonus_sentence_pronunciation_report_sent

    if bonus_sentence_pronunciation_report_sent:
        return None
    payload = _bonus_sentence_pronunciation_report_payload()
    if payload is None:
        return None
    bonus_sentence_pronunciation_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _make_bonus_pool_handler(index):
    def handler(event=None):
        place_bonus_tile(index)
    return handler


def on_bonus_tile_submit_typed(event=None):
    submit_bonus_tile_translation(_element("bonus-tile-answer-input").value)


def on_bonus_tile_answer_keydown(event=None):
    if event is not None and getattr(event, "key", None) == "Enter":
        event.preventDefault()
        on_bonus_tile_submit_typed()


def on_bonus_sentence_submit_typed(event=None):
    submit_bonus_sentence_translation(_element("bonus-sentence-answer-input").value)


def on_bonus_sentence_answer_keydown(event=None):
    if event is not None and getattr(event, "key", None) == "Enter":
        event.preventDefault()
        on_bonus_sentence_submit_typed()


# ===========================================================================
# L11 -- the freeform sentence builder. Unlike a week's Bonus section (one
# sentence, three tasks, opened from that row), this can be opened at any time
# and mixes the bonus sentences of EVERY unlocked week: the English meaning is
# shown and you tap the French word tiles into order. It only ever draws on
# weeks the pacing gate has already unlocked, never touches a plot's SRS state,
# and every finished sentence lands in the practice ledger as "builder", so it
# visibly counts toward the headline practice score and the study streak.
# ===========================================================================
BUILDER_SESSION_LENGTH = 10
BUILDER_RNG = random.Random()
BUILDER_EMPTY_MESSAGE = (
    "No sentences are unlocked yet. Each unlocked week brings its own sentence into the builder."
)
BUILDER_CORRECT = "That's the right order."
BUILDER_INCORRECT = "Not quite. The sentence is: {sentence}"
BUILDER_SUMMARY = "Sentence builder complete: {correct}/{total} in the right order."

builder_active = False
builder_queue = []
builder_index = 0
builder_pool = []
builder_placed = []
builder_result = None
builder_score = {"correct": 0, "total": 0}
builder_proxies = []


def _destroy_builder_proxies():
    for proxy in builder_proxies:
        proxy.destroy()
    builder_proxies.clear()


def builder_sentences():
    """Every bonus sentence from every unlocked week."""
    return [
        sentence
        for week in CATALOG["weeks"]
        if state.is_row_unlocked(week["sequence"])
        for sentence in week.get("bonus_sentences", [])
    ]


def _begin_builder_sentence():
    global builder_pool, builder_placed, builder_result
    builder_placed = []
    builder_result = None
    if builder_index >= len(builder_queue):
        builder_pool = []
        return
    sentence = builder_queue[builder_index]
    pool = list(sentence["tiles"])
    BUILDER_RNG.shuffle(pool)
    # A shuffle that lands on the answer would make the task trivial.
    if len(pool) > 1 and [t["fr"] for t in pool] == [t["fr"] for t in sentence["tiles"]]:
        pool.reverse()
    builder_pool = pool


def start_sentence_builder(event=None):
    global builder_active, builder_queue, builder_index, builder_score
    sentences = builder_sentences()
    BUILDER_RNG.shuffle(sentences)
    builder_queue = sentences[:BUILDER_SESSION_LENGTH]
    builder_index = 0
    builder_score = {"correct": 0, "total": 0}
    builder_active = True
    _begin_builder_sentence()
    render()
    return builder_queue


def place_builder_tile(pool_index):
    """Moves one tile from the pool to the end of the sentence. When the pool
    empties the order is checked (a whole-sentence pass or fail)."""
    global builder_result
    if not builder_active or builder_result is not None or not (0 <= pool_index < len(builder_pool)):
        return None
    builder_placed.append(builder_pool.pop(pool_index))
    if not builder_pool:
        sentence = builder_queue[builder_index]
        builder_result = [t["fr"] for t in builder_placed] == [t["fr"] for t in sentence["tiles"]]
        builder_score["total"] += 1
        if builder_result:
            builder_score["correct"] += 1
        record_practice("builder", builder_result)
    render()
    return builder_result


def undo_builder_tile(event=None):
    """Takes the last placed tile back (only before the sentence is checked)."""
    if not builder_active or builder_result is not None or not builder_placed:
        return False
    builder_pool.append(builder_placed.pop())
    render()
    return True


def next_builder_sentence(event=None):
    global builder_index
    if not builder_active or builder_result is None:
        return None
    builder_index += 1
    _begin_builder_sentence()
    render()
    return builder_index < len(builder_queue)


def close_sentence_builder(event=None):
    global builder_active, builder_queue, builder_index, builder_pool, builder_placed, builder_result
    builder_active = False
    builder_queue = []
    builder_index = 0
    builder_pool = []
    builder_placed = []
    builder_result = None
    render()


def _make_builder_pool_handler(index):
    def handler(event=None):
        place_builder_tile(index)
    return handler


# ===========================================================================
# L5 -- the conversation simulator: a short scripted exchange that chains the
# phrases from several topics. Each turn is either the other person speaking
# (npc, with an English gloss) or an English cue for what you want to say; you
# pick the fitting French line from three. Every line is a phrase from the
# course catalog (placeholders filled in), and a dialogue only opens once every
# topic it draws on sits in an unlocked week, so it can never preview a locked
# week. Wrong picks show the right line and carry on (no punishment); each
# turn lands in the practice ledger as "conversation".
# ===========================================================================
CONVERSATIONS = [
    {
        "id": "meeting", "title": "Meeting someone new",
        "topics": ["fren151-w1-phrase001", "fren151-w2-phrase001", "fren151-w2-phrase002", "fren151-w3-phrase001"],
        "turns": [
            {"npc": "Comment vous appelez-vous?", "gloss": "What's your name? (formal)",
             "options": ["Je m'appelle Léa.", "Ça va bien.", "J'ai vingt ans."]},
            {"npc": "Comment allez-vous?", "gloss": "How are you? (formal)",
             "options": ["Bien, merci. Et vous?", "Je m'appelle Léa.", "Je suis australienne."]},
            {"npc": "Quelle est votre nationalité?", "gloss": "What is your nationality?",
             "options": ["Je suis australienne.", "Ça va bien.", "J'ai vingt ans."]},
            {"npc": "Quel âge avez-vous?", "gloss": "How old are you? (formal)",
             "options": ["J'ai vingt ans.", "Je m'appelle Léa.", "Bien, merci."]},
        ],
    },
    {
        "id": "getting_to_know", "title": "Getting to know you",
        "topics": ["fren151-w4-phrase001", "fren151-w5-phrase001", "fren151-w10-phrase001", "fren151-w9-phrase001"],
        "turns": [
            {"npc": "Qu'est-ce que vous faites dans la vie?", "gloss": "What do you do for a living? (formal)",
             "options": ["Je travaille comme cuisinier.", "J'habite à Sydney.", "Je m'appelle Paul."]},
            {"npc": "Où habitez-vous?", "gloss": "Where do you live?",
             "options": ["J'habite à Sydney.", "Je suis au chômage.", "Bien, merci."]},
            {"npc": "Parlez-vous français?", "gloss": "Do you speak French?",
             "options": ["Je parle un peu de français.", "J'habite à Sydney.", "Je suis fils unique."]},
            {"npc": "As-tu des frères ou des sœurs?", "gloss": "Do you have brothers or sisters?",
             "options": ["Je suis fils unique.", "Je parle un peu de français.", "Je travaille à temps plein."]},
        ],
    },
    {
        "id": "directions", "title": "Asking the way",
        "topics": ["fren151-w6-phrase001", "fren151-w6-phrase002"],
        "turns": [
            {"cue": "You are lost. Ask how to get to the museum.",
             "options": ["Pour aller au musée, s'il vous plaît?", "Où habitez-vous?", "Quelle heure est-il?"]},
            {"cue": "Ask if it is far from here.",
             "options": ["C'est loin d'ici?", "Je préfère Paris.", "Je m'appelle Léa."]},
            {"cue": "Ask if there is a bakery near here.",
             "options": ["Est-ce qu'il y a une boulangerie près d'ici?", "C'est loin d'ici?", "Je préfère Paris."]},
            {"cue": "Say you are looking for the station.",
             "options": ["Je cherche la gare.", "Où habitez-vous?", "Est-ce qu'il y a une boulangerie près d'ici?"]},
        ],
    },
    {
        "id": "shopping", "title": "Shopping for clothes",
        "topics": ["fren152-w7-phrase-slide001"],
        "turns": [
            {"npc": "Je peux vous aider?", "gloss": "Can I help you?",
             "options": ["Je cherche un pull.", "Par carte.", "Je fais du 38."]},
            {"npc": "Vous faites quelle taille?", "gloss": "What size are you?",
             "options": ["Je fais du 38.", "Par carte.", "Je cherche un pull."]},
            {"cue": "Ask if you can try it on.",
             "options": ["Je peux l'essayer?", "C'est combien?", "Vous payez comment?"]},
            {"cue": "Ask how much it is.",
             "options": ["C'est combien?", "Je peux l'essayer?", "En espèces."]},
            {"npc": "Vous payez comment?", "gloss": "How are you paying?",
             "options": ["Par carte.", "Je fais du 38.", "Je cherche un pull."]},
        ],
    },
    {
        "id": "restaurant", "title": "At a restaurant",
        "topics": ["fren152-w11-phrase001", "fren152-w9-phrase001"],
        "turns": [
            {"cue": "Ask the waiter for the menu.",
             "options": ["Pouvez-vous me donner la carte?", "L'addition, s'il vous plaît?", "Avez-vous choisi?"]},
            {"npc": "Avez-vous choisi?", "gloss": "Have you chosen?",
             "options": ["Comme plat principal, je voudrais un steak à point.", "Pouvez-vous me donner la carte?", "Quel est le plat du jour?"]},
            {"cue": "Ask what today's special is.",
             "options": ["Quel est le plat du jour?", "L'addition, s'il vous plaît?", "Avez-vous choisi?"]},
            {"cue": "You have finished. Ask for the bill.",
             "options": ["L'addition, s'il vous plaît?", "Pouvez-vous me donner la carte?", "Quel est le plat du jour?"]},
        ],
    },
    {
        "id": "time_and_dates", "title": "Time and dates",
        "topics": ["fren152-w2-phrase001", "fren152-w5-phrase001", "fren152-w5-phrase002"],
        "turns": [
            {"npc": "Quelle heure est-il?", "gloss": "What time is it?",
             "options": ["Il est seize heures quarante.", "C'est le douze mai.", "J'ai vingt ans."]},
            {"npc": "Quelle est la date de ton anniversaire?", "gloss": "When is your birthday?",
             "options": ["C'est le douze mai.", "Il est seize heures quarante.", "Je m'appelle Léa."]},
            {"cue": "Say that it is noon.",
             "options": ["Il est midi.", "Il est minuit.", "C'est le douze mai."]},
            {"cue": "Ask someone how many hours a week they work.",
             "options": ["Combien d'heures par semaine travaillez-vous?", "Combien de fois par jour travaillez-vous?", "Quelle heure est-il?"]},
        ],
    },
]
CONVERSATION_RNG = random.Random()
CONVERSATION_EMPTY_MESSAGE = (
    "No conversations are unlocked yet. Each one opens once the weeks whose phrases it uses are unlocked."
)
CONVERSATION_CORRECT = "Yes, that fits."
CONVERSATION_INCORRECT = "Not quite. The line that fits is: {line}"
CONVERSATION_SUMMARY = "Conversation complete: {correct}/{total} fitting replies."

conversation_active = False
conversation = None
conversation_turn = 0
conversation_choices = []
conversation_result = None
conversation_picked = None
conversation_score = {"correct": 0, "total": 0}
conversation_last_id = None
conversation_proxies = []


def _destroy_conversation_proxies():
    for proxy in conversation_proxies:
        proxy.destroy()
    conversation_proxies.clear()


def _topic_sequence(topic_id):
    for week in CATALOG["weeks"]:
        for topic in week["topics"]:
            if topic["id"] == topic_id:
                return week["sequence"]
    return None


def conversation_available(entry):
    sequences = [_topic_sequence(t) for t in entry["topics"]]
    return all(s is not None and state.is_row_unlocked(s) for s in sequences)


def available_conversations():
    return [c for c in CONVERSATIONS if conversation_available(c)]


def _begin_conversation_turn():
    global conversation_choices, conversation_result, conversation_picked
    conversation_result = None
    conversation_picked = None
    if conversation is None or conversation_turn >= len(conversation["turns"]):
        conversation_choices = []
        return
    choices = list(conversation["turns"][conversation_turn]["options"])
    CONVERSATION_RNG.shuffle(choices)
    conversation_choices = choices


def start_conversation(event=None, conversation_id=None):
    """Opens one available dialogue (the named one, else a random one other
    than the last played when there is a choice)."""
    global conversation_active, conversation, conversation_turn, conversation_score, conversation_last_id
    options = available_conversations()
    conversation_active = True
    conversation_turn = 0
    conversation_score = {"correct": 0, "total": 0}
    if conversation_id is not None:
        options = [c for c in options if c["id"] == conversation_id]
    elif len(options) > 1:
        options = [c for c in options if c["id"] != conversation_last_id] or options
    conversation = CONVERSATION_RNG.choice(options) if options else None
    if conversation is not None:
        conversation_last_id = conversation["id"]
    _begin_conversation_turn()
    render()
    return conversation


def pick_conversation_line(index):
    """Answers the current turn with the option at `index` (of the shuffled
    choices). Returns True/False, or None when the pick is not allowed now."""
    global conversation_result, conversation_picked
    if not conversation_active or conversation is None or conversation_result is not None:
        return None
    if not (0 <= index < len(conversation_choices)):
        return None
    turn = conversation["turns"][conversation_turn]
    conversation_picked = conversation_choices[index]
    conversation_result = conversation_picked == turn["options"][0]
    conversation_score["total"] += 1
    if conversation_result:
        conversation_score["correct"] += 1
    record_practice("conversation", conversation_result)
    render()
    return conversation_result


def next_conversation_turn(event=None):
    global conversation_turn
    if not conversation_active or conversation is None or conversation_result is None:
        return None
    conversation_turn += 1
    _begin_conversation_turn()
    render()
    return conversation_turn < len(conversation["turns"])


def close_conversation(event=None):
    global conversation_active, conversation, conversation_turn, conversation_choices
    global conversation_result, conversation_picked
    conversation_active = False
    conversation = None
    conversation_turn = 0
    conversation_choices = []
    conversation_result = None
    conversation_picked = None
    render()


def _make_conversation_handler(index):
    def handler(event=None):
        pick_conversation_line(index)
    return handler


# ===========================================================================
# L9 -- listening comprehension. The browser's own speech synthesis reads a
# French sentence aloud (no audio files, no network) and you pick what it
# means from three English options. Sentences are the bonus sentences of the
# unlocked weeks, so it never previews a locked week. It needs a browser with
# speech synthesis (the page's `champSpeak` hook); without one the panel says so
# instead of starting. Answers land in the practice ledger as "listening".
# ===========================================================================
LISTENING_SESSION_LENGTH = 8
LISTENING_RNG = random.Random()
LISTENING_UNAVAILABLE_MESSAGE = (
    "Your browser has no speech voices available, so listening practice cannot start here."
)
LISTENING_EMPTY_MESSAGE = "No sentences are unlocked yet. Each unlocked week brings its own sentence."
LISTENING_CORRECT = "Yes, that is what it says."
LISTENING_INCORRECT = "Not quite. It says: {fr} ({en})"
LISTENING_SUMMARY = "Listening practice complete: {correct}/{total} understood."

listening_active = False
listening_available = True
listening_queue = []
listening_index = 0
listening_choices = []
listening_result = None
listening_score = {"correct": 0, "total": 0}
listening_proxies = []


def _destroy_listening_proxies():
    for proxy in listening_proxies:
        proxy.destroy()
    listening_proxies.clear()


def speech_available():
    """Whether the page can speak French (its `champSpeak` hook exists and the
    browser reports speech synthesis)."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    return getattr(window, "champSpeak", None) is not None and bool(getattr(window, "champSpeechAvailable", lambda: False)())


def speak_french(text, slow=False):
    """Reads `text` aloud; False when the page cannot speak."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    hook = getattr(window, "champSpeak", None)
    if hook is None:
        return False
    hook(str(text), bool(slow))
    return True


def _begin_listening_question(speak=True):
    global listening_choices, listening_result
    listening_result = None
    if listening_index >= len(listening_queue):
        listening_choices = []
        return
    sentence = listening_queue[listening_index]
    others = [s["en"] for s in builder_sentences() if s["en"] != sentence["en"]]
    LISTENING_RNG.shuffle(others)
    choices = [sentence["en"]] + others[:2]
    LISTENING_RNG.shuffle(choices)
    listening_choices = choices
    if speak:
        speak_french(sentence["fr"])


def start_listening(event=None):
    global listening_active, listening_available, listening_queue, listening_index, listening_score
    listening_active = True
    listening_available = speech_available()
    listening_index = 0
    listening_score = {"correct": 0, "total": 0}
    sentences = builder_sentences()
    LISTENING_RNG.shuffle(sentences)
    listening_queue = sentences[:LISTENING_SESSION_LENGTH] if listening_available else []
    _begin_listening_question()
    render()
    return listening_queue


def replay_listening(slow=False):
    if not listening_active or listening_index >= len(listening_queue):
        return False
    return speak_french(listening_queue[listening_index]["fr"], slow=slow)


def on_listening_play(event=None):
    replay_listening(False)


def on_listening_slow(event=None):
    replay_listening(True)


def pick_listening_answer(index):
    global listening_result
    if not listening_active or listening_result is not None or listening_index >= len(listening_queue):
        return None
    if not (0 <= index < len(listening_choices)):
        return None
    sentence = listening_queue[listening_index]
    listening_result = listening_choices[index] == sentence["en"]
    listening_score["total"] += 1
    if listening_result:
        listening_score["correct"] += 1
    record_practice("listening", listening_result)
    render()
    return listening_result


def next_listening_question(event=None):
    global listening_index
    if not listening_active or listening_result is None:
        return None
    listening_index += 1
    _begin_listening_question()
    render()
    return listening_index < len(listening_queue)


def close_listening(event=None):
    global listening_active, listening_queue, listening_index, listening_choices, listening_result
    listening_active = False
    listening_queue = []
    listening_index = 0
    listening_choices = []
    listening_result = None
    render()


def _make_listening_handler(index):
    def handler(event=None):
        pick_listening_answer(index)
    return handler


def render_listening():
    panel = _element("listening-panel")
    choices_box = _element("listening-choices")
    _destroy_listening_proxies()
    choices_box.innerHTML = ""
    if not listening_active:
        panel.hidden = True
        return
    panel.hidden = False
    empty = _element("listening-empty-message")
    summary = _element("listening-summary")
    card = _element("listening-card")
    if not listening_queue:
        empty.hidden = False
        empty.innerText = LISTENING_EMPTY_MESSAGE if listening_available else LISTENING_UNAVAILABLE_MESSAGE
        summary.hidden = True
        card.hidden = True
        _element("listening-progress").innerText = ""
        return
    empty.hidden = True
    if listening_index >= len(listening_queue):
        card.hidden = True
        summary.hidden = False
        summary.innerText = LISTENING_SUMMARY.format(**listening_score)
        _element("listening-progress").innerText = ""
        return
    card.hidden = False
    summary.hidden = True
    sentence = listening_queue[listening_index]
    _element("listening-progress").innerText = f"Sentence {listening_index + 1} of {len(listening_queue)}"
    for index, choice in enumerate(listening_choices):
        button = document.createElement("button")
        button.id = f"listening-choice-{index}"
        button.className = "secondary"
        button.innerText = choice
        button.disabled = listening_result is not None
        proxy = create_proxy(_make_listening_handler(index))
        button.addEventListener("click", proxy)
        listening_proxies.append(proxy)
        choices_box.appendChild(button)
    feedback = _element("listening-feedback")
    if listening_result is None:
        feedback.innerText = ""
    else:
        feedback.innerText = LISTENING_CORRECT if listening_result else LISTENING_INCORRECT.format(
            fr=sentence["fr"], en=sentence["en"]
        )
    _element("listening-next-button").hidden = listening_result is None


# ===========================================================================
# L4b -- placement test. An opt-in, mixed test that samples every stretch of
# the syllabus in increasing difficulty (reusing generate_question() and
# check_answer(), and the proficiency test's topic/plot helpers) and, if the
# player confirms, fast-forwards the plots they demonstrably know to a modest
# starting stage. The rules that keep it safe:
#   * ONLY RAISES. A plot is touched only if it is still completely untouched
#     (a Seed never watered): anything already watered, wilting, in the weeds
#     or further along is left exactly as it is, so a placement can never lower
#     progress and can never be "undone" into a worse state.
#   * MODEST. Known plots become Sprouts (one correct answer's worth), never
#     higher, with a real due date 1..PLACEMENT_SPREAD_DAYS days out (spread
#     across the plots so they do not all fall due on one day), so ordinary
#     reviews still confirm the knowledge.
#   * CONFIRMED FIRST. The result screen states exactly what would change
#     ("You will start at week N; X plots move to Sprout") with Apply/Cancel;
#     nothing is written until Apply.
#   * CONSERVATIVE. The rows are cut into PLACEMENT_BAND_COUNT bands of
#     consecutive weeks; a band is passed with PLACEMENT_PASS_CORRECT right of
#     its PLACEMENT_QUESTIONS_PER_BAND questions (one question per row, cycling
#     back for a short band). The test stops the moment a band is failed (or
#     can no longer be passed), and only the leading passed bands are placed.
# A row's lock state is respected (only unlocked rows are probed or placed; the
# pacing gate itself was removed in L4a so today that is every row). The
# highest row ever placed through is saved as `placement_through` (only once
# non-zero). Every answer feeds the practice ledger as "placement".
# ===========================================================================
PLACEMENT_BAND_COUNT = 6
PLACEMENT_QUESTIONS_PER_BAND = 4
PLACEMENT_PASS_CORRECT = 3
PLACEMENT_START_STAGE = STAGE_SPROUT
PLACEMENT_SPREAD_DAYS = 6  # first due dates land 1..6 days out (< BLOOMING_INTERVAL_DAYS)
PLACEMENT_RNG = random.Random()
PLACEMENT_INTRO = (
    "Already know some French? This test samples every stretch of the course, easiest first, "
    "and stops when a stretch gets hard. You can then skip the weeks you know: those plots start "
    "as Sprouts and still come up for review, so nothing is taken on trust. It never lowers or "
    "locks anything you have already grown."
)
PLACEMENT_HINT = (
    "Coming back to this, or already know some French? Try the placement test to skip the weeks you know."
)
PLACEMENT_EMPTY_MESSAGE = "No weeks are unlocked, so there is nothing to place you in yet."
PLACEMENT_CORRECT = "Correct."
PLACEMENT_INCORRECT = "Not quite. The answer is: {answer}"
PLACEMENT_SUMMARY = "Placement test finished: {correct}/{total} right."
PLACEMENT_BAND_LINE = "Weeks {first}-{last}: {correct}/{total} ({outcome})"
PLACEMENT_NONE_MESSAGE = (
    "No placement: the first stretch was not solid yet, so you start at week {start}. "
    "Nothing has been changed."
)
PLACEMENT_NOTHING_MESSAGE = (
    "You will start at week {start}; none of those plots are untouched, so nothing needs to change."
)
PLACEMENT_PLAN_MESSAGE = (
    "You will start at week {start}; {count} plot{s} move{v} to {stage}. "
    "Plots you have already watered are left alone, and nothing is ever lowered."
)
PLACEMENT_PAST_END_MESSAGE = (
    "You will be placed past the last week; {count} plot{s} move{v} to {stage}. "
    "Plots you have already watered are left alone, and nothing is ever lowered."
)
PLACEMENT_APPLIED_MESSAGE = "Placement applied: {count} plot{s} now start as {stage} and will come up for review soon."
PLACEMENT_RECORD_MESSAGE = "You have already been placed through week {through}. A new test can only move you further."

placement_through = 0  # saved: highest row ever placed through (0 = never)
placement_active = False
placement_phase = "intro"  # intro | testing | summary
placement_queue = []  # [{"band", "sequence", "topic_id", "topic_title", "question"}]
placement_bands_list = []  # [[sequence, ...], ...] for the current session
placement_index = 0
placement_result = None
placement_submitted_answer = None
placement_band_scores = {}  # band -> {"correct", "total"}
placement_plan_data = None
placement_applied = False
placement_proxies = []


def _destroy_placement_proxies():
    for proxy in placement_proxies:
        proxy.destroy()
    placement_proxies.clear()


def placement_bands():
    """The unlocked rows' sequence numbers, in order, cut into at most
    PLACEMENT_BAND_COUNT near-equal groups of consecutive weeks (the first
    groups take the extra rows). 23 rows give bands of 4, 4, 4, 4, 4, 3."""
    sequences = sorted(row.sequence for row in state.rows if state.is_row_unlocked(row.sequence))
    if not sequences:
        return []
    count = min(PLACEMENT_BAND_COUNT, len(sequences))
    base, extra = divmod(len(sequences), count)
    bands = []
    cursor = 0
    for index in range(count):
        size = base + (1 if index < extra else 0)
        bands.append(sequences[cursor:cursor + size])
        cursor += size
    return bands


def _placement_pick(sequence, rng, used):
    """One (topic, plot) for a row: a random topic (so the row's grammar is not
    drowned by its many vocab plots), then a random plot in it, avoiding a plot
    already used in the same band when the row offers another."""
    options = [
        (topic, plot)
        for topic in proficiency_test_topics(sequence)
        for plot in _topic_plots(topic)
    ]
    if not options:
        return None
    fresh = [pair for pair in options if pair[1].plot_id not in used]
    topics = {pair[0]["id"]: pair[0] for pair in (fresh or options)}
    topic = topics[rng.choice(sorted(topics))]
    plots = [pair[1] for pair in (fresh or options) if pair[0]["id"] == topic["id"]]
    return topic, rng.choice(plots)


def build_placement_test(rng=None, bands=None):
    """The whole ladder up front: for each band, PLACEMENT_QUESTIONS_PER_BAND
    questions, one per row (cycling back for a short band). The session may
    end before the last band (see `_placement_band_outcome`)."""
    rng = PLACEMENT_RNG if rng is None else rng
    bands = placement_bands() if bands is None else bands
    queue = []
    for band_index, sequences in enumerate(bands):
        used = set()
        for slot in range(PLACEMENT_QUESTIONS_PER_BAND):
            picked = _placement_pick(sequences[slot % len(sequences)], rng, used)
            if picked is None:
                continue
            topic, plot = picked
            used.add(plot.plot_id)
            queue.append(
                {
                    "band": band_index,
                    "sequence": plot.sequence,
                    "topic_id": topic["id"],
                    "topic_title": topic["title"],
                    "question": generate_question(plot, rng),
                }
            )
    return queue


def _placement_band_outcome(band):
    """'pass', 'fail' (can no longer pass) or 'open' (still undecided)."""
    total = sum(1 for entry in placement_queue if entry["band"] == band)
    scored = placement_band_scores.get(band, {"correct": 0, "total": 0})
    needed = min(PLACEMENT_PASS_CORRECT, total)
    if scored["correct"] >= needed:
        return "pass"
    if scored["correct"] + (total - scored["total"]) < needed:
        return "fail"
    return "open"


def placement_passed_band_count():
    """Leading bands passed. The test stops at the first failed band, and every
    band before it has been asked in full, so this counts 'pass' bands until the
    first one that is not."""
    passed = 0
    for band in range(len(placement_bands_list)):
        if _placement_band_outcome(band) != "pass":
            break
        passed += 1
    return passed


def placement_through_from_results():
    """The last row of the last passed leading band (0 if the first band was
    not passed)."""
    passed = placement_passed_band_count()
    return placement_bands_list[passed - 1][-1] if passed else 0


def build_placement_plan(through):
    """What placing the player through row `through` WOULD do -- pure, it
    mutates nothing. Only plots that are still completely untouched (a Seed
    never watered, no streak, not in the weeds) in an unlocked row up to
    `through` are eligible; each gets a staggered first due offset."""
    eligible = [
        plot
        for row in state.rows
        if row.sequence <= through and state.is_row_unlocked(row.sequence)
        for plot in state.row_plots(row.sequence)
        if plot.stage == STAGE_SEED
        and plot.last_reviewed is None
        and plot.correct_streak == 0
        and not plot.in_weeds
    ]
    last_sequence = max((row.sequence for row in state.rows), default=0)
    return {
        "through": through,
        "start_sequence": through + 1 if through < last_sequence else None,
        "stage": PLACEMENT_START_STAGE,
        "plots": [
            (plot.plot_id, 1 + index % PLACEMENT_SPREAD_DAYS) for index, plot in enumerate(eligible)
        ],
    }


def placement_plan_text(plan):
    count = len(plan["plots"])
    stage = str(plan["stage"]).capitalize()
    if plan["through"] <= 0:
        return PLACEMENT_NONE_MESSAGE.format(start=1)
    if plan["start_sequence"] is None:
        return PLACEMENT_PAST_END_MESSAGE.format(
            count=count, s="" if count == 1 else "s", v="s" if count == 1 else "", stage=stage
        )
    if count == 0:
        return PLACEMENT_NOTHING_MESSAGE.format(start=plan["start_sequence"])
    return PLACEMENT_PLAN_MESSAGE.format(
        start=plan["start_sequence"], count=count, s="" if count == 1 else "s",
        v="s" if count == 1 else "", stage=stage,
    )


def apply_placement(plan=None):
    """Write a confirmed plan. Re-checks each plot is still untouched (so it
    can only ever raise), records the highest row placed through, and returns
    how many plots moved."""
    global placement_through, placement_applied
    plan = placement_plan_data if plan is None else plan
    if plan is None:
        return 0
    moved = 0
    for plot_id, offset in plan["plots"]:
        plot = state.plots_by_id.get(plot_id)
        if (
            plot is None
            or plot.stage != STAGE_SEED
            or plot.last_reviewed is not None
            or plot.correct_streak != 0
            or plot.in_weeds
        ):
            continue
        plot.correct_streak = 1
        plot.interval_days = offset
        plot.last_reviewed = state.current_day
        plot.next_due = state.current_day + offset
        plot.stage = plan["stage"]
        moved += 1
    placement_through = max(placement_through, min(plan["through"], len(state.rows)))
    placement_applied = True
    state.invalidate_unlocks()
    render()
    return moved


def start_placement(event=None):
    global placement_active, placement_phase, placement_queue, placement_bands_list
    global placement_index, placement_result, placement_submitted_answer
    global placement_band_scores, placement_plan_data, placement_applied
    placement_active = True
    placement_phase = "intro"
    placement_queue = []
    placement_bands_list = placement_bands()
    placement_index = 0
    placement_result = None
    placement_submitted_answer = None
    placement_band_scores = {}
    placement_plan_data = None
    placement_applied = False
    render()


def begin_placement_test(event=None):
    global placement_phase, placement_queue, placement_bands_list, placement_index
    global placement_result, placement_submitted_answer, placement_band_scores
    global placement_plan_data, placement_applied
    if not placement_active:
        return []
    placement_bands_list = placement_bands()
    placement_queue = build_placement_test(bands=placement_bands_list)
    placement_index = 0
    placement_result = None
    placement_submitted_answer = None
    placement_band_scores = {}
    placement_plan_data = None
    placement_applied = False
    placement_phase = "testing" if placement_queue else "intro"
    _element("placement-answer-input").value = ""
    render()
    return placement_queue


def _finish_placement():
    global placement_phase, placement_plan_data
    placement_phase = "summary"
    placement_plan_data = build_placement_plan(placement_through_from_results())


def submit_placement_answer(given):
    global placement_result, placement_submitted_answer
    if (
        not placement_active
        or placement_phase != "testing"
        or placement_index >= len(placement_queue)
        or placement_result is not None
    ):
        return None
    entry = placement_queue[placement_index]
    question = entry["question"]
    typed_mode = question["mode"] == "typed"
    placement_submitted_answer = str(given).strip() if typed_mode else given
    tier = grading_tier(question["answer"]) if typed_mode else None
    placement_result = check_answer(question, given, tier=tier, accent_sensitive=ACCENT_SENSITIVE)
    score = placement_band_scores.setdefault(entry["band"], {"correct": 0, "total": 0})
    score["total"] += 1
    if placement_result:
        score["correct"] += 1
    record_practice("placement", placement_result)
    render()
    return placement_result


def next_placement_question(event=None):
    global placement_index, placement_result, placement_submitted_answer
    if not placement_active or placement_phase != "testing" or placement_result is None:
        return None
    band = placement_queue[placement_index]["band"]
    placement_index += 1
    placement_result = None
    placement_submitted_answer = None
    _element("placement-answer-input").value = ""
    if _placement_band_outcome(band) == "fail" or placement_index >= len(placement_queue):
        _finish_placement()
    render()
    return placement_phase


def on_apply_placement(event=None):
    if placement_phase != "summary" or placement_plan_data is None or placement_applied:
        return 0
    return apply_placement()


def close_placement(event=None):
    """Close (or Cancel) the panel. Nothing is written by closing."""
    global placement_active, placement_phase, placement_queue, placement_bands_list
    global placement_index, placement_result, placement_submitted_answer
    global placement_band_scores, placement_plan_data, placement_applied
    placement_active = False
    placement_phase = "intro"
    placement_queue = []
    placement_bands_list = []
    placement_index = 0
    placement_result = None
    placement_submitted_answer = None
    placement_band_scores = {}
    placement_plan_data = None
    placement_applied = False
    render()


def _validated_placement_through(raw):
    if isinstance(raw, bool) or not isinstance(raw, int):
        return 0
    return max(0, min(len(state.rows), raw))


def _make_placement_choice_handler(choice):
    def handler(event=None):
        submit_placement_answer(choice)
    return handler


def on_placement_submit_typed(event=None):
    submit_placement_answer(_element("placement-answer-input").value)


def on_placement_answer_keydown(event=None):
    if event is not None and getattr(event, "key", None) == "Enter":
        on_placement_submit_typed()


def _farm_untouched():
    return all(plot.last_reviewed is None and plot.stage == STAGE_SEED for plot in state.plots)


def render_placement():
    hint = _element("placement-hint")
    hint.hidden = not (placement_through == 0 and _farm_untouched() and not placement_active)
    hint.innerText = PLACEMENT_HINT if not hint.hidden else ""
    panel = _element("placement-panel")
    choices_box = _element("placement-choices")
    _destroy_placement_proxies()
    choices_box.innerHTML = ""
    if not placement_active:
        panel.hidden = True
        return
    panel.hidden = False
    intro = _element("placement-intro")
    start = _element("placement-start-button")
    card = _element("placement-card")
    summary = _element("placement-summary")
    intro_shown = placement_phase == "intro"
    intro.hidden = not intro_shown
    intro.innerText = (
        (PLACEMENT_INTRO if placement_bands_list else PLACEMENT_EMPTY_MESSAGE)
        + (" " + PLACEMENT_RECORD_MESSAGE.format(through=placement_through) if placement_through else "")
    ) if intro_shown else ""
    start.hidden = not (intro_shown and placement_bands_list)
    card.hidden = placement_phase != "testing"
    summary.hidden = placement_phase != "summary"
    for element_id in ("placement-bands", "placement-plan", "placement-status"):
        _element(element_id).hidden = placement_phase != "summary"
    for element_id in ("placement-apply-button", "placement-cancel-button", "placement-retry-button"):
        _element(element_id).hidden = placement_phase != "summary"
    _element("placement-progress").innerText = ""

    if placement_phase == "summary":
        correct = sum(score["correct"] for score in placement_band_scores.values())
        total = sum(score["total"] for score in placement_band_scores.values())
        summary.innerText = PLACEMENT_SUMMARY.format(correct=correct, total=total)
        bands = _element("placement-bands")
        bands.innerHTML = ""
        for band, score in sorted(placement_band_scores.items()):
            line = document.createElement("p")
            line.className = "proficiency-topic-line"
            outcome = _placement_band_outcome(band)
            line.innerText = PLACEMENT_BAND_LINE.format(
                first=placement_bands_list[band][0],
                last=placement_bands_list[band][-1],
                correct=score["correct"],
                total=score["total"],
                outcome="passed" if outcome == "pass" else "not yet",
            )
            bands.appendChild(line)
        plan = placement_plan_data
        _element("placement-plan").innerText = placement_plan_text(plan)
        can_apply = (
            not placement_applied
            and plan["through"] > 0
            and (bool(plan["plots"]) or plan["through"] > placement_through)
        )
        _element("placement-apply-button").disabled = not can_apply
        _element("placement-apply-button").hidden = placement_applied or plan["through"] <= 0
        _element("placement-cancel-button").innerText = "Close" if placement_applied else "Cancel"
        status = _element("placement-status")
        status.innerText = (
            PLACEMENT_APPLIED_MESSAGE.format(
                count=len(plan["plots"]),
                s="" if len(plan["plots"]) == 1 else "s",
                stage=str(plan["stage"]).capitalize(),
            )
            if placement_applied
            else ""
        )
        _element("placement-retry-button").hidden = placement_applied
        return
    if placement_phase != "testing":
        return

    entry = placement_queue[placement_index]
    question = entry["question"]
    _element("placement-progress").innerText = f"{placement_index + 1} of up to {len(placement_queue)}"
    _element("placement-context").innerText = question["context"]
    _element("placement-instruction").innerText = question["instruction"]
    _element("placement-prompt").innerText = question["prompt"]
    note = _element("placement-note")
    note.innerText = question["note"] or ""
    note.hidden = not question["note"]
    answered = placement_result is not None
    answer_input = _element("placement-answer-input")
    submit = _element("placement-submit-button")
    if question["mode"] == "choice":
        answer_input.hidden = True
        submit.hidden = True
        for index, choice in enumerate(question["choices"]):
            button = document.createElement("button")
            button.id = f"placement-choice-{index}"
            button.innerText = choice
            button.disabled = answered
            button.className = "choice choice--answer" if answered and choice == question["answer"] else "choice"
            proxy = create_proxy(_make_placement_choice_handler(choice))
            button.addEventListener("click", proxy)
            placement_proxies.append(proxy)
            choices_box.appendChild(button)
    else:
        answer_input.hidden = False
        submit.hidden = False
        submit.disabled = answered
    _element("placement-next-button").hidden = not answered
    feedback = _element("placement-feedback")
    if not answered:
        feedback.innerText = ""
    else:
        feedback.innerText = (
            PLACEMENT_CORRECT if placement_result else PLACEMENT_INCORRECT.format(answer=question["answer"])
        )


def render_conversation():
    panel = _element("conversation-panel")
    choices_box = _element("conversation-choices")
    _destroy_conversation_proxies()
    choices_box.innerHTML = ""
    if not conversation_active:
        panel.hidden = True
        return
    panel.hidden = False
    empty = _element("conversation-empty-message")
    summary = _element("conversation-summary")
    card = _element("conversation-card")
    if conversation is None:
        empty.hidden = False
        empty.innerText = CONVERSATION_EMPTY_MESSAGE
        summary.hidden = True
        card.hidden = True
        _element("conversation-title").innerText = ""
        _element("conversation-progress").innerText = ""
        return
    empty.hidden = True
    _element("conversation-title").innerText = conversation["title"]
    if conversation_turn >= len(conversation["turns"]):
        card.hidden = True
        summary.hidden = False
        summary.innerText = CONVERSATION_SUMMARY.format(**conversation_score)
        _element("conversation-progress").innerText = ""
        return
    card.hidden = False
    summary.hidden = True
    turn = conversation["turns"][conversation_turn]
    _element("conversation-progress").innerText = f"Turn {conversation_turn + 1} of {len(conversation['turns'])}"
    if "npc" in turn:
        _element("conversation-line").innerText = turn["npc"]
        _element("conversation-gloss").innerText = turn["gloss"]
    else:
        _element("conversation-line").innerText = turn["cue"]
        _element("conversation-gloss").innerText = "Choose what you would say."
    for index, choice in enumerate(conversation_choices):
        button = document.createElement("button")
        button.id = f"conversation-choice-{index}"
        button.className = "secondary"
        button.innerText = choice
        button.disabled = conversation_result is not None
        proxy = create_proxy(_make_conversation_handler(index))
        button.addEventListener("click", proxy)
        conversation_proxies.append(proxy)
        choices_box.appendChild(button)
    feedback = _element("conversation-feedback")
    if conversation_result is None:
        feedback.innerText = ""
    else:
        feedback.innerText = CONVERSATION_CORRECT if conversation_result else CONVERSATION_INCORRECT.format(
            line=turn["options"][0]
        )
    _element("conversation-next-button").hidden = conversation_result is None


def render_builder():
    panel = _element("builder-panel")
    pool_box = _element("builder-pool")
    placed_box = _element("builder-placed")
    _destroy_builder_proxies()
    pool_box.innerHTML = ""
    placed_box.innerHTML = ""
    if not builder_active:
        panel.hidden = True
        return
    panel.hidden = False
    empty = _element("builder-empty-message")
    summary = _element("builder-summary")
    card = _element("builder-card")
    if not builder_queue:
        empty.hidden = False
        empty.innerText = BUILDER_EMPTY_MESSAGE
        summary.hidden = True
        card.hidden = True
        return
    empty.hidden = True
    if builder_index >= len(builder_queue):
        card.hidden = True
        summary.hidden = False
        summary.innerText = BUILDER_SUMMARY.format(**builder_score)
        _element("builder-progress").innerText = ""
        return
    card.hidden = False
    summary.hidden = True
    sentence = builder_queue[builder_index]
    _element("builder-progress").innerText = f"Sentence {builder_index + 1} of {len(builder_queue)}"
    _element("builder-prompt").innerText = sentence["en"]
    for index, tile in enumerate(builder_pool):
        button = document.createElement("button")
        button.id = f"builder-pool-tile-{index}"
        button.innerText = tile["fr"]
        button.className = "bonus-tile"
        proxy = create_proxy(_make_builder_pool_handler(index))
        button.addEventListener("click", proxy)
        builder_proxies.append(proxy)
        pool_box.appendChild(button)
    for tile in builder_placed:
        span = document.createElement("span")
        span.className = "bonus-tile bonus-tile--placed"
        span.innerText = tile["fr"]
        placed_box.appendChild(span)
    _element("builder-undo-button").hidden = builder_result is not None or not builder_placed
    _element("builder-next-button").hidden = builder_result is None
    feedback = _element("builder-feedback")
    if builder_result is None:
        feedback.innerText = ""
    else:
        feedback.innerText = BUILDER_CORRECT if builder_result else BUILDER_INCORRECT.format(sentence=sentence["fr"])


def render_bonus():
    panel = _element("bonus-panel")
    pool_box = _element("bonus-tile-pool")
    placed_box = _element("bonus-tile-placed")

    _destroy_bonus_pool_proxies()

    if not bonus_mode:
        panel.hidden = True
        pool_box.innerHTML = ""
        placed_box.innerHTML = ""
        _element("bonus-tile-report-button").hidden = True
        _element("bonus-tile-pronunciation-report-button").hidden = True
        _element("bonus-sentence-report-button").hidden = True
        _element("bonus-sentence-pronunciation-report-button").hidden = True
        return

    panel.hidden = False
    sentence = _current_bonus_sentence()

    order_section = _element("bonus-order-section")
    tiles_section = _element("bonus-tiles-section")
    sentence_section = _element("bonus-sentence-section")
    summary = _element("bonus-summary")

    if sentence is None:
        # Every sentence in the week's queue is done.
        order_section.hidden = True
        tiles_section.hidden = True
        sentence_section.hidden = True
        summary.hidden = False
        summary.innerText = BONUS_SUMMARY_MESSAGE.format(**bonus_score)
        pool_box.innerHTML = ""
        placed_box.innerHTML = ""
        _element("bonus-tile-report-button").hidden = True
        _element("bonus-tile-pronunciation-report-button").hidden = True
        _element("bonus-sentence-report-button").hidden = True
        _element("bonus-sentence-pronunciation-report-button").hidden = True
        return

    summary.hidden = True
    _element("bonus-progress").innerText = f"Sentence {bonus_index + 1} of {len(bonus_queue)}"

    if bonus_task == "order":
        order_section.hidden = False
        tiles_section.hidden = True
        sentence_section.hidden = True

        pool_box.innerHTML = ""
        for index, tile in enumerate(bonus_tile_pool):
            button = document.createElement("button")
            button.id = f"bonus-pool-tile-{index}"
            button.innerText = tile["fr"]
            button.className = "bonus-tile"
            proxy = create_proxy(_make_bonus_pool_handler(index))
            button.addEventListener("click", proxy)
            bonus_pool_proxies.append(proxy)
            pool_box.appendChild(button)

        placed_box.innerHTML = ""
        for tile in bonus_placed:
            span = document.createElement("span")
            span.className = "bonus-tile bonus-tile--placed"
            span.innerText = tile["fr"]
            placed_box.appendChild(span)

        continue_button = _element("bonus-order-continue-button")
        continue_button.hidden = bonus_order_correct is None
        feedback = _element("bonus-order-feedback")
        if bonus_order_correct is None:
            feedback.innerText = ""
        else:
            feedback.innerText = BONUS_ORDER_CORRECT if bonus_order_correct else (
                BONUS_ORDER_INCORRECT.format(sentence=sentence["fr"])
            )
        # Task 1 has no typed answer, so neither report button ever applies
        # to it -- same rule that keeps a wrong multiple-choice pick
        # report-free everywhere else.
        _element("bonus-tile-report-button").hidden = True
        _element("bonus-tile-pronunciation-report-button").hidden = True
        _element("bonus-sentence-report-button").hidden = True
        _element("bonus-sentence-pronunciation-report-button").hidden = True
        return

    pool_box.innerHTML = ""
    placed_box.innerHTML = ""

    if bonus_task == "translate_tiles":
        order_section.hidden = True
        tiles_section.hidden = False
        sentence_section.hidden = True

        tile = sentence["tiles"][bonus_tile_index]
        _element("bonus-tile-progress").innerText = (
            f"Tile {bonus_tile_index + 1} of {len(sentence['tiles'])}"
        )
        _element("bonus-tile-prompt").innerText = tile["fr"]

        answered = bonus_tile_result is not None
        answer_input = _element("bonus-tile-answer-input")
        submit = _element("bonus-tile-submit-button")
        next_button = _element("bonus-tile-next-button")
        answer_input.hidden = False
        submit.hidden = False
        submit.disabled = answered
        next_button.hidden = not answered

        feedback = _element("bonus-tile-feedback")
        if answered:
            template = FEEDBACK["correct" if bonus_tile_result else "incorrect"]
            feedback.innerText = template.format(answer=tile["en"])
        else:
            feedback.innerText = ""

        # Milestone 26: same two-button pattern as the main practice panel.
        report_button = _element("bonus-tile-report-button")
        show_report = answered and bonus_tile_result is False
        report_button.hidden = not show_report
        if show_report:
            report_button.disabled = bonus_tile_report_sent
            report_button.innerText = (
                REPORT_SENT_LABEL if bonus_tile_report_sent else REPORT_BUTTON_LABEL
            )
        pronunciation_button = _element("bonus-tile-pronunciation-report-button")
        pronunciation_button.hidden = False
        pronunciation_button.disabled = bonus_tile_pronunciation_report_sent
        pronunciation_button.innerText = (
            PRONUNCIATION_REPORT_SENT_LABEL
            if bonus_tile_pronunciation_report_sent
            else PRONUNCIATION_REPORT_BUTTON_LABEL
        )
        _element("bonus-sentence-report-button").hidden = True
        _element("bonus-sentence-pronunciation-report-button").hidden = True
        return

    if bonus_task == "translate_sentence":
        order_section.hidden = True
        tiles_section.hidden = True
        sentence_section.hidden = False

        _element("bonus-sentence-prompt").innerText = sentence["fr"]
        answered = bonus_sentence_result is not None
        answer_input = _element("bonus-sentence-answer-input")
        submit = _element("bonus-sentence-submit-button")
        next_button = _element("bonus-sentence-next-button")
        answer_input.hidden = False
        submit.hidden = False
        submit.disabled = answered
        next_button.hidden = not answered

        feedback = _element("bonus-sentence-feedback")
        if answered:
            template = FEEDBACK["correct" if bonus_sentence_result else "incorrect"]
            feedback.innerText = template.format(answer=sentence["en"])
        else:
            feedback.innerText = ""

        # Milestone 26: same two-button pattern as the main practice panel.
        _element("bonus-tile-report-button").hidden = True
        _element("bonus-tile-pronunciation-report-button").hidden = True
        report_button = _element("bonus-sentence-report-button")
        show_report = answered and bonus_sentence_result is False
        report_button.hidden = not show_report
        if show_report:
            report_button.disabled = bonus_sentence_report_sent
            report_button.innerText = (
                REPORT_SENT_LABEL if bonus_sentence_report_sent else REPORT_BUTTON_LABEL
            )
        pronunciation_button = _element("bonus-sentence-pronunciation-report-button")
        pronunciation_button.hidden = False
        pronunciation_button.disabled = bonus_sentence_pronunciation_report_sent
        pronunciation_button.innerText = (
            PRONUNCIATION_REPORT_SENT_LABEL
            if bonus_sentence_pronunciation_report_sent
            else PRONUNCIATION_REPORT_BUTTON_LABEL
        )


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

exam_date = None  # "YYYY-MM-DD" or None
exam_minutes = PLANNER_DEFAULT_MINUTES
planner_open = False
_planner_cache = {}


def _day_number(iso):
    """Whole days since 1970-01-01 for a valid 'YYYY-MM-DD', else None."""
    parsed = _parse_iso_date(iso)
    if parsed is None:
        return None
    return _calendar.timegm((parsed[0], parsed[1], parsed[2], 0, 0, 0)) // 86400


def exam_days_left():
    """Days from today to the exam date (0 = today, negative = passed), or
    None when there is no date or no clock."""
    if exam_date is None:
        return None
    today = _day_number(study_today())
    target = _day_number(exam_date)
    if today is None or target is None:
        return None
    return target - today


def _clamp_minutes(value):
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return PLANNER_DEFAULT_MINUTES
    minutes = max(PLANNER_MIN_MINUTES, min(PLANNER_MAX_MINUTES, minutes))
    return round(minutes / PLANNER_STEP_MINUTES) * PLANNER_STEP_MINUTES


class _SimPlot:
    """Just the scheduling fields schedule_after_review() reads and writes."""

    __slots__ = ("ease_factor", "interval_days", "last_reviewed", "next_due", "correct_streak", "stage")

    def __init__(self, plot):
        self.ease_factor = plot.ease_factor
        self.interval_days = plot.interval_days
        self.last_reviewed = plot.last_reviewed
        self.next_due = plot.next_due
        self.correct_streak = plot.correct_streak
        self.stage = plot.stage


def reviews_per_day(minutes):
    return max(0, int(minutes * 60 // STUDY_BUDDY_SECONDS_PER_REVIEW))


def simulate_harvest(days, minutes, miss_every=0):
    """How many plots would be Automated after `days` days of `minutes` a
    day, replaying the real scheduler on copies (no real plot is touched).
    `miss_every` > 0 makes every n-th answer wrong. Returns
    {"automated", "total", "percent"}."""
    sims = [_SimPlot(plot) for plot in state.plots]
    first_day = state.current_day
    queue = [
        (sim.next_due if isinstance(sim.next_due, int) else first_day, index)
        for index, sim in enumerate(sims)
        if sim.last_reviewed is not None
    ]
    heapq.heapify(queue)
    unplanted = [index for index, sim in enumerate(sims) if sim.last_reviewed is None]
    planted = 0
    capacity = reviews_per_day(minutes)
    answered = 0
    for offset in range(max(0, min(days, PLANNER_MAX_DAYS))):
        day = first_day + offset
        room = capacity
        while room and queue and queue[0][0] <= day:
            _due, index = heapq.heappop(queue)
            answered += 1
            correct = not (miss_every and answered % miss_every == 0)
            schedule_after_review(sims[index], correct, day)
            heapq.heappush(queue, (sims[index].next_due, index))
            room -= 1
        while room and planted < len(unplanted):
            index = unplanted[planted]
            planted += 1
            answered += 1
            correct = not (miss_every and answered % miss_every == 0)
            schedule_after_review(sims[index], correct, day)
            heapq.heappush(queue, (sims[index].next_due, index))
            room -= 1
    automated = sum(1 for sim in sims if sim.stage == STAGE_AUTOMATED)
    total = len(sims)
    return {"automated": automated, "total": total, "percent": (100.0 * automated / total) if total else 0.0}


def _farm_signature():
    """A cheap fingerprint of every plot's scheduling state, so a cached
    projection is reused until something that matters changes."""
    return hash(
        tuple((p.interval_days, p.next_due, p.correct_streak, p.last_reviewed, p.stage) for p in state.plots)
    )


def current_automated_percent():
    total = len(state.plots)
    return (100.0 * automated_plot_count() / total) if total else 0.0


def planner_projection(minutes=None):
    """{"days", "minutes", "cautious", "best", "current"} for the saved exam
    date, or None when there is no usable date. Cached on the inputs."""
    days = exam_days_left()
    if days is None or days <= 0:
        return None
    minutes = exam_minutes if minutes is None else _clamp_minutes(minutes)
    key = ("proj", exam_date, days, minutes, state.current_day, _farm_signature())
    cached = _planner_cache.get(key)
    if cached is not None:
        return cached
    result = {
        "days": days,
        "minutes": minutes,
        "reviews": reviews_per_day(minutes),
        "cautious": simulate_harvest(days, minutes, PLANNER_MISS_EVERY)["percent"],
        "best": simulate_harvest(days, minutes, 0)["percent"],
        "current": current_automated_percent(),
    }
    _planner_cache.clear()
    _planner_cache[key] = result
    return result


def planner_minimum_minutes():
    """The smallest daily effort (in PLANNER_STEP_MINUTES steps) whose
    cautious projection reaches PLANNER_TARGET_PERCENT: ("already", None)
    when the farm is there now, ("minutes", n), or ("unreachable", best
    percent at the maximum effort). None when there is no usable date."""
    days = exam_days_left()
    if days is None or days <= 0:
        return None
    key = ("min", exam_date, days, state.current_day, _farm_signature())
    cached = _planner_cache.get(key)
    if cached is not None:
        return cached
    if current_automated_percent() >= PLANNER_TARGET_PERCENT:
        result = ("already", None)
    else:
        steps = list(range(PLANNER_MIN_MINUTES, PLANNER_MAX_MINUTES + 1, PLANNER_STEP_MINUTES))

        def reaches(minutes):
            return simulate_harvest(days, minutes, PLANNER_MISS_EVERY)["percent"] >= PLANNER_TARGET_PERCENT

        if not reaches(steps[-1]):
            best = simulate_harvest(days, steps[-1], PLANNER_MISS_EVERY)["percent"]
            result = ("unreachable", best)
        else:
            low, high = 0, len(steps) - 1
            while low < high:
                middle = (low + high) // 2
                if reaches(steps[middle]):
                    high = middle
                else:
                    low = middle + 1
            result = ("minutes", steps[low])
    _planner_cache[key] = result
    return result


def exam_countdown_text():
    """The header chip: days to go plus the projected coverage at the saved
    daily effort. Empty (so the chip hides) with no date, no clock, or a date
    that has already passed."""
    days = exam_days_left()
    if days is None or days < 0:
        return ""
    if days == 0:
        return "Exam today"
    projection = planner_projection()
    when = f"Exam in {days} day{'s' if days != 1 else ''}"
    if projection is None:
        return when
    return f"{when} · about {projection['cautious']:.0f}% automated by then"


def set_exam_date(value):
    """Store (or clear, with an empty/invalid value) the exam date. Returns
    True when a valid date is now set."""
    global exam_date
    text = str(value or "").strip()
    exam_date = text if _parse_iso_date(text) is not None else None
    _planner_cache.clear()
    render()
    return exam_date is not None


def set_exam_minutes(value):
    global exam_minutes
    exam_minutes = _clamp_minutes(value)
    render()
    return exam_minutes


def on_toggle_planner(event=None):
    global planner_open
    planner_open = not planner_open
    render()


def on_planner_date_change(event=None):
    set_exam_date(_element("planner-date-input").value)


def on_planner_minutes_change(event=None):
    set_exam_minutes(_element("planner-minutes-input").value)


def on_planner_clear(event=None):
    _element("planner-date-input").value = ""
    set_exam_date("")


def _validated_exam_plan(raw):
    """(date or None, minutes) from an untrusted save value."""
    if not isinstance(raw, dict):
        return None, PLANNER_DEFAULT_MINUTES
    date = raw.get("date")
    date = date if isinstance(date, str) and _parse_iso_date(date) is not None else None
    minutes = raw.get("minutes")
    if isinstance(minutes, bool) or not isinstance(minutes, int):
        minutes = PLANNER_DEFAULT_MINUTES
    return date, _clamp_minutes(minutes)


def render_planner():
    tile = _element("exam-countdown-tile")
    text = exam_countdown_text()
    _element("exam-countdown-display").innerText = text
    tile.hidden = not text

    toggle = _element("planner-toggle-button")
    toggle.innerText = "Hide exam planner" if planner_open else "📅 Exam planner"
    panel = _element("planner-panel")
    panel.hidden = not planner_open
    if not planner_open:
        return
    date_input = _element("planner-date-input")
    date_input.value = exam_date or ""
    minutes_input = _element("planner-minutes-input")
    minutes_input.value = str(exam_minutes)
    _element("planner-minutes-label").innerText = f"{exam_minutes} minutes a day"

    days = exam_days_left()
    summary, projection_line, suggestion = "", "", ""
    if exam_date is None:
        summary = "Pick your exam date to see what a few minutes a day adds up to."
    elif days is None:
        summary = "Today's date is not available here, so the countdown cannot be worked out."
    elif days < 0:
        summary = "That date has passed. Pick a new one, or clear it."
    elif days == 0:
        summary = "The exam is today. Whatever you have grown is what you take in."
    else:
        summary = f"{days} day{'s' if days != 1 else ''} to go (exam on {exam_date})."
        projection = planner_projection()
        projection_line = (
            f"At {projection['minutes']} minutes a day (about {projection['reviews']} answers a day), "
            f"roughly {projection['cautious']:.0f}% of the farm would be Automated by then, "
            f"or up to {projection['best']:.0f}% if every answer were right. "
            f"Right now: {projection['current']:.0f}%."
        )
        found = planner_minimum_minutes()
        if found is not None:
            kind, value = found
            if kind == "already":
                suggestion = f"The farm is already at {PLANNER_TARGET_PERCENT}% Automated or more. Keeping it watered is enough."
            elif kind == "minutes":
                suggestion = (
                    f"To reach {PLANNER_TARGET_PERCENT}% Automated by then, aim for at least {value} "
                    f"minute{'s' if value != 1 else ''} a day."
                )
            else:
                suggestion = (
                    f"{PLANNER_TARGET_PERCENT}% is out of reach in this time, even at {PLANNER_MAX_MINUTES} "
                    f"minutes a day (best about {value:.0f}%). A mock exam over the weeks it covers is a better use of the time."
                )
    _element("planner-summary").innerText = summary
    _element("planner-projection").innerText = projection_line
    _element("planner-projection").hidden = not projection_line
    _element("planner-suggestion").innerText = suggestion
    _element("planner-suggestion").hidden = not suggestion


# ===========================================================================
# L-20: an on-screen accent bar beside every typed answer box
# ===========================================================================
#
# One row of letter buttons (e with its accents, the cedilla, the oe ligature,
# and so on) under each typed-answer box, so a phone or a keyboard without
# French accents can still type an accent-checked answer. Pressing a key puts
# the letter at the caret and keeps the box focused (mousedown is cancelled so
# a phone keeps its keyboard up). The keys stay out of the tab order (a typist
# already has the box) but carry names for a screen reader. A bar is shown
# exactly when its box is shown, and it stays quietly dimmed while the accent
# check is off ("accents optional"), working with the existing toggle rather
# than replacing it. Built once at boot; nothing here is saved or timed.
ACCENT_CHARS = [
    ("é", "e acute"), ("è", "e grave"), ("ê", "e circumflex"), ("ë", "e diaeresis"),
    ("à", "a grave"), ("â", "a circumflex"), ("î", "i circumflex"), ("ï", "i diaeresis"),
    ("ô", "o circumflex"), ("ù", "u grave"), ("û", "u circumflex"), ("ü", "u diaeresis"),
    ("ç", "c cedilla"), ("œ", "o e ligature"), ("æ", "a e ligature"), ("ÿ", "y diaeresis"),
]
ACCENT_BARS = {
    "accent-bar-practice": "practice-answer-input",
    "accent-bar-review": "review-answer-input",
    "accent-bar-proficiency": "proficiency-answer-input",
    "accent-bar-placement": "placement-answer-input",
    "accent-bar-bonus-tile": "bonus-tile-answer-input",
    "accent-bar-bonus-sentence": "bonus-sentence-answer-input",
}
ACCENT_BAR_OPTIONAL_NOTE = "Accents are optional right now (the accent check is off)."


def accent_sensitive_now():
    """Whether typed answers are being checked for accents right now."""
    return ACCENT_SENSITIVE


def insert_accent(input_id, char):
    """Put `char` at the caret (replacing any selection) in the named box and
    return the new text. With no caret information the letter goes on the end."""
    box = _element(input_id)
    value = str(box.value or "")
    start = getattr(box, "selectionStart", None)
    end = getattr(box, "selectionEnd", None)
    if isinstance(start, bool) or not isinstance(start, int):
        start = len(value)
    if isinstance(end, bool) or not isinstance(end, int):
        end = start
    start = max(0, min(start, len(value)))
    end = max(start, min(end, len(value)))
    box.value = value[:start] + char + value[end:]
    caret = start + len(char)
    try:
        box.setSelectionRange(caret, caret)
        box.focus()
    except Exception:
        pass  # a missing caret API must never lose the letter
    return box.value


def _make_accent_handler(input_id, char):
    def handler(event=None):
        insert_accent(input_id, char)
    return handler


def _keep_input_focus(event=None):
    if event is not None and hasattr(event, "preventDefault"):
        event.preventDefault()


def build_accent_bars():
    for bar_id, input_id in ACCENT_BARS.items():
        bar = _element(bar_id)
        bar.innerHTML = ""
        for char, name in ACCENT_CHARS:
            key = document.createElement("button")
            key.type = "button"
            key.className = "secondary accent-key"
            key.innerText = char
            key.setAttribute("aria-label", f"{char}, {name}")
            key.setAttribute("tabindex", "-1")
            key.title = name
            key.addEventListener("mousedown", create_proxy(_keep_input_focus))
            key.addEventListener("click", create_proxy(_make_accent_handler(input_id, char)))
            bar.appendChild(key)


def render_accent_bars():
    optional = not accent_sensitive_now()
    for bar_id, input_id in ACCENT_BARS.items():
        bar = _element(bar_id)
        bar.hidden = bool(_element(input_id).hidden)
        bar.className = "accent-bar accent-bar--optional" if optional else "accent-bar"
        bar.title = ACCENT_BAR_OPTIONAL_NOTE if optional else ""


def setup():
    global ALWAYS_MULTIPLE_CHOICE
    build_farm()
    render_legend()
    build_accent_bars()
    _element("practice-submit-button").addEventListener("click", create_proxy(on_submit_typed))
    _element("practice-answer-input").addEventListener("keydown", create_proxy(on_answer_keydown))
    _element("practice-close-button").addEventListener("click", create_proxy(close_practice))
    _element("practice-slip-button").addEventListener("click", create_proxy(forgive_slip))
    _element("practice-leech-rest-button").addEventListener("click", create_proxy(rest_leech))
    _element("practice-next-button").addEventListener(
        "click", create_proxy(on_next_practice_plot)
    )
    _element("practice-report-button").addEventListener("click", create_proxy(submit_report))
    _element("practice-pronunciation-report-button").addEventListener(
        "click", create_proxy(submit_pronunciation_report)
    )
    _element("practice-confidence-sure-button").addEventListener(
        "click", create_proxy(lambda event=None: set_confidence("sure"))
    )
    _element("practice-confidence-unsure-button").addEventListener(
        "click", create_proxy(lambda event=None: set_confidence("unsure"))
    )
    _element("water-next-button").addEventListener("click", create_proxy(on_water_next))
    _element("next-day-button").addEventListener("click", create_proxy(on_next_day))
    _element("accent-toggle-checkbox").addEventListener(
        "click", create_proxy(on_toggle_accent_sensitivity)
    )
    _element("accent-toggle-checkbox").checked = ACCENT_SENSITIVE
    _element("review-toggle-button").addEventListener("click", create_proxy(on_toggle_review))
    _element("cultural-notes-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_cultural_notes)
    )
    _element("dashboard-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_dashboard)
    )
    _element("calendar-toggle-button").addEventListener("click", create_proxy(on_toggle_calendar))
    _element("farm-filter-select").addEventListener("change", create_proxy(on_farm_filter_change))
    _element("farm-sort-select").addEventListener("change", create_proxy(on_farm_sort_change))
    _element("planner-toggle-button").addEventListener("click", create_proxy(on_toggle_planner))
    _element("planner-date-input").addEventListener("change", create_proxy(on_planner_date_change))
    _element("planner-minutes-input").addEventListener("input", create_proxy(on_planner_minutes_change))
    _element("planner-minutes-input").addEventListener("change", create_proxy(on_planner_minutes_change))
    _element("planner-clear-button").addEventListener("click", create_proxy(on_planner_clear))
    _populate_cram_selects()
    _populate_water_selects()
    ALWAYS_MULTIPLE_CHOICE = pref_get(PREF_ALWAYS_MC) == "1"
    _load_semester_prefs()
    _element("always-mc-checkbox").checked = ALWAYS_MULTIPLE_CHOICE
    _element("format-schedule-note").innerText = " ".join(format_schedule_lines())
    _element("always-mc-checkbox").addEventListener("click", create_proxy(on_toggle_always_mc))
    _element("water-options-toggle-button").addEventListener("click", create_proxy(on_toggle_water_options))
    _element("water-options-close-button").addEventListener("click", create_proxy(on_toggle_water_options))
    _element("shop-toggle-button").addEventListener("click", create_proxy(on_toggle_shop))
    _element("shop-close-button").addEventListener("click", create_proxy(on_toggle_shop))
    _element("water-row-select").addEventListener("change", create_proxy(on_water_row_change))
    _element("water-topic-select").addEventListener("change", create_proxy(on_water_topic_change))
    _element("water-opt-next-button").addEventListener("click", create_proxy(on_water_next_option))
    _element("water-opt-row-button").addEventListener("click", create_proxy(on_water_row_start))
    _element("water-opt-topic-button").addEventListener("click", create_proxy(on_water_topic_start))
    _element("water-opt-wilting-button").addEventListener("click", create_proxy(on_water_wilting_start))
    _element("water-opt-mc-button").addEventListener("click", create_proxy(on_water_mc_start))
    _element("water-opt-typed-button").addEventListener("click", create_proxy(on_water_typed_start))
    _element("water-opt-listen-button").addEventListener("click", create_proxy(on_water_listen_start))
    _element("review-listen-button").addEventListener("click", create_proxy(on_review_listen))
    _element("review-listen-show-button").addEventListener("click", create_proxy(on_review_listen_show))
    _element("practice-deepdive-button").addEventListener("click", create_proxy(on_toggle_deepdive))
    _element("review-cram-button").addEventListener("click", create_proxy(on_start_cram_review))
    _element("review-weakspots-button").addEventListener("click", create_proxy(on_start_weak_spot_review))
    _element("phrasebook-toggle-button").addEventListener("click", create_proxy(on_toggle_phrasebook_panel))
    _element("phrasebook-practice-button").addEventListener("click", create_proxy(on_start_phrasebook_review))
    _element("practice-bookmark-button").addEventListener("click", create_proxy(on_bookmark_practice))
    _element("review-bookmark-button").addEventListener("click", create_proxy(on_bookmark_review))
    _element("calendar-prev-button").addEventListener("click", create_proxy(on_calendar_prev))
    _element("calendar-next-button").addEventListener("click", create_proxy(on_calendar_next))
    _element("review-word-button").addEventListener("click", create_proxy(on_start_word_review))
    _element("review-grammar-button").addEventListener(
        "click", create_proxy(on_start_grammar_review)
    )
    _element("quick-water-button").addEventListener("click", create_proxy(on_quick_water))
    _element("sentence-builder-button").addEventListener("click", create_proxy(start_sentence_builder))
    _element("conversation-button").addEventListener("click", create_proxy(start_conversation))
    _element("listening-button").addEventListener("click", create_proxy(start_listening))
    _element("placement-button").addEventListener("click", create_proxy(start_placement))
    _element("placement-start-button").addEventListener("click", create_proxy(begin_placement_test))
    _element("placement-submit-button").addEventListener("click", create_proxy(on_placement_submit_typed))
    _element("placement-answer-input").addEventListener("keydown", create_proxy(on_placement_answer_keydown))
    _element("placement-next-button").addEventListener("click", create_proxy(next_placement_question))
    _element("placement-apply-button").addEventListener("click", create_proxy(on_apply_placement))
    _element("placement-cancel-button").addEventListener("click", create_proxy(close_placement))
    _element("placement-retry-button").addEventListener("click", create_proxy(begin_placement_test))
    _element("placement-close-button").addEventListener("click", create_proxy(close_placement))
    _element("listening-play-button").addEventListener("click", create_proxy(on_listening_play))
    _element("listening-slow-button").addEventListener("click", create_proxy(on_listening_slow))
    _element("listening-next-button").addEventListener("click", create_proxy(next_listening_question))
    _element("listening-close-button").addEventListener("click", create_proxy(close_listening))
    _element("conversation-next-button").addEventListener("click", create_proxy(next_conversation_turn))
    _element("conversation-close-button").addEventListener("click", create_proxy(close_conversation))
    _element("builder-undo-button").addEventListener("click", create_proxy(undo_builder_tile))
    _element("builder-next-button").addEventListener("click", create_proxy(next_builder_sentence))
    _element("builder-close-button").addEventListener("click", create_proxy(close_sentence_builder))
    _element("review-marathon-button").addEventListener(
        "click", create_proxy(on_start_marathon_review)
    )
    _element("study-buddy-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_study_buddy)
    )
    _element("review-submit-button").addEventListener(
        "click", create_proxy(on_review_submit_typed)
    )
    _element("review-answer-input").addEventListener(
        "keydown", create_proxy(on_review_answer_keydown)
    )
    _element("review-next-button").addEventListener("click", create_proxy(next_review_question))
    _element("review-close-button").addEventListener("click", create_proxy(close_review))
    _element("proficiency-submit-button").addEventListener(
        "click", create_proxy(on_proficiency_submit_typed)
    )
    _element("proficiency-answer-input").addEventListener(
        "keydown", create_proxy(on_proficiency_answer_keydown)
    )
    _element("proficiency-next-button").addEventListener(
        "click", create_proxy(next_proficiency_question)
    )
    _element("proficiency-close-button").addEventListener(
        "click", create_proxy(close_proficiency_test)
    )
    _element("liaison-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_liaison_drill)
    )
    _element("liaison-next-button").addEventListener(
        "click", create_proxy(next_liaison_question)
    )
    _element("liaison-close-button").addEventListener(
        "click", create_proxy(close_liaison_drill)
    )
    _element("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    _element("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    _element("legend-toggle-button").addEventListener("click", create_proxy(on_toggle_legend))
    _element("farm-legend-button").addEventListener("click", create_proxy(on_toggle_legend))
    _element("report-log-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_report_log)
    )
    # Explicit, not just relying on index.html's `hidden` attribute -- the
    # toast element is only otherwise touched by show_achievement_toast()
    # (unlike every *panel*, which gets its `hidden` state re-set on every
    # render()), so it needs its own starting state set here.
    _element("achievement-toast").hidden = True
    _element("bonus-order-continue-button").addEventListener(
        "click", create_proxy(advance_from_order)
    )
    _element("bonus-tile-submit-button").addEventListener(
        "click", create_proxy(on_bonus_tile_submit_typed)
    )
    _element("bonus-tile-answer-input").addEventListener(
        "keydown", create_proxy(on_bonus_tile_answer_keydown)
    )
    _element("bonus-tile-next-button").addEventListener("click", create_proxy(next_bonus_tile))
    _element("bonus-sentence-submit-button").addEventListener(
        "click", create_proxy(on_bonus_sentence_submit_typed)
    )
    _element("bonus-sentence-answer-input").addEventListener(
        "keydown", create_proxy(on_bonus_sentence_answer_keydown)
    )
    _element("bonus-sentence-next-button").addEventListener(
        "click", create_proxy(next_bonus_sentence)
    )
    _element("bonus-close-button").addEventListener("click", create_proxy(close_bonus_section))

    # Milestone 26: report buttons, extended from the main practice panel
    # into Review, Proficiency, and Bonus's tile/sentence tasks.
    _element("review-report-button").addEventListener("click", create_proxy(submit_review_report))
    _element("review-pronunciation-report-button").addEventListener(
        "click", create_proxy(submit_review_pronunciation_report)
    )
    _element("proficiency-report-button").addEventListener(
        "click", create_proxy(submit_proficiency_report)
    )
    _element("proficiency-pronunciation-report-button").addEventListener(
        "click", create_proxy(submit_proficiency_pronunciation_report)
    )
    _element("bonus-tile-report-button").addEventListener(
        "click", create_proxy(submit_bonus_tile_report)
    )
    _element("bonus-tile-pronunciation-report-button").addEventListener(
        "click", create_proxy(submit_bonus_tile_pronunciation_report)
    )
    _element("bonus-sentence-report-button").addEventListener(
        "click", create_proxy(submit_bonus_sentence_report)
    )
    _element("bonus-sentence-pronunciation-report-button").addEventListener(
        "click", create_proxy(submit_bonus_sentence_pronunciation_report)
    )

    # Milestones 27-30: the arcade minigame family -- hand in the live farm
    # plus the two question-generation functions every minigame reuses, then
    # let minigames.py wire its own DOM listeners entirely on its own (see
    # that module's docstring for why it stays fully self-contained).
    minigames.configure(
        state,
        generate_question,
        variants_for,
        record_practice,
        credit_plot_fn=credit_game_plot_id,
        credit_item_fn=credit_game_item,
        credit_reset_fn=reset_growth_credit,
        credit_text_fn=growth_credit_text,
        plot_for_fr_fn=plot_for_fr,
        pref_get_fn=pref_get,
        pref_set_fn=pref_set,
        check_answer_fn=check_question_answer,
    )
    minigames.configure_speech(speak_french, speech_available)
    minigames.on_amis_loaded = render
    render_growth_markers()
    minigames.setup()

    render()


setup()


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


def _plot_record(plot):
    return {
        "ease_factor": plot.ease_factor,
        "interval_days": plot.interval_days,
        "last_reviewed": plot.last_reviewed,
        "next_due": plot.next_due,
        "correct_streak": plot.correct_streak,
        "stage": plot.stage,
        "in_weeds": plot.in_weeds,
        # L-18: only written while a plot is on a losing run, so a normal
        # save is unchanged.
        **({"fail_run": plot.fail_run} if plot.fail_run else {}),
        # 2026-10-08: day of the last full watering, only once there is one.
        **({"last_watered": plot.last_watered} if plot.last_watered is not None else {}),
    }


def _reset_plot(plot):
    plot.ease_factor = DEFAULT_EASE
    plot.interval_days = 0
    plot.last_reviewed = None
    plot.next_due = None
    plot.correct_streak = 0
    plot.stage = STAGE_SEED
    plot.in_weeds = False
    plot.fail_run = 0
    plot.last_watered = None
    plot.nudged_day = None


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
        "error_patterns": dict(error_pattern_counts),
        "practice_ledger": {
            mode: dict(entry) for mode, entry in practice_ledger.items() if entry["total"]
        },
        # Z11 "My Reports" -- only written once something has actually been
        # reported, matching practice_ledger's own "don't bloat an untouched
        # save" rule above.
        **({"report_log": list(report_log)} if report_log else {}),
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) -- always
        # freshly recomputed from the farm above, never read back in
        # load_state(). This is what makes this game's achievements show up
        # on the hub-wide dashboard alongside every other game's.
        "achievements_earned": achievement_ids_earned(),
        # L13 -- opt-in study-buddy preference; only written when on, so
        # the default save is unchanged.
        **({"study_buddy": True} if study_buddy_enabled else {}),
        # L7a -- real calendar days with study activity; only written once
        # something has been studied, like practice_ledger above.
        **({"study_days": dict(study_days)} if study_days else {}),
        # L19 -- saved phrasebook plot ids, only once something is saved.
        **({"phrasebook": list(phrasebook)} if phrasebook else {}),
        # L4b -- highest row the player was placed through, only once non-zero.
        **({"placement_through": placement_through} if placement_through else {}),
        # L-9 -- the exam date and the what-if minutes, only once a date is set.
        **({"exam_plan": {"date": exam_date, "minutes": exam_minutes}} if exam_date else {}),
        # L-17 / L-14 / L-18: today's golden plot and daily goals, and how many
        # stubborn plots have been rested; each written only once it means something.
        **({"golden": dict(golden_plot)} if golden_plot["claimed"] else {}),
        **(
            {"quests": {"day": quest_state["day"], "progress": dict(quest_state["progress"]), "done": list(quest_state["done"])}}
            if quest_state["day"] >= 0 and (quest_state["progress"] or quest_state["done"])
            else {}
        ),
        **({"leech_rests": leech_rests} if leech_rests else {}),
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
    global error_pattern_counts, practice_ledger, study_buddy_enabled, report_log, study_days, phrasebook
    global placement_through, exam_date, exam_minutes, leech_rests

    study_buddy_enabled = data.get("study_buddy") is True

    saved_plots = data.get("plots") or {}
    state.current_day = data.get("current_day", 0)
    state.invalidate_unlocks()
    error_pattern_counts = dict(data.get("error_patterns") or {})
    practice_ledger = _validated_practice_ledger(data.get("practice_ledger"))
    study_days = _validated_study_days(data.get("study_days"))
    phrasebook = _validated_phrasebook(data.get("phrasebook"))
    placement_through = _validated_placement_through(data.get("placement_through"))
    exam_date, exam_minutes = _validated_exam_plan(data.get("exam_plan"))
    golden_plot.update(_validated_golden(data.get("golden")))
    quest_state.update(_validated_quests(data.get("quests")))
    leech_rests = _validated_leech_rests(data.get("leech_rests"))
    coins_state.update(_validated_coins(data.get("coins")))
    _planner_cache.clear()
    # Z11 "My Reports" -- an old save predating this feature simply has no
    # "report_log" key, which sanitize() already treats as "empty list",
    # the same forward-compatibility standard every other per-game field
    # in this hub's save schemas already holds itself to.
    report_log = narrative_log.sanitize(
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
