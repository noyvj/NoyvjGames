"""Answer-report review, 2026-10-08: the owner noticed that many of the 50
unresolved live answer reports were not about French at all but about odd
ENGLISH sides of the catalog (meta text in a gloss, UK/US spellings, missing
synonyms, slash and hyphen conventions, spelled-out numbers, ...).

Every outcome is recorded in tests/report_review.json. This file pins the
data fixes made in fren_combined_catalog.json:

* LIVE tests run the exact path a typed answer takes in play
  (grading_tier() -> check_answer(..., tier=...)) against the real catalog
  item, so they fail if the data regresses.
* STRICT-tier tests: a one-word answer is graded STRICT, and STRICT today
  ignores a curated accepted_en/accepted_fr array (see report_review.json,
  outcome "needs-code"). For those the data assertion always runs and the
  live assertion is an xfail (non-strict) that flips to a pass as soon as
  check_answer() lets the STRICT tier consult the curated array.
* Hygiene tests keep the whole catalog free of the classes of oddity that
  were swept (revision notes in an answer, duplicate or blank accepted
  entries, digit glosses without their spelled-out forms, ...).
"""

import json
import re
from pathlib import Path

import pytest

REVIEW_PATH = Path(__file__).resolve().parent / "report_review.json"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _topic(module, topic_id):
    for week in module.CATALOG["weeks"]:
        for topic in week["topics"]:
            if topic["id"] == topic_id:
                return topic
    raise AssertionError(f"topic not found: {topic_id}")


def _item(module, topic_id, idx):
    return _topic(module, topic_id)["items"][idx]


def _plot_id(module, topic_id, idx):
    topic = _topic(module, topic_id)
    return topic_id if topic["topic_type"] == "grammar" else f"{topic_id}-i{idx:02d}"


def _live(module, topic_id, idx, field, typed, accent_sensitive=True):
    """The real typed-answer path: tier chosen from the canonical answer,
    curated array looked up through the plot id."""
    item = _item(module, topic_id, idx)
    question = {
        "mode": "typed",
        "answer": item[field],
        "choices": [],
        "plot_id": _plot_id(module, topic_id, idx),
        "topic_type": _topic(module, topic_id)["topic_type"],
    }
    tier = module.grading_tier(item[field])
    return module.check_answer(question, typed, tier=tier, accent_sensitive=accent_sensitive)


def _tier(module, topic_id, idx, field):
    return module.grading_tier(_item(module, topic_id, idx)[field])


def _in_array(module, topic_id, idx, field, typed):
    item = _item(module, topic_id, idx)
    target = module.normalize_answer(typed)
    candidates = [item[field]] + list(item.get(f"accepted_{field}", []))
    return any(module.normalize_answer(c) == target for c in candidates)


