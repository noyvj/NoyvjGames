"""FS (FREN152 slides) content: what each slide week added to its farm row, and that every added
item plays properly (variants, generated questions, typed answers). The topics were written from
the course's weekly topics in my own wording; nothing here is slide text.
"""

import random

from .test_report_fixes import _item, _live, _topic

# week number of the slide programme -> what was added to farm row (week + 11).
FS_WEEKS = {
    1: {"row": 12, "topics": 7, "plots": 40, "must_have": [
        "et quart", "moins le quart", "du soir", "Il est midi moins cinq.", "À quelle heure est le cours?",
        "réfléchir à", "réussir à", "rendre visite à", "répondre à", "maigrir", "dîner",
    ]},
    2: {"row": 13, "topics": 10, "plots": 48, "must_have": [
        "je me lave", "je me lève", "je m'habille", "se promener", "se démaquiller", "d'abord", "en semaine",
        "quatre fois par an", "Je ne fais jamais de sport.", "Aujourd'hui, c'est lundi.", "Le réveil sonne à six heures.",
    ]},
}


def _fs_topics(module, row=None):
    return [
        t for w in module.CATALOG["weeks"] for t in w["topics"]
        if "-fs" in t["id"] and (row is None or w["sequence"] == row)
    ]


def _plots_of(topics):
    return sum(1 if t["topic_type"] == "grammar" else len(t["items"]) for t in topics)


def test_each_slide_week_added_what_it_says(game_env):
    module = game_env.module
    for week, spec in FS_WEEKS.items():
        topics = _fs_topics(module, spec["row"])
        assert len(topics) == spec["topics"], week
        assert _plots_of(topics) == spec["plots"], week
        frs = {i["fr"] for t in topics for i in t["items"]}
        for needed in spec["must_have"]:
            assert needed in frs, (week, needed)


def test_every_added_plot_has_three_variants_and_generates_every_one(game_env):
    module = game_env.module
    rng = random.Random(5)
    ids = {t["id"] for t in _fs_topics(module)}
    checked = 0
    for plot in game_env.state.plots:
        if plot.topic_id not in ids:
            continue
        variants = module.variants_for(plot)
        assert len(variants) >= 3, (plot.plot_id, variants)
        for variant in variants:
            question = module.generate_question(plot, rng, variant=variant)
            assert question["answer"].strip() and question["prompt"].strip(), (plot.plot_id, variant)
            if question["mode"] == "choice":
                assert question["answer"] in question["choices"]
            assert module.check_answer(question, question["answer"]) is True
            checked += 1
    assert checked >= 100


def test_added_items_accept_their_canonical_answers_and_curated_alternatives(game_env):
    module = game_env.module
    for topic in _fs_topics(module):
        if topic["topic_type"] == "grammar":
            continue
        for idx, item in enumerate(topic["items"]):
            assert _live(module, topic["id"], idx, "en", item["en"]), (topic["id"], item["en"])
            extras = item.get("accepted_en", [])
            assert extras == [] or extras[0] == item["en"], (topic["id"], item["fr"])
            assert len({module.normalize_answer(x) for x in extras}) == len(extras), (topic["id"], item["fr"])
            for typed in extras:
                assert _live(module, topic["id"], idx, "en", typed), (topic["id"], item["fr"], typed)
            if len(item["fr"]) <= module.MAX_TYPED_ANSWER_LENGTH:
                assert _live(module, topic["id"], idx, "fr", item["fr"]), (topic["id"], item["fr"])


def test_no_added_item_repeats_another_item_in_its_own_topic(game_env):
    module = game_env.module
    for topic in _fs_topics(module):
        frs = [i["fr"].lower() for i in topic["items"]]
        assert len(frs) == len(set(frs)), topic["id"]


def test_added_glosses_follow_the_catalogue_conventions(game_env):
    module = game_env.module
    for topic in _fs_topics(module):
        for item in topic["items"]:
            assert item["fr"] == item["fr"].strip() and item["en"] == item["en"].strip()
            assert "  " not in item["fr"] + item["en"], (topic["id"], item["fr"])
            assert "—" not in item["en"], (topic["id"], item["en"])
            assert "FREN1" not in item["en"] + item["fr"]
        assert topic["title"] and not topic["title"].endswith(".")


# --- week 1 ------------------------------------------------------------------


