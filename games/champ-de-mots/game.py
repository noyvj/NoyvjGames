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

import json
import random
import re
import unicodedata

CATALOG_FILENAME = "fren_combined_catalog.json"

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


def _read_catalog_json():
    """The page's boot script fetches the catalog and hands it to Python as a
    window global (`CATALOG_JSON`) before running this file; the pytest
    harness sets the same attribute on its fake `js` module. A filesystem
    fallback keeps the module importable outside both."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "CATALOG_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CATALOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


CATALOG = json.loads(_read_catalog_json())

CHAPTER_TITLES = {str(c["number"]): c["title"] for c in CATALOG.get("chapters", [])}


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


def schedule_after_review(plot, correct, day):
    """Apply one review outcome to a plot's SRS state (design doc §6)."""
    if correct:
        plot.correct_streak += 1
        if plot.correct_streak == 1:
            plot.interval_days = FIRST_INTERVAL_DAYS
        elif plot.correct_streak == 2:
            plot.interval_days = SECOND_INTERVAL_DAYS
        else:
            plot.interval_days = max(
                plot.interval_days + 1, int(round(plot.interval_days * plot.ease_factor))
            )
        plot.ease_factor = min(MAX_EASE, plot.ease_factor + EASE_CORRECT_BONUS)
    else:
        plot.correct_streak = 0
        plot.interval_days = RESET_INTERVAL_DAYS
        plot.ease_factor = max(MIN_EASE, plot.ease_factor - EASE_INCORRECT_PENALTY)

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
        """§7's pacing gate: a row opens only once every plot in the row before
        it has reached at least Sprout.

        FREN151 (sequence 1-11) is already finished in real life, so those rows
        are a catch-up zone that is open from the start. The gate is expressed
        purely as a growth condition — there is no live "today" in this game,
        and a date-driven release would sit on top of this rule rather than
        replace it.
        """
        if self._unlocked_cache is None:
            self._unlocked_cache = self._compute_unlocked()
        return sequence in self._unlocked_cache

    def _compute_unlocked(self):
        unlocked = set()
        for row in self.rows:
            if row.sequence <= CATCH_UP_MAX_SEQUENCE:
                unlocked.add(row.sequence)
                continue
            previous = self.row_plots(row.sequence - 1)
            if previous and all(
                STAGE_RANK[p.stage] >= STAGE_RANK[STAGE_SPROUT] for p in previous
            ):
                unlocked.add(row.sequence)
        return unlocked

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
    def review(self, plot_id, correct, day=None):
        plot = self.plots_by_id.get(plot_id)
        if plot is None:
            return None
        self.invalidate_unlocks()
        return schedule_after_review(
            plot, correct, self.current_day if day is None else day
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
}

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


