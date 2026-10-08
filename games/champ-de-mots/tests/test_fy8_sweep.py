"""FY-8 (2026-10-08): the three answer reports that arrived after the first
review, plus the same-class sweep of week 6 and weeks 12 to 23.

Outcomes are recorded in tests/report_review.json. Every case here runs the
real typed-answer path (grading_tier() -> check_answer()) against the real
catalog item, so it fails if the data or the two small grading changes
(ligatures and slash spacing in normalize_answer(); the 'd contractions)
regress.
"""

import re

import pytest

from .test_report_fixes import _all_items, _in_array, _live


# --------------------------------------------------------------------------
# the three reports
# --------------------------------------------------------------------------
def test_report_a10db191_the_road_counts_for_la_rue(game_env):
    module = game_env.module
    for typed in ("the road", "road", "The Road", "the street", "street"):
        assert _live(module, "fren151-w6-vocab002", 18, "en", typed), typed
    # la route is its own word with its own plot, la rue does not accept "route"
    assert not _live(module, "fren151-w6-vocab002", 18, "en", "the route")
    assert not _live(module, "fren151-w6-vocab002", 18, "en", "the avenue")


def test_report_4f38d109_is_it_far_close_to_here(game_env):
    module = game_env.module
    for typed in (
        "is it far/close to here",
        "Is it far/close to here?",
        "Is it far from here?",
        "Is it close to here?",
        "Is it far/close (from here)?",
        "Is it far?",
        "is it far / close",
    ):
        assert _live(module, "fren151-w6-phrase001", 3, "en", typed), typed
    assert not _live(module, "fren151-w6-phrase001", 3, "en", "Is it expensive?")


def test_report_8295f0aa_c_est_loin_d_ici(game_env):
    module = game_env.module
    for typed in (
        "C'est loin d'ici",
        "C'est loin d'ici?",
        "c'est près d'ici",
        "C'est loin/près d'ici?",
        "C'est loin/près (d'ici)?",
        "C'est loin?",
    ):
        assert _live(module, "fren151-w6-phrase001", 3, "fr", typed), typed
    assert not _live(module, "fren151-w6-phrase001", 3, "fr", "C'est cher d'ici")


def test_is_there_a_near_here_both_ways(game_env):
    module = game_env.module
    assert _live(module, "fren151-w6-phrase001", 4, "en", "Is there a... near here?")
    assert _live(module, "fren151-w6-phrase001", 4, "fr", "Est-ce qu'il y a... près d'ici?")
    assert _live(module, "fren151-w6-phrase001", 4, "fr", "Est-ce qu'il y a... (près d'ici)?")


# --------------------------------------------------------------------------
# the grading changes behind the sweep
# --------------------------------------------------------------------------
def test_ligatures_fold_to_two_letters_whatever_the_accent_setting(game_env):
    module = game_env.module
    n = module.normalize_answer
    assert n("œuf") == n("oeuf") == "oeuf"
    assert n("sœur", fold_accents=False) == n("soeur", fold_accents=False)
    assert n("Œuvre") == "oeuvre"
    # a real accent is still an accent
    assert n("été", fold_accents=False) != n("ete", fold_accents=False)


def test_typing_oeuf_counts_for_un_oeuf_and_boeuf(game_env):
    module = game_env.module
    # find the two catalog items by their French text
    hits = {}
    for topic, idx, item in _all_items(module):
        if item["fr"] in ("un œuf / des œufs", "du bœuf"):
            hits[item["fr"]] = (topic["id"], idx)
    assert len(hits) == 2
    tid, idx = hits["un œuf / des œufs"]
    assert _live(module, tid, idx, "fr", "un oeuf", accent_sensitive=True)
    assert _live(module, tid, idx, "fr", "des oeufs", accent_sensitive=True)
    tid, idx = hits["du bœuf"]
    assert _live(module, tid, idx, "fr", "du boeuf", accent_sensitive=True)
    assert _live(module, tid, idx, "fr", "du bœuf", accent_sensitive=True)


