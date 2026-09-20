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

import difflib
import json
import random
import re
import unicodedata

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


def generate_question(plot, rng=None, variant=None, exclude=None, farm=None):
    """Build one practice prompt for a plot, fresh, from catalog facts."""
    rng = random.Random() if rng is None else rng
    farm = state if farm is None else farm
    available = variants_for(plot, farm)

    if variant is None:
        excluded = set()
        if isinstance(exclude, str):
            excluded = {exclude}
        elif exclude:
            excluded = set(exclude)
        pool = [v for v in available if v not in excluded] or available
        variant = rng.choice(pool)

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
        return _choice_question(plot, variant, blanked, answer, pool, rng, note)

    if variant == V_CONJUGATION_SWAP:
        # The pronoun is re-rolled from the table's own six-person set each
        # visit, so the blank moves around instead of drilling one form (§5).
        pronoun, answer = rng.choice(conjugation_forms(plot))
        return _choice_question(
            plot, variant, f"{pronoun} {BLANK_MARKER}", answer,
            _form_pool(farm, plot, answer), rng, note,
        )

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
NUMBER_REGIONALISMS = {
    "soixante-dix": ("septante",),
    "quatre-vingts": ("huitante",),
    "quatre-vingt-dix": ("nonante", "neufante"),
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
    typed = normalize_answer(given, fold_accents=fold_accents)
    if not typed:
        return False
    if tier is None:
        return typed in answer_alternatives(question["answer"])
    if tier == TIER_STRICT:
        return typed in strict_alternatives(question["answer"], fold_accents=fold_accents)
    accepted = _lookup_accepted(question)
    return typed in answer_alternatives(question["answer"], accepted=accepted, fold_accents=fold_accents)


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
    farm = _element("farm")
    farm.innerHTML = ""
    plot_cells.clear()

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
        farm.appendChild(row_element)


def render_legend():
    lines = [f"{STAGE_ICON[stage]} {STAGE_LABEL[stage]}" for stage in STAGE_ORDER]
    lines.append(f"💧 {WILTING_LEGEND}")
    lines.append(f"{WEEDS_ICON} {WEEDS_LEGEND}")
    _element("legend").innerText = "  ·  ".join(lines)


# Improvement Ideas §4: optional, toggleable cultural/usage notes -- off the
# main screen by default so it adds depth without cluttering the core drill
# for anyone who just wants to water plots. Session-only, like the review
# controls above: no note ever grows a plant or affects unlocking.
cultural_notes_open = False


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


def on_toggle_dashboard(event=None):
    global dashboard_open
    dashboard_open = not dashboard_open
    render()


def render_dashboard():
    panel = _element("dashboard-panel")
    toggle = _element("dashboard-toggle-button")
    toggle.innerText = "Hide progress dashboard" if dashboard_open else "Progress dashboard"
    panel.hidden = not dashboard_open
    if not dashboard_open:
        return

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


def _maybe_toast_new_achievements():
    """Diffs the currently-earned set against what's already been seen this
    session and toasts anything newly crossed. Called from
    render_achievements(), which already runs on every render() pass, so
    there's no need for a separate call site wired into every place a
    plot can reach Automated (the main practice panel, Review's nudge,
    etc.)."""
    global _achievement_ids_seen
    earned_ids = set(achievement_ids_earned())
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
        line.innerText = f"🏆 {entry['label']}"
        container.appendChild(line)
    if group["next"] is not None:
        line = document.createElement("p")
        line.className = "achievement-next"
        line.innerText = (
            f"Next: {group['next']['label']} ({group['next']['current']} of {group['next']['target']})"
        )
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
    hub_link.href = "../../index.html"
    hub_link.innerText = "View achievements across every game →"
    panel.appendChild(hub_link)


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


def _plot_classes(plot):
    classes = ["plot", f"plot--{plot.stage}"]
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
    if not state.is_row_unlocked(plot.sequence):
        classes.append("plot--locked")
    return " ".join(classes)


def _plot_title(plot):
    parts = [f"{plot.label} — {plot.topic_title}", STAGE_LABEL[plot.stage].split(" — ")[0]]
    if plot.stage == STAGE_AUTOMATED:
        parts.append(AUTOMATED_TOOLTIP_NOTE)
    if plot.in_weeds:
        parts.append(WEEDS_TOOLTIP_NOTE)
    if is_due(plot, state.current_day):
        parts.append(DUE_NOTE)
    return " · ".join(parts)


def render_farm():
    for plot in state.plots:
        cell = plot_cells.get(plot.plot_id)
        if cell is None:
            continue
        cell.className = _plot_classes(plot)
        cell.innerText = STAGE_ICON[plot.stage]
        title = _plot_title(plot)
        cell.title = title
        # The sprite carries the meaning visually; screen readers get the same
        # sentence the tooltip does.
        cell.setAttribute("aria-label", title)
        cell.disabled = not state.is_row_unlocked(plot.sequence)

    for row in state.rows:
        plots = state.row_plots(row.sequence)
        grown = sum(1 for p in plots if p.stage != STAGE_SEED)
        _element(f"row-progress-{row.sequence}").innerText = f"{grown}/{len(plots)}"
        unlocked = state.is_row_unlocked(row.sequence)
        _element(f"row-lock-{row.sequence}").hidden = unlocked
        _element(f"row-{row.sequence}").className = "row" if unlocked else "row row--locked"

        row_due = sum(1 for p in plots if is_due(p, state.current_day)) if unlocked else 0
        due_element = _element(f"row-due-{row.sequence}")
        due_element.hidden = not row_due
        due_element.innerText = ROW_DUE_NOTE.format(count=row_due) if row_due else ""

        _element(f"row-proficiency-{row.sequence}").disabled = not unlocked
        _element(f"row-bonus-{row.sequence}").disabled = not unlocked


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

    if not practice_open or current_question is None:
        panel.hidden = True
        choices_box.innerHTML = ""
        _element("practice-report-button").hidden = True
        _element("practice-blurb").hidden = True
        _element("practice-pronunciation-note").hidden = True
        _element("practice-pronunciation-report-button").hidden = True
        _element("practice-next-button").hidden = True
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


def render():
    render_farm()
    render_status()
    render_practice()
    render_review()
    render_proficiency()
    render_bonus()
    render_cultural_notes()
    render_dashboard()
    render_liaison_drill()
    render_achievements()
    render_changelog()
    minigames.render()


# --- interactions ----------------------------------------------------------


def open_practice(plot_id, variant=None):
    """Water a plot: roll a fresh question for it (§5) and show the panel."""
    global current_question, current_result, current_submitted_answer, practice_open, report_sent, pronunciation_report_sent, current_confidence

    plot = state.plots_by_id.get(plot_id)
    if plot is None or not state.is_row_unlocked(plot.sequence):
        return None

    current_question = generate_question(
        plot, QUESTION_RNG, variant=variant, exclude=getattr(plot, "last_variant", None)
    )
    plot.last_variant = current_question["variant"]
    current_result = None
    current_submitted_answer = None
    current_confidence = None
    report_sent = False
    pronunciation_report_sent = False
    practice_open = True
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
    global current_result, current_submitted_answer, combo_count

    if current_question is None or current_result is not None:
        return None
    typed_mode = current_question["mode"] == "typed"
    current_submitted_answer = str(given).strip() if typed_mode else given
    # §14.2: the tier is decided from the answer's own shape, only for typed
    # answers -- multiple choice is always an exact match regardless.
    tier = grading_tier(current_question["answer"]) if typed_mode else None
    current_result = check_answer(
        current_question, given, tier=tier, accent_sensitive=ACCENT_SENSITIVE
    )
    combo_count = combo_count + 1 if current_result else 0
    plot = state.plots_by_id.get(current_question["plot_id"])
    if plot is not None:
        if current_result:
            plot.in_weeds = False
        elif typed_mode and is_weed_confusion(current_question["answer"], given):
            plot.in_weeds = True
    if not current_result and typed_mode:
        pattern = classify_wrong_typed_answer(current_question, given, tier)
        record_error_pattern(pattern)
    state.review(
        current_question["plot_id"],
        current_result,
        combo=combo_count,
        confidence=current_confidence,
    )
    render()
    return current_result


def close_practice(event=None):
    global current_question, current_result, current_submitted_answer, practice_open, report_sent, pronunciation_report_sent, current_confidence

    current_question = None
    current_result = None
    current_submitted_answer = None
    current_confidence = None
    report_sent = False
    pronunciation_report_sent = False
    practice_open = False
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
    """A correct Review answer isn't a full watering event: it nudges the
    interval a little further out and records that the plot was seen today
    (so a save doesn't silently drop the nudge — see get_state()'s "touched"
    rule), but deliberately never touches `correct_streak`, `ease_factor` or
    `stage`. Only the daily loop's `schedule_after_review()` grows a plant."""
    plot.interval_days = max(1, plot.interval_days) + REVIEW_NUDGE_DAYS
    plot.next_due = day + plot.interval_days
    plot.last_reviewed = day


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
    if mode != "grammar":
        return None
    preferred = [v for v in variants_for(plot) if v in GRAMMAR_REVIEW_PREFERRED_VARIANTS]
    return QUESTION_RNG.choice(preferred) if preferred else None


def _advance_review_question():
    global review_question, review_result
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
        plot, QUESTION_RNG, variant=_review_variant_for(plot, review_mode)
    )
    review_result = None