def normalize_answer(text):
    """Case-, accent- and punctuation-insensitive form used for comparisons.

    Accents are folded away deliberately: mistyping é as e should never cost
    you a plant. The one place that leniency would defeat the point — the
    phonetic accents topic — is handled by not offering typed variants there.
    """
    text = unicodedata.normalize("NFKD", str(text))
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
    distractors = rng.sample(pool, DISTRACTOR_COUNT)
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
    something a typed answer should have to reproduce."""
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


def answer_alternatives(answer):
    """Everything a typed answer may reasonably be spelled as."""
    alternatives = set()
    raw = str(answer).strip()
    base = strip_parentheticals(raw)
    candidates = {raw, base, _strip_plus_annotation(raw), _strip_plus_annotation(base)}
    pieces = list(candidates)
    for candidate in candidates:
        pieces.extend(re.split(r"\s*/\s*|\s*;\s*", candidate))
    for chunk in pieces:
        chunk = chunk.strip()
        if not chunk:
            continue
        normalized = normalize_answer(chunk)
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


def check_answer(question, given):
    """Multiple choice is exact; typed answers are checked leniently."""
    if question["mode"] == "choice":
        return given == question["answer"]
    typed = normalize_answer(given)
    if not typed:
        return False
    return typed in answer_alternatives(question["answer"])


# ===========================================================================
# Milestone 4 — the static farm grid UI (design doc §3 and §8)
# ===========================================================================
#
# Deliberately static: the farm is a plain grid of cells, one per plot, and a
# growth stage is just a different sprite and class on the cell. No animation,
# nothing that has to be caught mid-motion for a screenshot. The grid is built
# once at boot and only its cells' text/classes are rewritten afterwards —
# 722 cells is too many to recreate on every answer.

from js import document
from pyodide.ffi import create_proxy

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
AUTOMATED_TOOLTIP_NOTE = "auto-watered"
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

# Module-level UI state.
current_question = None
current_result = None
practice_open = False
plot_cells = {}
QUESTION_RNG = random.Random()


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
    _element("legend").innerText = "  ·  ".join(lines)


def _plot_classes(plot):
    classes = ["plot", f"plot--{plot.stage}"]
    if is_wilting(plot, state.current_day):
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

    available = state.available_plots()
    growing = sum(1 for p in available if p.stage != STAGE_SEED)
    automated = sum(1 for p in available if p.stage == STAGE_AUTOMATED)
    _element("progress-display").innerText = (
        f"{growing} of {len(state.plots)} plots growing · {automated} automated"
    )

    unlocked = sum(1 for r in state.rows if state.is_row_unlocked(r.sequence))
    _element("row-summary-display").innerText = f"{unlocked} of {len(state.rows)} rows open"

    water_next = _element("water-next-button")
    water_next.disabled = not due
    water_next.innerText = "Water the next plot" if due else "All watered"


def render_practice():
    panel = _element("practice-panel")
    choices_box = _element("practice-choices")
    answer_input = _element("practice-answer-input")
    submit = _element("practice-submit-button")

    if not practice_open or current_question is None:
        panel.hidden = True
        choices_box.innerHTML = ""
        return

    panel.hidden = False
    _element("practice-context").innerText = current_question["context"]
    _element("practice-instruction").innerText = current_question["instruction"]
    _element("practice-prompt").innerText = current_question["prompt"]

    note = _element("practice-note")
    note.innerText = current_question["note"] or ""
    note.hidden = not current_question["note"]

    answered = current_result is not None
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
            button.addEventListener("click", create_proxy(_make_choice_handler(choice)))
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


def render():
    render_farm()
    render_status()
    render_practice()


# --- interactions ----------------------------------------------------------


def open_practice(plot_id, variant=None):
    """Water a plot: roll a fresh question for it (§5) and show the panel."""
    global current_question, current_result, practice_open

    plot = state.plots_by_id.get(plot_id)
    if plot is None or not state.is_row_unlocked(plot.sequence):
        return None

    current_question = generate_question(
        plot, QUESTION_RNG, variant=variant, exclude=getattr(plot, "last_variant", None)
    )
    plot.last_variant = current_question["variant"]
    current_result = None
    practice_open = True
    _element("practice-answer-input").value = ""
    render()
    return current_question


def submit_answer(given):
    global current_result

    if current_question is None or current_result is not None:
        return None
    current_result = check_answer(current_question, given)
    state.review(current_question["plot_id"], current_result)
    render()
    return current_result


def close_practice(event=None):
    global current_question, current_result, practice_open

    current_question = None
    current_result = None
    practice_open = False
    render()


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


def on_next_day(event=None):
    state.advance_day()
    render()


def setup():
    build_farm()
    render_legend()
    _element("practice-submit-button").addEventListener("click", create_proxy(on_submit_typed))
    _element("practice-answer-input").addEventListener("keydown", create_proxy(on_answer_keydown))
    _element("practice-close-button").addEventListener("click", create_proxy(close_practice))
    _element("water-next-button").addEventListener("click", create_proxy(on_water_next))
    _element("next-day-button").addEventListener("click", create_proxy(on_next_day))
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
    }


def _reset_plot(plot):
    plot.ease_factor = DEFAULT_EASE
    plot.interval_days = 0
    plot.last_reviewed = None
    plot.next_due = None
    plot.correct_streak = 0
    plot.stage = STAGE_SEED


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
    }


def load_state(data):
    saved_plots = data.get("plots") or {}
    state.current_day = data.get("current_day", 0)
    state.invalidate_unlocks()

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

    # Any question on screen was generated against the farm that just got
    # replaced, so it is closed rather than answered into the new one.
    close_practice()
    return True