# --------------------------------------------------------------------------
# live: LENIENT-tier fixes (work today)
# --------------------------------------------------------------------------
LIVE_CASES = [
    # the reports
    ("fren151-w10-grammar001", 1, "en", "a Little"),                         # un peu
    ("fren151-w10-grammar001", 1, "en", "a little bit"),
    ("fren151-w10-grammar-slide001", 3, "fr", "Mon frère est à Paris"),
    ("fren151-w10-grammar-slide001", 3, "fr", "mon frère il est à paris"),
    ("fren152-w2-phrase001", 1, "en", "it is 4:40 pm"),
    ("fren152-w2-phrase001", 1, "en", "It's 4:40pm"),
    ("fren152-w2-phrase001", 1, "en", "It's 4:40 p.m."),
    ("fren152-w2-phrase001", 1, "en", "It's twenty to five"),
    ("fren152-w2-grammar002", 0, "en", "I finish / you finish / he finishes"),
    ("fren152-w2-grammar002", 1, "en", "we finish / you finish / they finish"),
    ("fren152-w2-grammar002", 2, "en", "I sell / you sell / he sells"),
    ("fren152-w2-grammar002", 3, "en", "we sell, you sell, they sell"),
    ("fren152-w2-grammar001", 0, "fr", "mille neuf cent nonante-deux"),
    ("fren152-w2-grammar001", 1, "fr", "dix-neuf cent nonante deux"),
    ("fren152-w2-grammar001", 1, "fr", "dix neuf cent quatre vingt douze"),
    ("fren152-w2-vocab001", 0, "en", "0 to 60"),
    ("fren152-w2-vocab001", 0, "en", "zero to sixty"),
    ("fren151-w4-grammar001", 0, "en", "a gift for Henry"),
    ("fren151-w4-grammar001", 0, "en", "a present for Henry"),
    ("fren151-w4-vocab001", 6, "en", "for my c.v."),
    ("fren151-w4-vocab001", 6, "en", "for my resume"),
    ("fren151-w4-vocab001", 6, "fr", "pour le CV"),
    ("fren151-w1-vocab001", 2, "en", "hi"),
    ("fren151-w1-vocab001", 2, "en", "bye"),
    ("fren151-w1-vocab001", 2, "en", "hi and bye"),
    ("fren151-w4-vocab-slide001", 11, "fr", "la psychologie"),
    ("fren151-w4-vocab-slide001", 11, "fr", "la psycho"),
    ("fren151-w4-vocab-slide001", 12, "fr", "la philosophie"),
    ("fren151-w1-phrase001", 3, "en", "how is it spelled"),
    ("fren151-w1-phrase001", 3, "en", "How do you spell that"),
    ("fren151-w5-grammar003", 1, "en", "I don't like math"),
    ("fren151-w3-phrase002", 0, "fr", "j'ai envie de"),
    ("fren151-w3-phrase002", 0, "fr", "J'ai envie d'une"),
    ("fren151-w3-phrase002", 1, "fr", "j'ai besoin de"),
    ("fren151-w3-vocab002", 3, "fr", "livres"),
    ("fren151-w11-vocab001", 0, "fr", "yeux bleus"),
    ("fren151-w1-vocab003", 7, "en", "What is the right answer"),
    # UK / US spellings and vocabulary (LENIENT items)
    ("fren151-w7-vocab001", 15, "en", "a theater"),
    ("fren151-w7-vocab001", 16, "en", "a movie theater"),
    ("fren151-w7-vocab001", 24, "en", "a car park"),
    ("fren151-w7-vocab001", 24, "en", "a parking lot"),
    ("fren151-w7-grammar001", 0, "en", "There is a theater"),
    ("fren151-w7-grammar001", 1, "en", "There isn't a theater"),
    ("fren152-w4-vocab001", 5, "en", "I watch my favorite series"),
    ("fren152-w4-vocab001", 5, "en", "I watch my favourite show"),
    ("fren152-w13-vocab001", 2, "en", "I have already traveled overseas"),
    ("fren152-w13-vocab001", 2, "en", "I've already travelled abroad"),
    ("fren151-w9-vocab004", 3, "en", "to watch a movie"),
    ("fren152-w10-grammar004", 0, "en", "a tin of"),
    ("fren152-w10-grammar004", 0, "en", "a box of"),
    ("fren152-w10-grammar004", 0, "en", "a can of"),
    ("fren152-w10-grammar004", 3, "en", "a jar of"),
    ("fren152-w10-grammar004", 1, "en", "a pack of"),
    ("fren152-w10-grammar004", 6, "en", "a liter of / half a liter of"),
    ("fren152-w6-grammar003", 0, "en", "this sweater"),
    ("fren152-w6-vocab001", 7, "en", "a sweater"),
    # word-level slash alternatives (each full alternative on its own)
    ("fren151-w2-grammar003", 2, "en", "he speaks"),
    ("fren151-w2-grammar003", 2, "en", "one speaks"),
    ("fren151-w2-grammar003", 2, "fr", "elle parle"),
    ("fren151-w3-grammar001", 2, "en", "she has"),
    ("fren151-w9-grammar003", 2, "en", "she makes"),
    ("fren151-w9-grammar003", 0, "en", "I make"),
    ("fren151-w9-vocab003", 3, "en", "I play rugby"),
    ("fren151-w10-grammar002", 1, "en", "He seems kind"),
    ("fren151-w9-grammar004", 1, "en", "I love"),
    ("fren151-w2-vocab002", 2, "en", "to love"),
    ("fren151-w4-phrase001", 2, "fr", "Quel est votre métier"),
    ("fren151-w9-phrase001", 2, "fr", "Je suis fille unique"),
    ("fren151-w6-phrase001", 3, "en", "Is it close"),
    ("fren151-w6-phrase001", 3, "fr", "C'est près"),
    ("fren152-w4-grammar001", 2, "en", "I go out / you go out / he goes out"),
    ("fren152-w6-grammar001", 1, "en", "we put on / you put on / they put on"),
    ("fren152-w8-grammar001", 0, "en", "I want to / you want to / he wants to"),
    ("fren152-w10-grammar002", 2, "en", "I drink / you drink / he drinks"),
    ("fren152-w12-grammar002", 1, "en", "we know / you know / they know"),
    ("fren152-w11-phrase001", 3, "en", "I'd like a medium steak"),
    ("fren152-w11-phrase001", 3, "fr", "Je voudrais un steak à point"),
    ("fren152-w11-grammar001", 0, "en", "I have spoken"),
    ("fren152-w11-grammar001", 2, "en", "she has sold"),
    ("fren151-w1-grammar001", 5, "en", "an eraser"),
    ("fren152-w4-grammar003", 0, "fr", "la plus"),
    # optional-suffix forms (LENIENT items): both the bare and the full form
    ("fren151-w8-vocab001", 5, "fr", "bien desservie"),
    ("fren152-w13-grammar002", 0, "fr", "je me suis lavée"),
    ("fren151-w2-phrase002", 2, "fr", "Je suis australienne d'origine libanaise"),
    ("fren151-w4-vocab001", 5, "fr", "pour parler avec des amies"),
    # plural nouns without the article (LENIENT items)
    ("fren151-w9-vocab001", 0, "fr", "parents"),
    ("fren152-w6-vocab001", 4, "fr", "chaussures"),
    ("fren152-w6-vocab001", 23, "fr", "lunettes de soleil"),
    ("fren152-w9-vocab003", 16, "fr", "frites"),
    ("fren151-w1-phon002", 0, "en", "acute accent"),
    ("fren151-w1-phon002", 2, "en", "circumflex"),
    ("fren151-w9-vocab001", 7, "fr", "grands-parents"),
    # earlier triage stays working
    ("fren151-w1-vocab003", 6, "en", "listen closely"),
    ("fren151-w1-vocab003", 4, "en", "all together"),
    ("fren151-w7-vocab001", 21, "en", "a store"),
    ("fren151-w4-phrase002", 0, "en", "I work part time"),
    ("fren151-w3-phrase001", 1, "fr", "quel âge avez vous"),
    ("fren151-w9-grammar002", 0, "en", "the cat of the pharmacist"),
    ("fren151-w7-vocab001", 20, "en", "a shopping center"),
]