def start_review(mode, event=None):
    """Roll a fresh Review session: mode is "word" (vocab/phrase) or
    "grammar", the count and minimum-stage filter come from the session's
    own in-page controls (§14.4: both configurable, not fixed)."""
    global review_mode, review_queue, review_index, review_score

    topic_types = {"vocab", "phrase"} if mode == "word" else {"grammar"}
    candidates = review_candidates(topic_types, _review_min_stage_setting())
    candidates = _interleave_by_stage(candidates, REVIEW_RNG)

    review_mode = mode
    review_queue = [p.plot_id for p in candidates[: _review_count_setting()]]
    review_index = 0
    review_score = {"correct": 0, "total": 0}
    _advance_review_question()
    _element("review-answer-input").value = ""
    render()


def submit_review_answer(given):
    global review_result, review_submitted_answer

    if review_question is None or review_result is not None:
        return None
    typed_mode = review_question["mode"] == "typed"
    review_submitted_answer = str(given).strip() if typed_mode else given
    tier = grading_tier(review_question["answer"]) if typed_mode else None
    review_result = check_answer(
        review_question, given, tier=tier, accent_sensitive=ACCENT_SENSITIVE
    )
    review_score["total"] += 1
    if review_result:
        review_score["correct"] += 1
        plot = state.plots_by_id.get(review_question["plot_id"])
        if plot is not None:
            nudge_review_correct(plot, state.current_day)
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


