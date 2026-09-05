"""Report-queue review, 2026-09-05: 25 reports from the live answer_reports
table were triaged by hand (§14.2.4). 5 traced to a real STRICT-tier bug,
fixed in game.py and covered by tests/test_grading_v2.py instead of here.
12 were genuine alternate phrasings/spelling variants, added as
accepted_en/accepted_fr overrides directly on the catalog. 8 were rejected
(incomplete answers, or answers that lose a distinction the item is
specifically testing) and deliberately left unaccepted -- no test for those,
since "still rejected" is just the pre-existing, unmodified behavior.

Each test here finds the real catalog item (not a hand-built stand-in) and
checks the exact path a live typed answer takes: _lookup_accepted() ->
answer_alternatives(..., accepted=...) -> normalize_answer(). This is the
same seam Milestone 8's own tests use, just anchored to real report data
instead of synthetic examples.
"""

import re


def _find_item(module, item_id):
    match = re.match(r"(.+)-i(\d+)$", item_id)
    topic_id, idx = match.group(1), int(match.group(2))
    for week in module.CATALOG["weeks"]:
        for topic in week["topics"]:
            if topic["id"] == topic_id:
                return topic["items"][idx]
    raise AssertionError(f"topic not found for {item_id}")


def _accepts(module, item, field, typed):
    canonical = item[field]
    accepted = module._catalog_item_accepted(item, field)
    alternatives = module.answer_alternatives(canonical, accepted=accepted)
    return module.normalize_answer(typed) in alternatives


def test_listen_carefully_also_accepts_listen_closely(game_env):
    module = game_env.module
    item = _find_item(module, "fren151-w1-vocab003-i06")
    assert item["en"] == "listen carefully!"
    assert _accepts(module, item, "en", "listen closely")
    assert _accepts(module, item, "en", "listen carefully")


def test_everybody_together_also_accepts_all_together(game_env):
    module = game_env.module
    item = _find_item(module, "fren151-w1-vocab003-i04")
    assert item["en"] == "everybody together"
    assert _accepts(module, item, "en", "all together")


def test_grandparents_also_accepts_the_two_word_spelling(game_env):
    module = game_env.module
    item = _find_item(module, "fren151-w9-vocab001-i07")
    assert item["en"] == "grandparents"
    assert _accepts(module, item, "en", "grand parents")


def test_a_shop_also_accepts_a_store(game_env):
    module = game_env.module
    item = _find_item(module, "fren151-w7-vocab001-i21")
    assert item["en"] == "a shop"
    assert _accepts(module, item, "en", "a store")


def test_shopping_centre_mall_also_accepts_american_spelling(game_env):
    module = game_env.module
    item = _find_item(module, "fren151-w7-vocab001-i20")
    assert item["en"] == "a shopping centre/mall"
    assert _accepts(module, item, "en", "a shopping center")
    # Pre-existing slash-split behaviour (from the raw answer itself, not
    # the accepted override) must still work after adding the override.
    assert _accepts(module, item, "en", "a shopping centre")
    assert _accepts(module, item, "en", "mall")


def test_i_work_part_time_also_accepts_no_hyphen(game_env):
    module = game_env.module
    item = _find_item(module, "fren151-w4-phrase002-i00")
    assert item["en"] == "I work part-time."
    assert _accepts(module, item, "en", "I work part time")


def test_waiter_waitress_also_accepts_server(game_env):
    module = game_env.module
    item = _find_item(module, "fren151-w4-vocab002-i06")
    assert item["en"] == "waiter/waitress"
    assert _accepts(module, item, "en", "server")
    # Pre-existing slash-split behaviour must still work.
    assert _accepts(module, item, "en", "waiter")
    assert _accepts(module, item, "en", "waitress")


def test_quel_age_avez_vous_also_accepts_no_hyphen(game_env):
    module = game_env.module
    item = _find_item(module, "fren151-w3-phrase001-i01")
    assert item["fr"] == "Quel âge avez-vous?"
    assert _accepts(module, item, "fr", "quel age avez vous")


def test_so_so_also_accepts_two_words_no_hyphen(game_env):
    module = game_env.module
    item = _find_item(module, "fren151-w2-phrase001-i04")
    assert item["en"] == "so-so"
    assert _accepts(module, item, "en", "so so")


def test_theatre_also_accepts_american_spelling(game_env):
    module = game_env.module
    item = _find_item(module, "fren151-w10-vocab001-i11")
    assert item["en"] == "theatre"
    assert _accepts(module, item, "en", "theater")


def test_pharmacists_cat_also_accepts_the_of_construction(game_env):
    module = game_env.module
    item = _find_item(module, "fren151-w9-grammar002-i00")
    assert item["en"] == "the pharmacist's cat"
    assert _accepts(module, item, "en", "the cat of the pharmacist")


def test_kind_also_accepts_nice(game_env):
    module = game_env.module
    item = _find_item(module, "fren151-w10-vocab003-i00")
    assert item["en"] == "kind"
    assert _accepts(module, item, "en", "nice")
    # And the STRICT-tier fr side (fixed separately in game.py) still
    # accepts the bare masculine form without its "(le)" suffix.
    assert item["fr"] == "gentil(le)"
    assert module.check_answer(
        {"mode": "typed", "answer": item["fr"], "choices": []},
        "gentil",
        tier=module.TIER_STRICT,
    ) is True


def test_rejected_reports_are_deliberately_still_rejected(game_env):
    """The other half of the same triage: these submissions were judged
    genuinely wrong (incomplete, ungrammatical, or lose a distinction the
    item exists to test) and were deliberately NOT added -- pinned here so
    a future over-eager leniency pass doesn't accidentally start accepting
    them without a deliberate decision."""
    module = game_env.module

    noon_midnight = _find_item(module, "fren152-w2-phrase001-i03")
    assert noon_midnight["en"] == "noon / midnight"
    assert not _accepts(module, noon_midnight, "en", "12:00")

    what_time = _find_item(module, "fren152-w2-phrase001-i00")
    assert what_time["en"] == "What time is it?"
    assert not _accepts(module, what_time, "en", "what hour is it")

    older_sibling = _find_item(module, "fren151-w9-vocab001-i18")
    assert older_sibling["en"] == "older brother / sister"
    assert not _accepts(module, older_sibling, "en", "older sibling")

    et_toi = _find_item(module, "fren151-w2-phrase001-i05")
    assert et_toi["fr"] == "Et toi / Et vous?"
    assert not _accepts(module, et_toi, "fr", "et tu")
