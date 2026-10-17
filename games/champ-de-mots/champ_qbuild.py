"""Building questions: normalising answers, blanking a word, finding look-alike distractors, the pools they come from and
variants_for() (which kinds of question a plot offers).
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import difflib
import re
import unicodedata

from champ_rules import STAGE_BUDDING, STAGE_RANK
from champ_model import state


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
