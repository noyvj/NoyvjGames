"""Improvement Ideas addendum: a gender-tagging drill -- masc/fem tested
separately from meaning. Only a vocab noun whose own catalog text leads
with an unambiguous "le "/"la " article is eligible; an elided "l'" gives
no gender away and is deliberately left out rather than guessed at.
"""


def _plot_for_fr(state, fr_text):
    return next(p for p in state.plots if p.items[0].get("fr") == fr_text)


def test_gender_tag_parts_splits_an_unambiguous_masculine_noun(game_env):
    module = game_env.module
    assert module.gender_tag_parts("le tourisme") == ("le", "tourisme")


def test_gender_tag_parts_splits_an_unambiguous_feminine_noun(game_env):
    module = game_env.module
    assert module.gender_tag_parts("la mode") == ("la", "mode")


def test_gender_tag_parts_rejects_an_elided_article(game_env):
    """"l'" doesn't reveal gender at all -- must not be guessed at."""
    module = game_env.module
    assert module.gender_tag_parts("l'informatique") is None


def test_gender_tag_parts_rejects_text_with_no_leading_article(game_env):
    module = game_env.module
    assert module.gender_tag_parts("bonjour") is None
    assert module.gender_tag_parts("lentement") is None  # "le" is not a word boundary here


def test_a_masculine_vocab_plot_offers_the_gender_tag_variant(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "le tourisme")
    assert module.V_GENDER_TAG in module.variants_for(plot)


def test_a_plot_with_an_elided_article_does_not_offer_the_gender_tag_variant(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "l'informatique")
    assert module.V_GENDER_TAG not in module.variants_for(plot)


def test_a_grammar_plot_never_offers_the_gender_tag_variant(game_env):
    """Grammar plots are one plot per rule, not per noun -- even one whose
    example text happens to start with "Le " (a full sentence, not a bare
    noun) must not be mistaken for a drillable gendered noun."""
    module, state = game_env.module, game_env.state
    grammar_plot = next(p for p in state.plots if p.topic_type == "grammar")
    assert module.V_GENDER_TAG not in module.variants_for(grammar_plot)


def test_the_gender_tag_question_shows_the_bare_noun_and_two_articles(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "le tourisme")
    question = module.generate_question(plot, variant=module.V_GENDER_TAG)
    assert question["mode"] == "choice"
    assert question["prompt"] == "tourisme"
    assert set(question["choices"]) == {"le", "la"}
    assert question["answer"] == "le"
    assert question["note"] is None


def test_the_gender_tag_question_never_shows_the_english_meaning(game_env):
    """The whole point is testing gender apart from meaning -- "fashion"
    must not leak into the prompt, choices, or note for "la mode"."""
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "la mode")
    assert plot.items[0]["en"] == "fashion"
    question = module.generate_question(plot, variant=module.V_GENDER_TAG)
    assert "fashion" not in question["prompt"].lower()
    assert not any("fashion" in choice.lower() for choice in question["choices"])


def test_a_feminine_noun_answers_la(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "la mode")
    question = module.generate_question(plot, variant=module.V_GENDER_TAG)
    assert question["prompt"] == "mode"
    assert question["answer"] == "la"


def test_answering_the_gender_tag_question_correctly_grows_the_plot(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "le tourisme")
    module.open_practice(plot.plot_id, variant=module.V_GENDER_TAG)
    module.submit_answer("le")
    assert module.current_result is True
    assert plot.stage != module.STAGE_SEED


def test_answering_the_gender_tag_question_incorrectly_does_not_grow_the_plot(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "le tourisme")
    module.open_practice(plot.plot_id, variant=module.V_GENDER_TAG)
    module.submit_answer("la")
    assert module.current_result is False
    assert plot.stage == module.STAGE_SEED