def test_week_1_time_words_and_example_times(game_env):
    module = game_env.module
    words = _topic(module, "fren152-w2-vocab-fs01")
    glosses = {i["fr"]: i["en"] for i in words["items"]}
    assert glosses["et demie"] == "half past"
    assert glosses["moins le quart"] == "quarter to"
    times = _topic(module, "fren152-w2-phrase-fs02")
    assert _live(module, times["id"], 1, "en", "It is a quarter to ten")
    assert _live(module, times["id"], 5, "en", "It's 3:30 pm")
    assert _live(module, times["id"], 4, "fr", "il est minuit et quart")


def test_week_1_verb_lists_are_the_regular_families(game_env):
    module = game_env.module
    for topic_id, ending in (("fren152-w2-vocab-fs05", "ir"), ("fren152-w2-vocab-fs06", "re")):
        for item in _topic(module, topic_id)["items"]:
            first = item["fr"].split()[0]
            assert first.endswith(ending), item["fr"]
    assert all(i["fr"].endswith("er") for i in _topic(module, "fren152-w2-vocab-fs04")["items"])
    # the "à" verbs keep the preposition in the item, so the typed answer teaches it
    assert _item(module, "fren152-w2-vocab-fs05", 2)["fr"] == "réfléchir à"
    assert _live(module, "fren152-w2-vocab-fs05", 4, "en", "to pass an exam")


def test_week_1_number_plurals_is_one_grammar_plot_with_a_rule(game_env):
    module = game_env.module
    topic = _topic(module, "fren152-w2-grammar-fs07")
    assert topic["topic_type"] == "grammar" and "mille" in topic["rule"].lower()
    assert "fren152-w2-grammar-fs07" in game_env.state.plots_by_id


# --- week 2 ------------------------------------------------------------------


def test_week_2_reflexive_tables_are_person_by_person_conjugation_plots(game_env):
    module = game_env.module
    for topic_id in ("fren152-w3-grammar-fs01", "fren152-w3-grammar-fs02", "fren152-w3-grammar-fs03"):
        plot = game_env.state.plots_by_id[topic_id]
        assert module.is_conjugation_plot(plot), topic_id
        assert module.V_CONJUGATION_SWAP in module.variants_for(plot)
        assert [i["fr"].split()[0] for i in plot.items] == ["je", "tu", "il", "nous", "vous", "ils"]


def test_week_2_reflexive_pronouns_match_their_subjects(game_env):
    module = game_env.module
    expected = {"je": "me", "tu": "te", "il": "se", "nous": "nous", "vous": "vous", "ils": "se"}
    for topic_id in ("fren152-w3-grammar-fs01", "fren152-w3-grammar-fs02"):
        for item in _topic(module, topic_id)["items"]:
            subject, pronoun = item["fr"].split()[:2]
            assert pronoun == expected[subject], item["fr"]
    elided = {"je": "m'", "tu": "t'", "il": "s'", "ils": "s'"}
    for item in _topic(module, "fren152-w3-grammar-fs03")["items"]:
        words = item["fr"].split()
        if words[0] in elided:
            assert words[1].startswith(elided[words[0]]), item["fr"]
        else:
            assert words[1] == words[0], item["fr"]  # nous nous / vous vous never shorten


def test_week_2_se_lever_carries_the_grave_accent_where_it_should(game_env):
    forms = [i["fr"] for i in _topic(game_env.module, "fren152-w3-grammar-fs02")["items"]]
    assert [("è" in f) for f in forms] == [True, True, True, False, False, True]


def test_week_2_body_part_sentences_use_the_article_not_a_possessive(game_env):
    for item in _topic(game_env.module, "fren152-w3-phrase-fs04")["items"]:
        assert " les " in item["fr"], item["fr"]
        assert not any(w in item["fr"].lower().split() for w in ("mes", "ses", "mon", "son", "ma", "sa"))


def test_week_2_ne_jamais_sentences_really_wrap_the_verb(game_env):
    for item in _topic(game_env.module, "fren152-w3-grammar-fs08")["items"]:
        text = item["fr"].lower()
        assert ("ne " in text or "n'" in text) and "jamais" in text, item["fr"]
        assert text.index("jamais") > text.replace("n'", "ne ").index("ne")


def test_week_2_routine_words_and_frequency_have_their_english(game_env):
    module = game_env.module
    glosses = {i["fr"]: i["en"] for i in _topic(module, "fren152-w3-vocab-fs06")["items"]}
    assert glosses["tôt"] == "early" and glosses["tard"] == "late" and glosses["d'abord"] == "first"
    freq = {i["fr"]: i["en"] for i in _topic(module, "fren152-w3-vocab-fs07")["items"]}
    assert freq["quatre fois par an"] == "four times a year" and freq["presque"] == "almost"
    assert _live(module, "fren152-w3-vocab-fs06", 3, "en", "afterwards")
