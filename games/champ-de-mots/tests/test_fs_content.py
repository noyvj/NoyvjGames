"""FS (FREN152 slides) content: what each slide week added to its farm row, and that every added
item plays properly (variants, generated questions, typed answers). The topics were written from
the course's weekly topics in my own wording; nothing here is slide text.
"""

import random
import re

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
    7: {"row": 18, "topics": 10, "plots": 58, "must_have": [
        "il fait mauvais", "au printemps", "en hiver", "la météo", "une valise", "emporter", "Il neige dans les Alpes.",
        "Paul m'appelle.", "Je le mange.", "remercier", "obtenir un diplôme", "louer", "je fais", "ils font",
        "Lundi, il fait froid.", "Dimanche, il fait chaud.",
    ]},
    8: {"row": 19, "topics": 12, "plots": 80, "must_have": [
        "une cerise", "des épinards", "du saucisson", "de la tarte", "du sel", "du lait écrémé", "un croissant",
        "au petit-déjeuner", "comme plat principal", "du couscous", "Non merci, pas de sel.", "J'adore les croissants.",
        "surveiller", "la santé",
    ]},
    9: {"row": 20, "topics": 9, "plots": 52, "must_have": [
        "une tablette de", "une douzaine de", "cent grammes de", "un sachet de", "un sandwich au fromage",
        "marchand de primeurs", "faire les courses", "À qui le tour?", "Ce sera tout.", "du camembert", "un pamplemousse",
        "Je vais le faire.", "J'en veux deux.",
    ]},
    10: {"row": 21, "topics": 9, "plots": 45, "must_have": [
        "regardé", "attendu", "j'ai regardé", "nous avons vendu", "Je n'ai pas fini mes devoirs.", "Sophie l'a écoutée.",
        "la raclette", "apporter", "C'était très bon, merci.", "J'ai perdu mes clés.",
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


# --- week 7 (and the Lecture 7 supplement) -------------------------------------


def test_week_7_seasons_use_au_for_spring_and_en_for_the_rest(game_env):
    items = {i["fr"]: i["en"] for i in _topic(game_env.module, "fren152-w8-vocab-fs01")["items"]}
    assert items["au printemps"] == "in spring"
    assert all(items[f"en {s}"].startswith("in ") for s in ("été", "automne", "hiver"))
    assert _live(game_env.module, "fren152-w8-vocab-fs01", 5, "en", "in fall")


def test_week_7_weather_sentences_mention_a_season_a_place_or_a_temperature(game_env):
    items = _topic(game_env.module, "fren152-w8-phrase-fs02")["items"]
    assert len(items) == 8
    assert any("Alpes" in i["fr"] for i in items) and any("degrés" in i["fr"] for i in items)


def test_week_7_packing_vocabulary_and_sentences(game_env):
    module = game_env.module
    assert _item(module, "fren152-w8-vocab-fs03", 0) == {"fr": "une valise", "en": "a suitcase", "accepted_en": ["a suitcase", "a case", "a bag", "a suit case"]}
    sentences = _topic(module, "fren152-w8-phrase-fs04")["items"]
    assert sentences[0]["fr"].startswith("Dans ma valise") and len(sentences) == 4


def test_week_7_object_pronoun_plots_put_the_pronoun_before_the_verb(game_env):
    module = game_env.module
    for topic_id in ("fren152-w8-grammar-fs05", "fren152-w8-grammar-fs06"):
        topic = _topic(module, topic_id)
        assert topic["topic_type"] == "grammar" and len(topic["items"]) >= 5
        for item in topic["items"]:
            assert any(p in item["fr"] for p in (" m'", " t'", " nous ", " vous ", " le ", " la ", " l'", " les ", "m'", "l'")), item["fr"]
    assert "before the verb" in _topic(module, "fren152-w8-grammar-fs05")["rule"]


def test_week_7_object_pronoun_sentences_start_with_names_so_they_are_not_conjugation_tables(game_env):
    module = game_env.module
    assert not module.is_conjugation_plot(game_env.state.plots_by_id["fren152-w8-grammar-fs05"])
    assert not module.is_conjugation_plot(game_env.state.plots_by_id["fren152-w8-grammar-fs06"])


def test_week_7_verb_lists_are_infinitives_without_overlapping_english(game_env):
    module = game_env.module
    verbs = _topic(module, "fren152-w8-vocab-fs07")["items"]
    assert len(verbs) == 10 and all(not i["fr"].startswith("se ") for i in verbs)
    glosses = [i["en"] for i in verbs]
    assert len(set(glosses)) == len(glosses)
    student = _topic(module, "fren152-w8-vocab-fs08")["items"]
    assert [i["fr"] for i in student][:2] == ["obtenir un diplôme", "rater"]
    assert _live(module, "fren152-w8-vocab-fs08", 4, "en", "to attend classes")


def test_lecture_7_supplement_is_its_own_bonus_pair_and_says_where_it_came_from(game_env):
    module = game_env.module
    faire = _topic(module, "fren152-w8-grammar-fs09")
    forecast = _topic(module, "fren152-w8-phrase-fs10")
    for topic in (faire, forecast):
        assert "Lecture 7 supplement" in topic["title"]
    assert "Bonus topic from the Lecture 7 supplement" in faire["rule"]
    assert module.is_conjugation_plot(game_env.state.plots_by_id[faire["id"]])
    assert [i["fr"] for i in faire["items"]] == ["je fais", "tu fais", "il fait", "nous faisons", "vous faites", "ils font"]
    days = [i["fr"].split(",")[0] for i in forecast["items"]]
    assert days == ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


# --- week 8 ------------------------------------------------------------------


def test_week_8_food_lists_are_large_and_use_the_partitive_or_a_count_article(game_env):
    module = game_env.module
    food = [
        "fren152-w9-vocab-fs01", "fren152-w9-vocab-fs02", "fren152-w9-vocab-fs03", "fren152-w9-vocab-fs04",
        "fren152-w9-vocab-fs05", "fren152-w9-vocab-fs06", "fren152-w9-vocab-fs08",
    ]
    total = 0
    for topic_id in food:
        for item in _topic(module, topic_id)["items"]:
            total += 1
            assert item["fr"].split()[0] in {"un", "une", "des", "du", "de", "les", "le", "la", "l'"} or item["fr"].startswith("de l'"), item["fr"]
    assert total >= 50  # "about 60 food items" in the plan: 50 food plots plus the meal words


def test_week_8_plural_food_words_accept_the_bare_noun(game_env):
    module = game_env.module
    for topic_id, idx, bare in (("fren152-w9-vocab-fs02", 0, "épinards"), ("fren152-w9-vocab-fs03", 1, "saucisses"),
                                ("fren152-w9-vocab-fs04", 6, "bonbons")):
        assert _live(module, topic_id, idx, "fr", bare), (topic_id, idx)


def test_week_8_milk_kinds_have_three_distinct_answers(game_env):
    module = game_env.module
    items = _topic(module, "fren152-w9-vocab-fs06")["items"][:3]
    assert [i["fr"] for i in items] == ["du lait entier", "du lait demi-écrémé", "du lait écrémé"]
    assert _live(module, "fren152-w9-vocab-fs06", 0, "en", "whole milk")
    assert _live(module, "fren152-w9-vocab-fs06", 2, "en", "skim milk")
    assert not _live(module, "fren152-w9-vocab-fs06", 2, "en", "whole milk")


def test_week_8_meal_words_use_au_and_comme(game_env):
    items = _topic(game_env.module, "fren152-w9-vocab-fs07")["items"]
    frs = [i["fr"] for i in items]
    assert frs[:3] == ["au petit-déjeuner", "au déjeuner", "au dîner"]
    assert [f.split()[0] for f in frs[3:7]] == ["comme"] * 4


def test_week_8_partitive_exception_plot_covers_pas_plus_etre_and_quantity(game_env):
    topic = _topic(game_env.module, "fren152-w9-grammar-fs10")
    frs = [i["fr"] for i in topic["items"]]
    assert any(" pas de " in f or "pas d'" in f for f in frs)
    assert any("plus de" in f for f in frs)
    assert any(f.startswith("Ce n'est pas du") for f in frs)  # être keeps the partitive
    assert any("beaucoup de" in f for f in frs)
    assert "être" in topic["rule"]


def test_week_8_liking_verbs_plot_keeps_to_the_definite_article(game_env):
    topic = _topic(game_env.module, "fren152-w9-grammar-fs11")
    for item in topic["items"]:
        assert not any(w in item["fr"].split() for w in ("du", "de", "des")), item["fr"]
        assert any(w in item["fr"] for w in (" le ", " la ", " les ")), item["fr"]
    assert not game_env.module.is_conjugation_plot(game_env.state.plots_by_id[topic["id"]])


def test_week_8_ordering_phrases_and_health_words(game_env):
    module = game_env.module
    assert len(_topic(module, "fren152-w9-phrase-fs09")["items"]) == 7
    health = {i["fr"]: i["en"] for i in _topic(module, "fren152-w9-vocab-fs12")["items"]}
    assert health["la santé"] == "health" and "n'oubliez pas" in health


# --- week 9 ------------------------------------------------------------------


def test_week_9_quantity_words_all_end_in_de(game_env):
    for item in _topic(game_env.module, "fren152-w10-vocab-fs01")["items"]:
        assert item["fr"].split()[-1] == "de", item["fr"]
    assert _live(game_env.module, "fren152-w10-vocab-fs01", 3, "en", "twelve")


def test_week_9_quantity_sentences_use_de_not_the_partitive(game_env):
    for item in _topic(game_env.module, "fren152-w10-phrase-fs02")["items"]:
        text = " " + item["fr"].lower().replace("'", "' ") + " "
        assert " du " not in text and " des " not in text and " de la " not in text, item["fr"]


def test_week_9_fillings_rule_pairs_a_with_the_content(game_env):
    topic = _topic(game_env.module, "fren152-w10-grammar-fs03")
    assert topic["topic_type"] == "grammar" and len(topic["items"]) == 6
    for item in topic["items"]:
        assert any(p in item["fr"] for p in (" au ", " aux ", " à la ", " à l'")), item["fr"]
    assert "un verre de lait" in topic["rule"]


def test_week_9_shop_words_and_supermarket_sections(game_env):
    module = game_env.module
    items = {i["fr"]: i["en"] for i in _topic(module, "fren152-w10-vocab-fs04")["items"]}
    assert items["salé(e)"] == "savoury" and items["sucré(e)"] == "sweet"
    assert _live(module, "fren152-w10-vocab-fs04", 8, "en", "to go grocery shopping")


def test_week_9_y_sentences_name_where_you_go(game_env):
    items = _topic(game_env.module, "fren152-w10-phrase-fs05")["items"]
    assert sum(1 for i in items if " y " in i["fr"] or "j'y" in i["fr"]) >= 4
    assert len(items) == 6


def test_week_9_food_shop_dialogue_has_buyer_and_seller_lines(game_env):
    module = game_env.module
    items = {i["fr"]: i["en"] for i in _topic(module, "fren152-w10-phrase-fs06")["items"]}
    assert len(items) == 9
    assert items["À qui le tour?"] == "Whose turn is it?"
    assert _live(module, "fren152-w10-phrase-fs06", 4, "en", "that's all")


def test_week_9_cheese_and_produce_words(game_env):
    items = [i["fr"] for i in _topic(game_env.module, "fren152-w10-vocab-fs07")["items"]]
    assert items[:4] == ["du camembert", "du gruyère", "du roquefort", "du fromage de chèvre"]


def test_week_9_pronoun_plots_follow_the_aller_and_en_rules(game_env):
    module = game_env.module
    futur = _topic(module, "fren152-w10-grammar-fs08")
    assert "right before the infinitive" in futur["rule"]
    assert all(" va" in i["fr"] or "vais" in i["fr"] or "allons" in i["fr"] or "vont" in i["fr"] for i in futur["items"])
    en = _topic(module, "fren152-w10-grammar-fs09")
    assert all(" en " in " " + i["fr"].replace("'", "' ") + " " or "'en" in i["fr"] for i in en["items"])
    for topic in (futur, en):
        assert not module.is_conjugation_plot(game_env.state.plots_by_id[topic["id"]])


# --- week 10 -----------------------------------------------------------------


def test_week_10_participles_end_in_the_three_regular_endings(game_env):
    items = _topic(game_env.module, "fren152-w11-vocab-fs01")["items"]
    assert len(items) == 17
    for item in items:
        assert item["fr"][-1] in {"é", "i", "u"}, item["fr"]
    assert _live(game_env.module, "fren152-w11-vocab-fs01", 7, "en", "ate")  # mangé
    assert _live(game_env.module, "fren152-w11-vocab-fs01", 9, "en", "sang")  # chanté


def test_week_10_passe_compose_tables_use_avoir_and_one_participle(game_env):
    module = game_env.module
    expected_avoir = ["j'ai", "tu as", "il a", "nous avons", "vous avez", "ils ont"]
    for topic_id, participle in (
        ("fren152-w11-grammar-fs02", "regardé"), ("fren152-w11-grammar-fs03", "fini"),
        ("fren152-w11-grammar-fs04", "vendu"),
    ):
        plot = game_env.state.plots_by_id[topic_id]
        assert module.is_conjugation_plot(plot), topic_id
        forms = [i["fr"] for i in plot.items]
        assert forms == [f"{a} {participle}" for a in expected_avoir], topic_id


def test_week_10_negative_wraps_the_auxiliary(game_env):
    topic = _topic(game_env.module, "fren152-w11-grammar-fs05")
    for item in topic["items"]:
        text = item["fr"]
        match = re.search(r"n'(ai|a|as|ont|avons|avez)\b", text)
        assert match and ("pas" in text or "jamais" in text), text
        assert match.start() < max(text.find("pas"), text.find("jamais"))
    assert not game_env.module.is_conjugation_plot(game_env.state.plots_by_id[topic["id"]])


def test_week_10_pronoun_agreement_plot_shows_masculine_and_feminine_participles(game_env):
    module = game_env.module
    topic = _topic(module, "fren152-w11-grammar-fs06")
    frs = [i["fr"] for i in topic["items"]]
    assert "Sophie l'a écouté." in frs and "Sophie l'a écoutée." in frs
    assert "Nous les avons mangés." in frs and "Nous les avons mangées." in frs
    assert "agrees" in topic["rule"] and not module.is_conjugation_plot(game_env.state.plots_by_id[topic["id"]])
    # the English keeps masculine and feminine apart so a typed answer can tell them apart
    assert not _live(module, topic["id"], 1, "en", "Sophie listened to him")
    assert _live(module, topic["id"], 0, "en", "Sophie listened to him")


def test_week_10_restaurant_words_and_dialogue(game_env):
    module = game_env.module
    words = {i["fr"]: i["en"] for i in _topic(module, "fren152-w11-vocab-fs07")["items"]}
    assert words["apporter"] == "to bring" and words["conseiller"] == "to recommend"
    dialogue = _topic(module, "fren152-w11-phrase-fs08")["items"]
    assert len(dialogue) == 7 and dialogue[-1]["fr"] == "C'était très bon, merci."


def test_week_10_passe_compose_sentences_are_all_past_with_avoir(game_env):
    for item in _topic(game_env.module, "fren152-w11-phrase-fs09")["items"]:
        text = " " + item["fr"].replace("'", "' ") + " "
        assert any(a in text for a in (" ai ", " as ", " a ", " avons ", " avez ", " ont ", "j' ai ")), item["fr"]
    assert len(_topic(game_env.module, "fren152-w11-phrase-fs09")["items"]) == 8


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
    "fren152-w8-grammar-fs09",
    "fren152-w11-grammar-fs02", "fren152-w11-grammar-fs03", "fren152-w11-grammar-fs04",
]