@pytest.mark.parametrize("topic_id,idx,field,typed", LIVE_CASES)
def test_live_typed_answer_is_accepted(game_env, topic_id, idx, field, typed):
    module = game_env.module
    assert _live(module, topic_id, idx, field, typed), (
        f"{topic_id} #{idx} [{field}] should accept {typed!r}"
    )


# --------------------------------------------------------------------------
# STRICT-tier fixes: data always present, live acceptance needs the game.py
# rule "STRICT consults the item's curated accepted_* array"
# --------------------------------------------------------------------------
STRICT_CASES = [
    ("fren151-w10-vocab001", 9, "en", "The cinema"),
    ("fren151-w10-vocab001", 9, "en", "the movies"),
    ("fren151-w4-vocab003", 9, "fr", "informatique"),
    ("fren151-w4-vocab-slide001", 2, "fr", "informatique"),
    ("fren151-w1-phon002", 3, "en", "accent tréma"),
    ("fren151-w1-phon002", 3, "en", "diaeresis"),
    ("fren151-w1-phon002", 4, "en", "cedilla"),
    ("fren151-w11-vocab-slide001", 1, "en", "thin"),
    ("fren151-w4-vocab-slide001", 9, "en", "math"),
    ("fren151-w10-vocab003", 0, "en", "nice"),
    ("fren151-w9-vocab001", 7, "en", "grand parents"),
    ("fren151-w4-vocab002", 6, "en", "server"),
    ("fren151-w4-vocab002", 6, "en", "waiter"),
    ("fren151-w4-vocab002", 9, "en", "teacher"),
    ("fren151-w2-phrase001", 4, "en", "so so"),
    ("fren151-w10-vocab001", 11, "en", "theater"),
    ("fren151-w9-vocab002", 5, "en", "neighbor"),
    ("fren152-w6-vocab002", 10, "en", "gray"),
    ("fren152-w6-vocab001", 2, "en", "pants"),
    ("fren152-w6-vocab001", 6, "en", "sneakers"),
    ("fren152-w9-vocab001", 4, "en", "yogurt"),
    ("fren152-w5-vocab001", 13, "en", "fall"),
    ("fren152-w8-vocab001", 5, "en", "sunblock"),
    ("fren152-w8-vocab001", 3, "en", "flip flops"),
    ("fren151-w1-vocab002", 20, "en", "twenty"),
    ("fren151-w2-vocab001", 8, "en", "ninety"),
    ("fren151-w5-vocab-slide001", 0, "en", "seventy"),
    ("fren152-w2-vocab002", 1, "en", "one thousand"),
    ("fren152-w2-vocab002", 3, "en", "a billion"),
    ("fren152-w12-grammar001", 1, "en", "drunk"),
    ("fren152-w12-grammar001", 16, "en", "seen"),
    ("fren151-w10-vocab001", 6, "en", "football"),
    ("fren151-w9-vocab001", 5, "en", "kids"),
    ("fren151-w9-vocab002", 6, "en", "roommate"),
    ("fren151-w8-vocab001", 9, "en", "calm"),
    ("fren151-w5-vocab001", 0, "fr", "Australie"),
    ("fren151-w8-vocab001", 11, "fr", "culturelle"),
    ("fren151-w10-vocab003", 0, "fr", "gentille"),
    ("fren151-w10-vocab003", 1, "fr", "intelligente"),
    ("fren152-w4-vocab002", 2, "fr", "intellectuelle"),
    ("fren151-w8-vocab001", 17, "fr", "chère"),
    ("fren152-w7-vocab002", 1, "en", "high heeled"),
    ("fren152-w6-vocab001", 20, "en", "bathing suit"),
    ("fren152-w8-vocab001", 0, "en", "swimsuit"),
    ("fren152-w6-vocab001", 21, "en", "pajamas"),
    ("fren151-w6-vocab001", 0, "en", "to the left"),
    ("fren151-w6-vocab001", 1, "en", "on the right"),
    ("fren151-w6-vocab002", 0, "en", "small river"),
]