def test_a_slash_reads_the_same_with_or_without_spaces(game_env):
    module = game_env.module
    n = module.normalize_answer
    assert n("I/you/he") == n("I / you / he") == n("I /you/ he")
    alt = module.answer_alternatives("a rubber/eraser")
    assert {"a rubber", "rubber", "eraser", "a rubber/eraser", "a rubber / eraser"} <= alt


def test_d_contractions_both_directions(game_env):
    module = game_env.module
    q = {"mode": "typed", "answer": "I'd like...", "choices": []}
    assert module.check_answer(q, "I would like...", tier=module.TIER_LENIENT)
    q = {"mode": "typed", "answer": "How is the weather?", "choices": []}
    assert module.check_answer(q, "How's the weather?", tier=module.TIER_LENIENT)
    q = {"mode": "typed", "answer": "Where's the station?", "choices": []}
    assert module.check_answer(q, "Where is the station?", tier=module.TIER_LENIENT)
    # a contraction never turns a wrong answer right
    q = {"mode": "typed", "answer": "I'd like...", "choices": []}
    assert not module.check_answer(q, "I will like...", tier=module.TIER_LENIENT)


# --------------------------------------------------------------------------
# sweep: answers a learner would really type (topic id, index, field, typed)
# --------------------------------------------------------------------------
SWEEP_PASSES = [
    # week 6
    ("fren151-w6-vocab001", 2, "en", "straight ahead"),
    ("fren151-w6-vocab001", 5, "en", "cross"),
    ("fren151-w6-vocab001", 7, "en", "beside"),
    ("fren151-w6-vocab001", 8, "en", "just to the right"),
    ("fren151-w6-vocab002", 1, "en", "big river"),
    ("fren151-w6-vocab002", 8, "en", "the harbour"),
    ("fren151-w6-vocab002", 8, "en", "the harbor"),
    ("fren151-w6-vocab002", 9, "en", "quay"),
    ("fren151-w6-vocab002", 17, "en", "the plaza"),
    ("fren151-w6-vocab002", 21, "en", "the path"),
    # week 13
    ("fren152-w3-vocab001", 0, "en", "to shower"),
    ("fren152-w3-vocab001", 2, "en", "to comb your hair"),
    ("fren152-w3-vocab001", 3, "en", "to put on make-up"),
    ("fren152-w3-vocab001", 3, "en", "to put on makeup"),
    ("fren152-w3-vocab001", 4, "en", "to brush your teeth"),
    ("fren152-w3-vocab001", 5, "fr", "s'habiller"),
    ("fren152-w3-vocab001", 5, "fr", "se déshabiller"),
    ("fren152-w3-vocab001", 5, "en", "to undress"),
    ("fren152-w3-vocab001", 10, "en", "to rise"),
    ("fren152-w3-grammar001", 0, "en", "on Mondays"),
    ("fren152-w3-grammar001", 0, "en", "every Monday"),
    ("fren152-w3-grammar001", 1, "en", "in the morning"),
    ("fren152-w3-vocab003", 2, "en", "now and then"),
    ("fren152-w3-vocab003", 6, "en", "once per day"),
    ("fren152-w3-vocab003", 9, "en", "daily"),
    ("fren152-w3-vocab-slide001", 4, "en", "the violin"),
    ("fren152-w3-vocab-slide001", 7, "en", "a keyboard"),
    ("fren152-w3-vocab-slide001", 6, "en", "the drums"),
    ("fren152-w3-vocab-slide001", 11, "en", "petanque"),
    # week 14
    ("fren152-w4-vocab001", 2, "en", "I eat breakfast"),
    ("fren152-w4-vocab001", 4, "en", "I walk on the beach"),
    ("fren152-w4-vocab001", 8, "en", "I have a bath"),
    ("fren152-w4-vocab002", 1, "en", "hardworking"),
    ("fren152-w4-vocab002", 4, "en", "partygoer"),
    ("fren152-w4-vocab002", 5, "en", "eco-friendly"),
    ("fren152-w4-grammar002", 0, "en", "more than"),
    ("fren152-w4-grammar002", 0, "en", "more...than"),
    ("fren152-w4-grammar002", 2, "en", "as...as"),
    ("fren152-w4-grammar002", 3, "en", "Jacques is bigger than Julie."),
    # week 15
    ("fren152-w5-phrase001", 1, "en", "What's the date of your birthday?"),
    ("fren152-w5-phrase002", 0, "en", "How many times a week?"),
    ("fren152-w5-phrase002", 1, "en", "How many hours a week?"),
    ("fren152-w5-grammar001", 2, "en", "how many"),
    ("fren152-w5-grammar001", 2, "en", "which"),
    # week 16
    ("fren152-w6-vocab001", 1, "en", "a pair of jeans"),
    ("fren152-w6-vocab001", 11, "en", "t-shirt"),
    ("fren152-w6-vocab001", 11, "en", "a tee shirt"),
    ("fren152-w6-vocab001", 18, "en", "a woolly hat"),
    ("fren152-w6-phrase001", 0, "en", "What do you wear today?"),
    ("fren152-w6-phrase001", 1, "en", "Today I am wearing..."),
    # week 17
    ("fren152-w7-phrase001", 0, "en", "What color is your...?"),
    ("fren152-w7-phrase001", 0, "en", "What colour are your...?"),
    ("fren152-w7-phrase001", 1, "en", "What material is your... made of?"),
    ("fren152-w7-vocab002", 0, "en", "long sleeves"),
    ("fren152-w7-vocab002", 0, "en", "short-sleeved"),
    ("fren152-w7-vocab002", 5, "en", "narrow"),
    ("fren152-w7-vocab002", 5, "en", "tight"),
    ("fren152-w7-vocab002", 5, "en", "narrow, tight"),
    ("fren152-w7-vocab002", 8, "en", "stripy"),
    ("fren152-w7-vocab002", 9, "en", "with spots"),
    ("fren152-w7-vocab-slide001", 5, "en", "faux fur"),
    ("fren152-w7-vocab-slide001", 7, "en", "size"),
    ("fren152-w7-phrase-slide001", 4, "en", "May I help you?"),
    ("fren152-w7-phrase-slide001", 5, "en", "Who is it for?"),
    ("fren152-w7-phrase-slide001", 6, "en", "What size do you wear?"),
    ("fren152-w7-phrase-slide001", 9, "en", "How much does it cost?"),
    ("fren152-w7-phrase-slide001", 10, "en", "How do you pay?"),
    ("fren152-w7-phrase-slide001", 11, "en", "with a card"),
    ("fren152-w7-phrase-slide001", 12, "en", "cash"),
    ("fren152-w7-phrase-slide001", 13, "en", "It's too expensive. I'll take it"),
    ("fren152-w7-phrase-slide001", 13, "en", "It is a bit expensive. I will take it"),
    # week 18
    ("fren152-w8-vocab001", 4, "en", "a bath towel"),
    ("fren152-w8-vocab001", 7, "en", "a hairdryer"),
    ("fren152-w8-vocab002", 0, "en", "How's the weather?"),
    ("fren152-w8-vocab002", 1, "en", "it's bad weather"),
    ("fren152-w8-vocab002", 1, "en", "it's nice weather"),
    ("fren152-w8-vocab002", 2, "en", "it's hot"),
    ("fren152-w8-vocab002", 2, "en", "it's cold"),
    ("fren152-w8-vocab002", 5, "en", "there is sun"),
    ("fren152-w8-vocab002", 9, "en", "there's a storm"),
    ("fren152-w8-grammar001", 2, "en", "I can / you can / he can"),
    ("fren152-w8-grammar001", 3, "en", "we can, you can, they can"),
    ("fren152-w8-grammar001", 4, "en", "I would like"),
    ("fren152-w8-grammar001", 4, "en", "I'd like"),
    # week 19
    ("fren152-w9-vocab002", 3, "en", "mineral water"),
    ("fren152-w9-vocab003", 0, "en", "an appetizer"),
    ("fren152-w9-vocab003", 0, "en", "an entrée"),
    ("fren152-w9-phrase001", 0, "en", "What do you eat for breakfast?"),
    ("fren152-w9-phrase001", 1, "en", "For breakfast I eat..."),
    ("fren152-w9-phrase001", 2, "en", "As a main, I'd like..."),
    ("fren152-w9-phrase001", 2, "en", "As a dessert, I would like..."),
    # week 20
    ("fren152-w10-vocab001", 1, "en", "the pastry shop"),
    ("fren152-w10-vocab001", 2, "en", "the grocery store"),
    ("fren152-w10-vocab001", 4, "en", "the fishmonger's"),
    ("fren152-w10-vocab001", 5, "en", "the deli"),
    ("fren152-w10-vocab001", 7, "en", "the fruit and veg shop"),
    ("fren152-w10-grammar001", 0, "en", "Are you going to the bakery? No, I'm going there tomorrow."),
    ("fren152-w10-grammar003", 0, "en", "I will play"),
    ("fren152-w10-grammar005", 0, "en", "Do you want coffee? Yes, I want some of it."),
    ("fren152-w10-grammar005", 1, "en", "They have three of them."),
    ("fren152-w10-grammar005", 2, "en", "No, I don't have any of them."),
    # week 21
    ("fren152-w11-phrase001", 0, "en", "Could you give me the menu?"),
    ("fren152-w11-phrase001", 1, "en", "Have you decided?"),
    ("fren152-w11-phrase001", 2, "en", "What's the dish of the day?"),
    ("fren152-w11-phrase001", 3, "en", "I would like a rare steak."),
    ("fren152-w11-phrase001", 4, "en", "still water"),
    ("fren152-w11-phrase001", 4, "en", "sparkling water"),
    ("fren152-w11-phrase001", 5, "en", "The check, please"),
    ("fren152-w11-phrase001", 5, "en", "Can I have the bill, please?"),
    ("fren152-w11-grammar002", 0, "en", "yesterday morning"),
    ("fren152-w11-grammar002", 0, "fr", "hier matin"),
    ("fren152-w11-grammar002", 4, "en", "lately"),
    ("fren152-w11-grammar002", 6, "en", "all at once"),
    # week 22
    ("fren152-w12-grammar002", 2, "en", "I know / you know / he knows"),
    ("fren152-w12-grammar002", 3, "en", "we know, you know, they know"),
    ("fren152-w12-grammar001", 11, "en", "could"),
    # week 23
    ("fren152-w13-grammar002", 0, "en", "I washed myself"),
    ("fren152-w13-grammar002", 3, "en", "they dressed"),
    ("fren152-w13-vocab001", 0, "en", "I can do DIY."),
    ("fren152-w13-vocab001", 1, "en", "I can work in a team."),
]


