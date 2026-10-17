"""generate_question(): turns a plot and a question kind into the prompt, choices and answer a player sees, plus the progressive
choice-versus-typed schedule (wants_typed).
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random
import re
import zlib

import champ_runstate as runstate
from champ_rules import DEFAULT_EASE, STAGE_AUTOMATED, STAGE_BLOOMING, STAGE_BUDDING, STAGE_SEED, STAGE_SPROUT
from champ_model import state
from champ_qbuild import (
    BLANK_MARKER, INSTRUCTIONS, V_BLANK_ENDING, V_BLANK_WORD, V_CONJUGATION_SWAP, V_EN_FR_CHOICE,
    V_EN_FR_TYPED, V_EXAMPLE_EN_FR, V_EXAMPLE_FR_EN, V_FR_EN_CHOICE, V_FR_EN_TYPED, V_GENDER_TAG,
    V_NAME_SYMBOL_CHOICE, V_NAME_SYMBOL_TYPED, V_SYMBOL_NAME_CHOICE, V_SYMBOL_NAME_TYPED, _choice_question,
    _context_line, _ending_pool, _ending_split, _enough, _form_pool, _raw_pool, _target_pool, _typable_items,
    _typed_question, blank_target, conjugation_forms, gender_tag_parts, split_pronoun, variants_for,
)


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
    if runstate.ALWAYS_MULTIPLE_CHOICE or plot.stage == STAGE_SEED or plot.last_reviewed is None:
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
