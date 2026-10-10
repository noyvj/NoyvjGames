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
        "quatre fois par an", "Je ne fais jamais de ski.", "Aujourd'hui, c'est lundi.", "Le réveil sonne à six heures.",
    ]},
    3: {"row": 14, "topics": 7, "plots": 47, "must_have": [
        "faire du yoga", "faire des promenades", "jouer aux cartes", "jouer du violon", "le karaté", "un rendez-vous",
        "chez le dentiste", "Qu'est-ce que tu fais jeudi?", "partir en vacances", "sortir les poubelles",
    ]},
    4: {"row": 15, "topics": 7, "plots": 41, "must_have": [
        "quand", "pourquoi", "qu'est-ce que", "à quelle heure", "C'est le premier avril.", "le premier mai",
        "Tu vas où?", "Que fais-tu dans la vie?", "Combien d'heures par semaine travailles-tu?", "à mon avis", "bon marché",
        "Le train est plus rapide que le bus.",
    ]},
    5: {"row": 16, "topics": 5, "plots": 33, "must_have": [
        "un anorak", "des bas", "un tailleur", "porter", "bleu clair", "vert foncé", "Ce sont des collants orange.",
        "des collants orange", "Cette chemise ne te va pas.", "Quels pulls sont en promotion?",
    ]},
    6: {"row": 17, "topics": 7, "plots": 40, "must_have": [
        "en lin", "uni(e)", "un sac noir en cuir", "affreux / affreuse", "moche / laid(e)", "Je prends celui-ci.",
        "Quelle est votre pointure?", "celle en soie", "Tu vas vraiment porter ça?", "en vitrine", "un portefeuille",
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


# --- week 3 ------------------------------------------------------------------


def test_week_3_faire_items_take_the_right_little_word(game_env):
    for item in _topic(game_env.module, "fren152-w4-vocab-fs01")["items"]:
        words = item["fr"].split()
        assert words[0] == "faire" and words[1] in {"du", "de", "des"}, item["fr"]
        if words[1] == "de":
            assert words[2] == "la", item["fr"]


def test_week_3_jouer_items_separate_games_from_instruments(game_env):
    module = game_env.module
    for item in _topic(module, "fren152-w4-vocab-fs02")["items"]:
        words = item["fr"].split()
        assert words[0] == "jouer"
        game_like = words[1] in {"au", "aux", "à"}
        instrument_like = words[1] in {"du", "de"}
        assert game_like != instrument_like, item["fr"]
        assert ("to play the" in item["en"]) == instrument_like or "play" in item["en"]
    # every instrument gloss names the instrument with its article
    glosses = {i["fr"]: i["en"] for i in _topic(module, "fren152-w4-vocab-fs02")["items"]}
    assert glosses["jouer du violon"] == "to play the violin"
    assert glosses["jouer de la batterie"] == "to play the drums"


def test_week_3_gym_and_appointment_words(game_env):
    module = game_env.module
    gym = {i["fr"]: i["en"] for i in _topic(module, "fren152-w4-vocab-fs03")["items"]}
    assert gym["la gymnastique"] == "gymnastics" and gym["le judo"] == "judo"
    appointments = [i["fr"] for i in _topic(module, "fren152-w4-vocab-fs04")["items"]]
    assert "un rendez-vous" in appointments and "une soirée déguisée" in appointments
    assert _live(module, "fren152-w4-vocab-fs04", 5, "en", "at the dentist")


def test_week_3_plans_use_a_time_or_a_place(game_env):
    module = game_env.module
    sentences = _topic(module, "fren152-w4-phrase-fs05")["items"]
    assert len(sentences) == 7
    assert any("heures" in i["fr"] for i in sentences)
    assert _live(module, "fren152-w4-phrase-fs05", 1, "en", "My judo class is at five pm")
    assert _live(module, "fren152-w4-phrase-fs05", 6, "en", "I'm going to the market at the weekend")


def test_week_3_jouer_grammar_plot_pairs_each_preposition_with_its_kind(game_env):
    topic = _topic(game_env.module, "fren152-w4-grammar-fs06")
    assert topic["topic_type"] == "grammar" and len(topic["items"]) == 6
    kinds = {i["fr"]: i["en"] for i in topic["items"]}
    assert kinds["Mon frère joue de la batterie."] == "My brother plays the drums."
    assert kinds["Ma sœur joue aux cartes."] == "My sister plays cards."
    assert "instrument" in topic["rule"] and "game" in topic["rule"]


def test_week_3_sortir_family_keeps_the_infinitive_endings(game_env):
    items = _topic(game_env.module, "fren152-w4-vocab-fs07")["items"]
    verbs = [i["fr"].split()[0] for i in items]
    assert verbs[:4] == ["sortir", "partir", "dormir", "servir"] and all(v.endswith("ir") for v in verbs[:4])
    assert [i["fr"] for i in items][-1] == "sortir les poubelles"


def test_week_2_never_example_was_reworded_not_copied(game_env):
    first = _topic(game_env.module, "fren152-w3-grammar-fs08")["items"][0]
    assert first["fr"] == "Je ne fais jamais de ski." and first["en"] == "I never go skiing."


# --- week 4 ------------------------------------------------------------------


def test_week_4_question_words_cover_the_basic_set(game_env):
    glosses = {i["fr"]: i["en"] for i in _topic(game_env.module, "fren152-w5-vocab-fs01")["items"]}
    assert glosses["où"] == "where" and glosses["pourquoi"] == "why" and glosses["comment"] == "how"
    assert glosses["combien"] == "how much"
    assert _live(game_env.module, "fren152-w5-vocab-fs01", 5, "en", "how many")


def test_week_4_dates_use_the_first_as_an_ordinal_and_other_days_as_numbers(game_env):
    module = game_env.module
    items = {i["fr"]: i["en"] for i in _topic(module, "fren152-w5-grammar-fs03")["items"]}
    assert items["le premier mai"] == "the first of May"
    others = [fr for fr in items if "premier" not in fr]
    assert len(others) == 3 and all(fr.startswith("le ") for fr in others)
    assert "premier" in _topic(module, "fren152-w5-grammar-fs03")["rule"]
    assert _live(module, "fren152-w5-phrase-fs02", 0, "en", "It's April first")
    assert _live(module, "fren152-w5-phrase-fs02", 3, "en", "My birthday is May 12th")


def test_week_4_question_patterns_include_formal_and_informal(game_env):
    module = game_env.module
    topic = _topic(module, "fren152-w5-grammar-fs04")
    assert topic["topic_type"] == "grammar" and len(topic["items"]) == 6
    frs = [i["fr"] for i in topic["items"]]
    assert "Tu vas où?" in frs and "Que fais-tu dans la vie?" in frs
    assert sum(1 for f in frs if f.endswith("?")) == 6
    assert "(formal)" in topic["items"][4]["en"]
    assert _live(module, topic["id"], 4, "en", "What do you do for a living")


def test_week_4_how_often_sentences_carry_their_numbers(game_env):
    items = _topic(game_env.module, "fren152-w5-phrase-fs05")["items"]
    assert [("combien" in i["fr"].lower()) for i in items][:2] == [True, True]
    assert _live(game_env.module, "fren152-w5-phrase-fs05", 2, "en", "I work 14 hours a week")


def test_week_4_comparison_words_and_sentences(game_env):
    module = game_env.module
    words = {i["fr"]: i["en"] for i in _topic(module, "fren152-w5-vocab-fs06")["items"]}
    assert words["bon marché"] == "cheap" and words["à mon avis"] == "in my opinion"
    sentences = _topic(module, "fren152-w5-phrase-fs07")["items"]
    markers = (" plus ", " moins ", " aussi ", "meilleure", " pire ")
    assert all(any(m in i["fr"] for m in markers) for i in sentences) and len(sentences) == 8
    assert "meilleur" in _topic(module, "fren152-w5-phrase-fs07")["rule"]


# --- week 5 ------------------------------------------------------------------


def test_week_5_extra_clothes_carry_their_article_and_the_plural_may_drop_it(game_env):
    module = game_env.module
    topic = _topic(module, "fren152-w6-vocab-fs01")
    for item in topic["items"][:-1]:
        assert item["fr"].split()[0] in {"un", "une", "des"}, item["fr"]
    assert _live(module, topic["id"], 1, "fr", "bas")  # "des bas" may lose des
    assert _live(module, topic["id"], 0, "en", "a parka")
    assert topic["items"][-1] == {"fr": "porter", "en": "to wear", "accepted_en": ["to wear", "to carry", "to bring"]}


def test_week_5_light_and_dark_colours_pair_a_colour_with_clair_or_foncé(game_env):
    for item in _topic(game_env.module, "fren152-w6-vocab-fs02")["items"]:
        colour, shade = item["fr"].split()
        assert shade in {"clair", "foncé"}, item["fr"]
        assert shade == ("clair" if item["en"].startswith(("light", "pale")) else "foncé")


def test_week_5_colour_agreement_plot_shows_the_exceptions(game_env):
    module = game_env.module
    topic = _topic(module, "fren152-w6-grammar-fs04")
    frs = [i["fr"] for i in topic["items"]]
    assert "des collants orange" in frs and "un pull marron" in frs  # orange and marron never change
    assert "une robe verte" in frs and "des chaussures noires" in frs
    assert "bleu clair" in " ".join(frs)
    assert "orange" in topic["rule"].lower() and "clair" in topic["rule"]


def test_week_5_clothes_sentences_use_real_colour_agreement(game_env):
    sentences = {i["fr"]: i["en"] for i in _topic(game_env.module, "fren152-w6-phrase-fs03")["items"]}
    assert "robe verte" in " ".join(sentences) and "chaussures noires" in " ".join(sentences)
    assert "Mes chaussettes sont rouges et blanches." in sentences
    assert len(sentences) == 10


def test_week_5_choosing_clothes_phrases_translate_both_ways(game_env):
    module = game_env.module
    topic = _topic(module, "fren152-w6-phrase-fs05")
    assert len(topic["items"]) == 6
    assert _live(module, topic["id"], 2, "en", "That shirt doesn't suit you")
    assert _live(module, topic["id"], 1, "en", "Which jumpers are on sale")


# --- week 6 ------------------------------------------------------------------


def test_week_6_word_order_plot_puts_colour_before_material_and_pattern(game_env):
    module = game_env.module
    topic = _topic(module, "fren152-w7-grammar-fs02")
    assert topic["topic_type"] == "grammar" and len(topic["items"]) == 6
    colours = {"noir", "grise", "violets", "rouge", "blanche", "beige"}
    for item in topic["items"]:
        words = item["fr"].split()
        assert (" en " in item["fr"]) or (" à " in item["fr"]), item["fr"]
        assert colours & set(words), item["fr"]
    assert "un pull en coton beige" in [i["fr"] for i in topic["items"]]  # material first is allowed too
    assert "en + material" in topic["rule"] or "en + material" in topic["rule"].replace("noun + colour + ", "")


def test_week_6_new_materials_and_styles_are_single_prepositional_phrases(game_env):
    items = _topic(game_env.module, "fren152-w7-vocab-fs01")["items"]
    frs = [i["fr"] for i in items]
    assert frs[:2] == ["uni(e)", "à manches courtes"]
    assert all(f.startswith("en ") for f in frs[2:])


def test_week_6_opinion_words_have_distinct_english(game_env):
    items = _topic(game_env.module, "fren152-w7-vocab-fs03")["items"]
    glosses = [i["en"] for i in items]
    assert len(set(glosses)) == len(glosses)
    assert _live(game_env.module, "fren152-w7-vocab-fs03", 1, "en", "ugly")
    assert _live(game_env.module, "fren152-w7-vocab-fs03", 1, "fr", "laid")  # either side of the slash


def test_week_6_shop_talk_has_ten_phrases_and_the_polite_closing(game_env):
    module = game_env.module
    topic = _topic(module, "fren152-w7-phrase-fs04")
    assert len(topic["items"]) == 10
    assert topic["items"][-1]["fr"] == "Merci, bonne journée!"
    assert _live(module, topic["id"], 8, "en", "I'll take this one")


def test_week_6_opinion_questions_use_plaire_in_both_numbers(game_env):
    frs = [i["fr"] for i in _topic(game_env.module, "fren152-w7-phrase-fs05")["items"]]
    assert any("te plaît" in f for f in frs) and any("te plaisent" in f for f in frs)
    assert len(frs) == 6


def test_week_6_demonstrative_pronoun_uses_cover_de_qui_en_and_ci_la(game_env):
    topic = _topic(game_env.module, "fren152-w7-grammar-fs06")
    frs = [i["fr"] for i in topic["items"]]
    assert frs[0].startswith("celui de") and "qui" in frs[2] and " en " in frs[1] and "-ci" in frs[4]
    assert all(f.split()[0].startswith(("celui", "celle", "ceux", "celles")) for f in frs)


def test_week_6_shoe_shop_words_are_a_real_vocab_list(game_env):
    items = _topic(game_env.module, "fren152-w7-vocab-fs07")["items"]
    assert [i["fr"] for i in items][:2] == ["en vitrine", "la pointure au-dessus"]
    assert len(items) == 10


def test_only_the_real_person_by_person_tables_count_as_conjugations(game_env):
    """A sentence list that merely starts with pronouns must not become a conjugation plot (the
    pronoun swap would write nonsense); only the declared tables are."""
    module = game_env.module
    found = sorted(
        p.topic_id for p in game_env.state.plots
        if "-fs" in p.topic_id and module.is_conjugation_plot(p)
    )
    assert found == sorted(DECLARED_CONJUGATION_TABLES)


DECLARED_CONJUGATION_TABLES = [
    "fren152-w3-grammar-fs01", "fren152-w3-grammar-fs02", "fren152-w3-grammar-fs03",
]