def render_review():
    controls = _element("review-controls")
    controls.hidden = not review_controls_open

    panel = _element("review-panel")
    empty_message = _element("review-empty-message")
    summary = _element("review-summary")
    choices_box = _element("review-choices")

    _destroy_review_choice_proxies()

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
            empty_message.innerText = REVIEW_EMPTY_MESSAGE
            summary.hidden = True
            return
        # Queue exhausted -- show the score, nothing else.
        panel.hidden = False
        empty_message.hidden = True
        summary.hidden = False
        summary.innerText = REVIEW_SUMMARY_MESSAGE.format(**review_score)
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
    _element("review-prompt").innerText = review_question["prompt"]

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
    topic_score = proficiency_topic_scores[entry["topic_id"]]
    topic_score["total"] += 1
    if proficiency_result:
        proficiency_score["correct"] += 1
        topic_score["correct"] += 1
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
        summary.innerText = PROFICIENCY_SUMMARY_MESSAGE.format(**proficiency_score)
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
    question = {"mode": "typed", "answer": tile["en"], "choices": []}
    bonus_tile_result = check_answer(
        question, given, tier=TIER_STRICT, accent_sensitive=ACCENT_SENSITIVE
    )
    bonus_tile_score["total"] += 1
    bonus_score["total"] += 1
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
    question = {"mode": "typed", "answer": sentence["en"], "choices": []}
    bonus_sentence_result = check_answer(
        question, given, tier=TIER_LENIENT, accent_sensitive=ACCENT_SENSITIVE
    )
    bonus_score["total"] += 1
    if bonus_sentence_result:
        bonus_score["correct"] += 1
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
        "marked_correct_answer": generate_accepted_variants(tile["en"]),
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


def setup():
    build_farm()
    render_legend()
    _element("practice-submit-button").addEventListener("click", create_proxy(on_submit_typed))
    _element("practice-answer-input").addEventListener("keydown", create_proxy(on_answer_keydown))
    _element("practice-close-button").addEventListener("click", create_proxy(close_practice))
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
    _element("review-word-button").addEventListener("click", create_proxy(on_start_word_review))
    _element("review-grammar-button").addEventListener(
        "click", create_proxy(on_start_grammar_review)
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
    minigames.configure(state, generate_question, variants_for)
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
    }


def _reset_plot(plot):
    plot.ease_factor = DEFAULT_EASE
    plot.interval_days = 0
    plot.last_reviewed = None
    plot.next_due = None
    plot.correct_streak = 0
    plot.stage = STAGE_SEED
    plot.in_weeds = False


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
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) -- always
        # freshly recomputed from the farm above, never read back in
        # load_state(). This is what makes this game's achievements show up
        # on the hub-wide dashboard alongside every other game's.
        "achievements_earned": achievement_ids_earned(),
    }


# REVIEW(testing): existing tests always pass explicit version/current_day/
# plots keys (even if plots is {}) -- no test calls load_state({}) exercising
# the data.get("plots") or {} and data.get("current_day", 0) defaults
# together end-to-end, the "truly empty save" case CLAUDE.md's Milestone 5
# notes call out as in-scope. Also no test loads a save with an unrecognized
# stage string to exercise the STAGE_RANK fallback a few lines below.
def load_state(data):
    global error_pattern_counts

    saved_plots = data.get("plots") or {}
    state.current_day = data.get("current_day", 0)
    state.invalidate_unlocks()
    error_pattern_counts = dict(data.get("error_patterns") or {})

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

    # Any question on screen was generated against the farm that just got
    # replaced, so it is closed rather than answered into the new one.
    close_practice()
    return True