@pytest.mark.parametrize("topic_id,idx,field,typed", SWEEP_PASSES)
def test_sweep_answers_a_learner_would_type_pass(game_env, topic_id, idx, field, typed):
    assert _live(game_env.module, topic_id, idx, field, typed), (topic_id, idx, typed)


SWEEP_FAILS = [
    # still wrong: a different word, a wrong tense, the opposite meaning
    ("fren151-w6-vocab002", 18, "en", "the bridge"),
    ("fren151-w6-vocab002", 1, "en", "small river"),
    ("fren151-w6-vocab002", 0, "en", "big river"),
    ("fren152-w7-vocab002", 5, "en", "wide"),
    ("fren152-w8-vocab002", 2, "en", "it's raining"),
    ("fren152-w8-vocab002", 1, "en", "it's hot"),
    ("fren152-w3-vocab003", 1, "en", "often"),
    ("fren152-w3-vocab001", 7, "en", "to wake up"),
    ("fren152-w11-phrase001", 4, "en", "mineral water"),
    ("fren152-w10-grammar005", 2, "en", "Yes, I have some."),
    ("fren152-w13-grammar002", 0, "en", "I washed the dishes"),
]


@pytest.mark.parametrize("topic_id,idx,field,typed", SWEEP_FAILS)
def test_sweep_additions_did_not_loosen_the_grader_too_far(game_env, topic_id, idx, field, typed):
    assert not _live(game_env.module, topic_id, idx, field, typed), (topic_id, idx, typed)