@pytest.mark.parametrize("topic_id,idx,field,typed", STRICT_CASES)
def test_strict_item_curated_array_has_the_variant(game_env, topic_id, idx, field, typed):
    module = game_env.module
    assert _in_array(module, topic_id, idx, field, typed), (
        f"{topic_id} #{idx} accepted_{field} is missing {typed!r}"
    )


@pytest.mark.xfail(
    reason="needs game.py: the STRICT tier in check_answer() must consult the item's curated "
    "accepted_en/accepted_fr (see tests/report_review.json, outcome needs-code)",
    strict=False,
)
@pytest.mark.parametrize("topic_id,idx,field,typed", STRICT_CASES)
def test_strict_item_variant_is_accepted_live(game_env, topic_id, idx, field, typed):
    module = game_env.module
    assert _live(module, topic_id, idx, field, typed)


# --------------------------------------------------------------------------
# rejected on purpose: these reports were judged genuinely wrong
# --------------------------------------------------------------------------
REJECTED = [
    ("fren151-w2-phrase001", 5, "fr", "et tu"),               # "tu" is not an object pronoun
    ("fren151-w2-phrase001", 5, "fr", "et tu / et vous"),
    ("fren151-w1-vocab003", 7, "en", "what is the answer"),    # drops "correct"/"bonne"
    ("fren152-w2-phrase001", 3, "en", "12:00"),                # midi/minuit are words, not a time
    ("fren152-w2-phrase001", 0, "en", "what hour is it"),      # calque, not English
    ("fren151-w9-vocab001", 18, "en", "older sibling"),        # loses the brother/sister pair
    ("fren151-w1-vocab001", 0, "en", "definitely-not-the-answer"),
    ("fren151-w1-vocab002", 20, "en", "twenty one"),            # accepted number words must be the right number
    ("fren151-w7-vocab001", 20, "en", "a shopping"),
]


@pytest.mark.parametrize("topic_id,idx,field,typed", REJECTED)
def test_wrong_answers_stay_wrong(game_env, topic_id, idx, field, typed):
    module = game_env.module
    assert not _live(module, topic_id, idx, field, typed)
    assert not _in_array(module, topic_id, idx, field, typed)


