"""Grading: the accepted spellings of an answer, strict and lenient tiers, the weeds look-alike table, the error-pattern digest
and check_answer().
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import re

import champ_runstate as runstate
from champ_model import state
from champ_qbuild import (
    ARTICLE_PREFIXES, TRAILING_PUNCTUATION, V_EXAMPLE_FR_EN, V_FR_EN_TYPED, V_GENDER_TAG, _answer_similarity,
    normalize_answer, strip_parentheticals,
)
from champ_questions import _strip_plus_annotation


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
    return check_answer(question, given, tier=tier, accent_sensitive=runstate.ACCENT_SENSITIVE)


def record_error_pattern(pattern):
    runstate.error_pattern_counts[pattern] = runstate.error_pattern_counts.get(pattern, 0) + 1


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