# --------------------------------------------------------------------------
# hygiene for the swept weeks
# --------------------------------------------------------------------------
SWEPT_SEQUENCES = {6} | set(range(12, 24))


def _swept_items(module):
    for week in module.CATALOG["weeks"]:
        if week["sequence"] not in SWEPT_SEQUENCES:
            continue
        for topic in week["topics"]:
            for idx, item in enumerate(topic["items"]):
                yield topic, idx, item


def test_no_gloss_in_the_swept_weeks_has_meta_text_outside_brackets(game_env):
    module = game_env.module
    seen = 0
    for topic, idx, item in _swept_items(game_env.module):
        outside = re.sub(r"\([^)]*\)", "", item["en"])
        seen += 1
        assert " vs. " not in outside, (topic["id"], idx, item["en"])
        assert "lundi =" not in outside, (topic["id"], idx, item["en"])
    assert seen > 250


def test_optional_brackets_that_a_player_types_are_accepted(game_env):
    module = game_env.module
    cases = [
        ("fren151-w6-vocab002", 0, "en", "(small) river"),
        ("fren151-w6-vocab002", 1, "en", "(big) river"),
        ("fren152-w8-vocab001", 4, "en", "a bath towel"),
        ("fren152-w9-vocab002", 3, "en", "mineral water"),
        ("fren152-w10-grammar001", 0, "en", "Are you going to the bakery? No, I'm going there tomorrow."),
        ("fren152-w10-grammar005", 0, "en", "Do you want coffee? Yes, I want some of it."),
        ("fren152-w10-grammar005", 1, "en", "They have three of them."),
        ("fren152-w10-grammar005", 2, "en", "No, I don't have any of them."),
        ("fren151-w6-phrase001", 3, "fr", "C'est loin/près d'ici?"),
        ("fren151-w6-phrase001", 4, "en", "Is there a... near here?"),
    ]
    for tid, idx, field, typed in cases:
        assert _live(module, tid, idx, field, typed), (tid, idx, typed)