# --------------------------------------------------------------------------
# spelling pairs: both the UK and the US form are accepted (data level; live
# for the LENIENT items above)
# --------------------------------------------------------------------------
SPELLING_PAIRS = [
    ("fren151-w10-vocab001", 11, "theatre", "theater"),
    ("fren151-w7-vocab001", 15, "a theatre", "a theater"),
    ("fren151-w7-grammar001", 0, "There is a theatre.", "There is a theater."),
    ("fren151-w7-vocab001", 20, "a shopping centre", "a shopping center"),
    ("fren151-w9-vocab002", 5, "neighbour", "neighbor"),
    ("fren152-w4-vocab001", 5, "I watch my favourite series", "I watch my favorite series"),
    ("fren152-w6-vocab002", 10, "grey", "gray"),
    ("fren152-w6-vocab001", 21, "pyjamas", "pajamas"),
    ("fren152-w9-vocab001", 4, "yoghurt", "yogurt"),
    ("fren152-w10-grammar004", 6, "a litre of", "a liter of"),
    ("fren152-w13-vocab001", 2, "I have already travelled overseas.", "I have already traveled overseas."),
    ("fren152-w7-vocab001", 0, "woollen", "woolen"),
    ("fren152-w7-vocab002", 7, "checked", "checkered"),
    ("fren151-w4-vocab-slide001", 9, "maths", "math"),
    ("fren151-w1-phrase001", 3, "How is that spelt?", "How is that spelled?"),
]


@pytest.mark.parametrize("topic_id,idx,uk,us", SPELLING_PAIRS)
def test_both_spellings_are_accepted(game_env, topic_id, idx, uk, us):
    module = game_env.module
    assert _in_array(module, topic_id, idx, "en", uk)
    assert _in_array(module, topic_id, idx, "en", us)


# --------------------------------------------------------------------------
# meta text in answers
# --------------------------------------------------------------------------
def test_no_answer_carries_revision_or_course_notes(game_env):
    module = game_env.module
    for week in module.CATALOG["weeks"]:
        for topic in week["topics"]:
            for item in topic["items"]:
                for field in ("fr", "en"):
                    text = item[field]
                    assert "revision from" not in text.lower(), (topic["id"], text)
                    assert "FREN1" not in text, (topic["id"], text)


def test_zero_to_sixty_is_a_clean_gloss(game_env):
    item = _item(game_env.module, "fren152-w2-vocab001", 0)
    assert item["en"] == "0 to 60"
    assert item["fr"] == "zéro à soixante"


# The one remaining em dash outside brackets is a dialogue pair (question - reply).
ALLOWED_EM_DASH = {("fren152-w7-phrase-slide001", 5)}


def test_no_explanatory_dash_text_outside_brackets_in_an_answer(game_env):
    module = game_env.module
    for week in module.CATALOG["weeks"]:
        for topic in week["topics"]:
            for idx, item in enumerate(topic["items"]):
                outside = re.sub(r"\([^)]*\)", "", item["en"])
                if (topic["id"], idx) in ALLOWED_EM_DASH:
                    continue
                assert "—" not in outside, (topic["id"], idx, item["en"])


def test_hints_were_moved_into_brackets_not_deleted(game_env):
    module = game_env.module
    assert _item(module, "fren151-w7-grammar004", 0)["en"] == "to go to (masc.) (à + le)"
    assert _item(module, "fren151-w7-grammar004", 2)["en"] == "to go to (plural) (à + les)"
    assert _live(module, "fren151-w7-grammar004", 0, "en", "to go to")
    assert _live(module, "fren151-w7-grammar004", 2, "en", "to go to")
    loyal = _item(module, "fren151-w10-grammar-slide002", 6)["en"]
    assert loyal.startswith("loyal (") and "-al" in loyal


# --------------------------------------------------------------------------
# accepted-array hygiene across the whole catalog
# --------------------------------------------------------------------------
def _all_items(module):
    for week in module.CATALOG["weeks"]:
        for topic in week["topics"]:
            for idx, item in enumerate(topic["items"]):
                yield topic, idx, item


def test_curated_arrays_are_clean(game_env):
    module = game_env.module
    count = 0
    for topic, idx, item in _all_items(module):
        for field in ("fr", "en"):
            arr = item.get(f"accepted_{field}")
            if arr is None:
                continue
            count += 1
            where = (topic["id"], idx, field)
            assert isinstance(arr, list) and arr, where
            assert all(isinstance(a, str) and a.strip() for a in arr), where
            assert arr[0] == item[field], where           # canonical first
            assert len(arr) == len(set(arr)), where        # no exact duplicates
    assert count > 150    # the sweep really touched the catalog


def test_accepted_keys_only_exist_for_a_real_field(game_env):
    module = game_env.module
    for topic, idx, item in _all_items(module):
        for key in item:
            if key.startswith("accepted"):
                assert key in ("accepted_fr", "accepted_en"), (topic["id"], idx, key)


def test_curated_variants_do_not_collide_with_a_sibling_answer(game_env):
    """An accepted variant must never be the canonical answer of a DIFFERENT
    item in the same topic (the player could then be marked right for the
    wrong word)."""
    module = game_env.module
    allowed = {
        # (topic, normalized variant): both of these are legitimately interchangeable
        ("fren151-w9-vocab001", "grandparents"),
        # mince (slim) and maigre (skinny/thin) overlap in English; the French
        # prompt is never ambiguous, only the English-to-French direction
        # shows the canonical gloss, which stays distinct.
        ("fren151-w11-vocab-slide001", "thin"),
    }
    for topic in (t for w in module.CATALOG["weeks"] for t in w["topics"]):
        for field in ("fr", "en"):
            canon = {}
            for idx, item in enumerate(topic["items"]):
                for alt in module.answer_alternatives(item[field]):
                    canon.setdefault(alt, set()).add(idx)
            for idx, item in enumerate(topic["items"]):
                for extra in item.get(f"accepted_{field}", []):
                    key = module.normalize_answer(extra)
                    others = canon.get(key, set()) - {idx}
                    if others and (topic["id"], key) not in allowed:
                        # grammar topics list several persons/genders with the
                        # same English gloss ("big" x4): identical gloss is fine
                        same_gloss = all(
                            module.normalize_answer(module.strip_parentheticals(topic["items"][o][field]))
                            == module.normalize_answer(module.strip_parentheticals(item[field]))
                            for o in others
                        )
                        assert same_gloss, (topic["id"], idx, field, extra, sorted(others))


# --------------------------------------------------------------------------
# digit glosses accept the spelled-out number
# --------------------------------------------------------------------------
ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
        "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
        "nineteen"]