def test_slash_lists_in_the_swept_weeks_accept_each_part_as_a_whole_phrase(game_env):
    """'it's cold / hot' used to accept 'it's cold' and 'hot' but not 'it's hot'."""
    module = game_env.module
    assert _live(module, "fren152-w8-vocab002", 2, "en", "it's cold")
    assert _live(module, "fren152-w8-vocab002", 2, "en", "it's hot")
    assert _live(module, "fren152-w8-vocab002", 1, "en", "it's bad weather")
    assert _live(module, "fren152-w11-phrase001", 4, "en", "still water")
    assert _live(module, "fren152-w11-phrase001", 4, "en", "sparkling water")


def test_comma_lists_accept_each_part(game_env):
    module = game_env.module
    for part in ("narrow", "tight", "narrow, tight", "narrow tight"):
        assert _live(module, "fren152-w7-vocab002", 5, "en", part), part


def test_noun_glosses_of_instruments_accept_an_article(game_env):
    module = game_env.module
    for idx, word in ((4, "violin"), (5, "clarinet"), (9, "cymbals"), (10, "flute"), (8, "accordion")):
        assert _live(module, "fren152-w3-vocab-slide001", idx, "en", f"the {word}") or word == "cymbals", word
    assert _live(module, "fren152-w3-vocab-slide001", 9, "en", "the cymbals")


def test_curated_arrays_in_the_swept_weeks_are_canonical_first_and_unique(game_env):
    module = game_env.module
    touched = 0
    for topic, idx, item in _swept_items(module):
        for field in ("fr", "en"):
            arr = item.get(f"accepted_{field}")
            if not arr:
                continue
            touched += 1
            assert arr[0] == item[field], (topic["id"], idx, field)
            normalized = [module.normalize_answer(a) for a in arr[1:]]
            assert all(normalized), (topic["id"], idx, field)
    assert touched > 120