TENS = {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty", 6: "sixty", 7: "seventy", 8: "eighty", 9: "ninety"}


def _words(n):
    if n < 20:
        return ONES[n]
    if n == 100:
        return "one hundred"
    tens, ones = divmod(n, 10)
    return TENS[tens] + (f"-{ONES[ones]}" if ones else "")


def test_every_digit_gloss_accepts_the_spelled_out_number(game_env):
    module = game_env.module
    seen = 0
    for topic, idx, item in _all_items(module):
        match = re.fullmatch(r"(\d{1,3})(?: \(.*\))?", item["en"])
        if not match:
            continue
        seen += 1
        number = int(match.group(1))
        assert _in_array(module, topic["id"], idx, "en", _words(number)), (topic["id"], idx, item["en"])
        if "-" in _words(number):
            assert _in_array(module, topic["id"], idx, "en", _words(number).replace("-", " ")), item["en"]
    assert seen >= 40


def test_big_numbers_accept_words(game_env):
    module = game_env.module
    assert _in_array(module, "fren152-w2-vocab002", 1, "en", "one thousand")
    assert _in_array(module, "fren152-w2-vocab002", 1, "en", "1000")
    assert _in_array(module, "fren152-w2-vocab002", 2, "en", "one million")
    assert _in_array(module, "fren152-w2-vocab002", 3, "en", "one billion")
    assert _in_array(module, "fren152-w2-grammar001", 2, "en", "two thousand and two")


# --------------------------------------------------------------------------
# same-class sweeps: plural without article, l' elision, optional suffix
# --------------------------------------------------------------------------
def test_plural_nouns_may_drop_des_or_les(game_env):
    module = game_env.module
    checked = 0
    for topic, idx, item in _all_items(module):
        if topic["topic_type"] == "grammar":
            continue
        fr = item["fr"]
        if re.match(r"(des|les) \S", fr) and "/" not in fr and "Unis" not in fr:
            checked += 1
            bare = re.sub(r"^(des|les) ", "", fr)
            assert _in_array(module, topic["id"], idx, "fr", bare), fr
    assert checked >= 35


def test_les_etats_unis_keeps_its_article(game_env):
    module = game_env.module
    item = _item(module, "fren151-w5-vocab001", 11)
    assert item["fr"] == "les États-Unis"
    assert "accepted_fr" not in item


def test_singular_le_la_nouns_still_need_their_article(game_env):
    """Gender is part of the item: dropping le/la is NOT accepted (pending an
    owner decision, see report_review.json: cdf98a34)."""
    module = game_env.module
    assert not _live(module, "fren151-w4-vocab003", 4, "fr", "mode")
    assert not _in_array(module, "fren151-w4-vocab003", 4, "fr", "mode")
    assert not _in_array(module, "fren151-w4-vocab003", 0, "fr", "tourisme")


def test_elided_l_nouns_accept_the_bare_noun(game_env):
    """l' hides the gender, so the bare noun carries the same information."""
    module = game_env.module
    checked = 0
    for topic, idx, item in _all_items(module):
        fr = item["fr"]
        if topic["topic_type"] != "grammar" and re.match(r"l'\S", fr) and "/" not in fr and "(" not in fr:
            checked += 1
            assert _in_array(module, topic["id"], idx, "fr", fr[2:]), fr
    assert checked >= 20


def test_optional_suffix_forms_accept_base_and_full_word(game_env):
    module = game_env.module
    for tid, idx, forms in [
        ("fren151-w10-vocab003", 0, ["gentil", "gentille"]),
        ("fren151-w10-vocab003", 1, ["intelligent", "intelligente"]),
        ("fren151-w8-vocab001", 11, ["culturel", "culturelle"]),
        ("fren151-w8-vocab001", 0, ["ancien", "ancienne"]),
        ("fren152-w4-vocab002", 7, ["coquet", "coquette"]),
        ("fren151-w8-grammar001", 7, ["grand", "grande"]),
        ("fren152-w4-grammar002", 4, ["meilleur", "meilleure", "meilleurs", "meilleures"]),
        ("fren151-w8-vocab001", 17, ["cher", "chère"]),
    ]:
        for form in forms:
            assert _in_array(module, tid, idx, "fr", form), (tid, idx, form)


def test_optional_suffix_items_never_accept_a_wrong_form(game_env):
    module = game_env.module
    assert not _in_array(module, "fren151-w10-vocab003", 0, "fr", "gentils")
    assert not _in_array(module, "fren151-w10-vocab003", 0, "fr", "gentile")


# --------------------------------------------------------------------------
# bonus sentence + tile
# --------------------------------------------------------------------------
def test_bonus_tile_has_curated_glosses(game_env):
    module = game_env.module
    sentence = next(
        b for w in module.CATALOG["weeks"] for b in w.get("bonus_sentences", [])
        if b["id"] == "fren151-w1-bonus001"
    )
    tile = sentence["tiles"][2]
    assert tile["fr"] == "m'appelle"
    assert tile["en"] == "am called"
    assert tile["accepted_en"][0] == "am called"
    assert "call myself" in tile["accepted_en"]
    assert "I call myself" in tile["accepted_en"]
    # the sentence rebuilds exactly as before (tiles keep fr/en as the only displayed text)
    assert " ".join(t["fr"] for t in sentence["tiles"]) == sentence["fr"]


def test_catalog_counts_unchanged(game_env):
    module = game_env.module
    topics = [t for w in module.CATALOG["weeks"] for t in w["topics"]]
    assert len(module.CATALOG["weeks"]) == 23
    assert len(topics) == sum(1 for _ in topics)
    assert sum(len(t["items"]) for t in topics) == 1047


# --------------------------------------------------------------------------
# the review file itself
# --------------------------------------------------------------------------
def test_report_review_file_covers_all_50_reports():
    data = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    entries = data["reports"] if isinstance(data, dict) else data
    assert len(entries) == 50
    ids = [e["report_id"] for e in entries]
    assert len(set(ids)) == 50
    allowed = {"fixed", "not-a-bug", "test-row", "needs-owner", "needs-code"}
    for entry in entries:
        outcome = entry["outcome"]
        assert outcome in allowed or re.fullmatch(r"duplicate-of:[0-9a-f-]{36}", outcome), entry
        assert entry["note"].strip() and entry["item_id"]
        if outcome.startswith("duplicate-of:"):
            assert outcome.split(":", 1)[1] in ids
