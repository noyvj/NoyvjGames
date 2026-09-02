"""Milestone 3: the runtime question generator (design doc §5).

Questions are *generated* from the catalog's raw fr/en facts every time a plot
is watered — never reproduced from the workbook's own exercises, dialogues or
puzzles. `test_every_generated_string_is_recombined_catalog_text` is the guard
on that constraint; the rest cover variant coverage and distractor plausibility.
"""

import random

import pytest


def _rng(seed=7):
    return random.Random(seed)


def _all_plots(game_env):
    return game_env.state.plots


# --- variant coverage ------------------------------------------------------


def test_every_plot_has_at_least_three_variants(game_env):
    module = game_env.module
    for plot in _all_plots(game_env):
        variants = module.variants_for(plot)
        assert len(variants) >= 3, f"{plot.plot_id} only has {variants}"
        assert len(set(variants)) == len(variants)


def test_vocab_plots_offer_both_directions(game_env):
    module = game_env.module
    plot = next(p for p in _all_plots(game_env) if p.topic_type == "vocab")
    variants = module.variants_for(plot)
    assert module.V_FR_EN_CHOICE in variants
    assert module.V_EN_FR_CHOICE in variants


def test_phrase_plots_use_the_same_translate_variants_as_vocab(game_env):
    module = game_env.module
    phrase = next(p for p in _all_plots(game_env) if p.topic_type == "phrase")
    assert module.V_FR_EN_CHOICE in module.variants_for(phrase)


def test_phonetic_plots_match_symbol_and_spoken_name(game_env):
    module = game_env.module
    phonetic = next(p for p in _all_plots(game_env) if p.topic_type == "phonetic")
    variants = module.variants_for(phonetic)
    assert module.V_SYMBOL_NAME_CHOICE in variants
    assert module.V_NAME_SYMBOL_CHOICE in variants


def test_grammar_plots_offer_a_fill_in_the_blank(game_env):
    module = game_env.module
    grammar = next(p for p in _all_plots(game_env) if p.topic_type == "grammar")
    assert module.V_BLANK_WORD in module.variants_for(grammar)


def test_conjugation_topics_get_the_pronoun_swap_variants(game_env):
    module = game_env.module
    conj = [p for p in _all_plots(game_env) if module.is_conjugation_plot(p)]
    # Exactly 10 grammar topics in the catalog are genuine person-by-person
    # verb tables: 3+ examples that each begin with a pronoun and continue
    # with one short form, across 2+ distinct pronouns. The catalog's other
    # verb topics pack a whole table (or two verbs) into a single string
    # ("je bois / tu bois / il boit") or are sentence examples — swapping a
    # pronoun into those would produce nonsense, so they must not qualify.
    assert len(conj) == 10
    for plot in conj:
        assert module.V_CONJUGATION_SWAP in module.variants_for(plot)


def test_non_conjugation_grammar_never_gets_the_pronoun_swap(game_env):
    module = game_env.module
    for plot in _all_plots(game_env):
        if plot.topic_type == "grammar" and not module.is_conjugation_plot(plot):
            assert module.V_CONJUGATION_SWAP not in module.variants_for(plot)


# --- generated question shape ---------------------------------------------


REQUIRED_KEYS = {
    "plot_id",
    "variant",
    "topic_type",
    "context",
    "instruction",
    "prompt",
    "note",
    "mode",
    "choices",
    "answer",
}


def test_generated_question_has_the_full_shape(game_env):
    module = game_env.module
    plot = _all_plots(game_env)[2]
    question = module.generate_question(plot, _rng())

    assert set(question) == REQUIRED_KEYS
    assert question["plot_id"] == plot.plot_id
    assert question["mode"] in {"choice", "typed"}
    assert question["prompt"]
    assert question["answer"]
    assert question["context"]


def test_every_plot_and_every_variant_generates_a_valid_question(game_env):
    """Smoke test across the whole 722-plot farm — no variant may raise, and
    every multiple-choice question must be answerable."""
    module = game_env.module
    rng = _rng(11)
    for plot in _all_plots(game_env):
        for variant in module.variants_for(plot):
            question = module.generate_question(plot, rng, variant=variant)
            assert question["variant"] == variant
            assert question["answer"].strip()
            assert question["prompt"].strip()
            if question["mode"] == "choice":
                assert len(question["choices"]) == module.QUESTION_CHOICE_COUNT
                assert question["answer"] in question["choices"]
                assert len(set(question["choices"])) == len(question["choices"])
            else:
                assert question["choices"] == []
            assert module.check_answer(question, question["answer"]) is True


def test_context_line_names_the_syllabus_placement(game_env):
    module = game_env.module
    plot = _all_plots(game_env)[0]
    context = module.generate_question(plot, _rng())["context"]
    assert "FREN151" in context
    assert "wk 1" in context
    assert plot.topic_title in context


def test_grammar_questions_surface_the_rule_as_a_note(game_env):
    module = game_env.module
    plot = next(p for p in _all_plots(game_env) if p.topic_type == "grammar" and p.rule)
    question = module.generate_question(plot, _rng(), variant=module.V_BLANK_WORD)
    assert question["note"] == plot.rule


# --- distractors -----------------------------------------------------------


def test_distractors_come_from_the_same_or_a_nearby_topic(game_env):
    """§5: distractors are pulled from other items in the same or a nearby
    topic, so they stay plausible rather than random noise."""
    module, state = game_env.module, game_env.state
    for plot in state.plots[:120]:
        for variant in module.variants_for(plot):
            question = module.generate_question(plot, _rng(3), variant=variant)
            if question["mode"] != "choice":
                continue
            nearby = module.nearby_strings(state, plot)
            for choice in question["choices"]:
                if choice == question["answer"]:
                    continue
                assert choice in nearby, f"{choice!r} for {plot.plot_id}/{variant}"


def test_distractors_never_repeat_the_answer(game_env):
    module = game_env.module
    rng = _rng(5)
    for plot in _all_plots(game_env)[:200]:
        question = module.generate_question(plot, rng)
        if question["mode"] == "choice":
            assert question["choices"].count(question["answer"]) == 1


def test_conjugation_swap_asks_for_one_person_of_the_verb(game_env):
    """The doc's own spec: 'conjugation items get a pronoun swapped in from the
    six-person set so the blank changes each visit.'"""
    module = game_env.module
    plot = next(p for p in _all_plots(game_env) if module.is_conjugation_plot(p))
    forms = {module.split_pronoun(i["fr"])[1] for i in plot.items if module.split_pronoun(i["fr"])}
    pronouns = {module.split_pronoun(i["fr"])[0] for i in plot.items if module.split_pronoun(i["fr"])}
    assert len(pronouns) >= 3

    seen_pronouns = set()
    for seed in range(25):
        question = module.generate_question(
            plot, _rng(seed), variant=module.V_CONJUGATION_SWAP
        )
        assert question["answer"] in forms
        assert any(question["prompt"].startswith(p) for p in pronouns)
        assert set(question["choices"]) <= forms
        seen_pronouns.add(question["prompt"].split("_")[0].strip())

    # Re-rolling really does swap the pronoun rather than fixing on one.
    assert len(seen_pronouns) >= 3


def test_blank_variants_hide_the_answer_in_the_prompt(game_env):
    module = game_env.module
    for plot in _all_plots(game_env):
        for variant in (module.V_BLANK_WORD, module.V_CONJUGATION_SWAP):
            if variant not in module.variants_for(plot):
                continue
            question = module.generate_question(plot, _rng(2), variant=variant)
            assert module.BLANK_MARKER in question["prompt"]
            assert question["answer"] not in question["prompt"].split()


def test_blank_target_accepts_either_form_of_a_masc_fem_pair(game_env):
    """A single-word "/" pair (e.g. "australien / australienne") is blanked
    as one unit, and the answer stays "/"-joined so either gendered form is
    accepted -- typing the masculine form when the feminine was "the"
    target (or vice versa) shouldn't be marked wrong."""
    module = game_env.module
    blanked, answer = module.blank_target("australien / australienne")
    assert blanked == module.BLANK_MARKER
    assert answer == "australien / australienne"

    question = {"mode": "typed", "answer": answer, "choices": []}
    assert module.check_answer(question, "australien") is True
    assert module.check_answer(question, "australienne") is True
    assert module.check_answer(question, "canadien") is False


def test_blank_target_refuses_to_blank_across_full_alternate_phrases(game_env):
    """"Comment vas-tu? / Ça va?" packs two genuinely different phrasings,
    not a one-word variant -- blanking a word inside one of them while the
    other sits fully visible ("Comment vas-tu? / Ça _____?") is a garbled
    question, so word-blanking is refused entirely here. The item still
    gets asked via direct translate/choice, which already accept either
    side of a "/"."""
    module = game_env.module
    assert module.blank_target("Comment vas-tu? / Ça va?") is None
    assert module.blank_target("un professeur / une professeure") is None
    assert module.blank_target("un / une élève") is None


def test_blank_target_ignores_a_slash_embedded_in_one_word(game_env):
    """A "/" with no surrounding whitespace, like the catalog's own
    "[places/attractions]" placeholder, is part of that single token, not
    an alternation separator -- it must fall through to the normal
    single-word blanking algorithm rather than being treated as a pair."""
    module = game_env.module
    result = module.blank_target("... parce qu'il y a + [places/attractions]")
    assert result is not None
    blanked, answer = result
    assert "/" not in answer


def test_blank_target_handles_a_slash_pair_with_inflection_parentheses(game_env):
    """"meilleur(e)(s) / pire(s)" (fren152-w4-grammar003) combines both
    things this function has to see through: parenthetical inflection
    markers, and a masc/fem-style "/" pair."""
    module = game_env.module
    blanked, answer = module.blank_target("meilleur(e)(s) / pire(s)")
    assert answer == "meilleur / pire"
    question = {"mode": "typed", "answer": answer, "choices": []}
    assert module.check_answer(question, "meilleur") is True
    assert module.check_answer(question, "pire") is True


def test_plot_that_lost_its_blank_variant_still_meets_the_variant_floor(game_env):
    """Regression guard: fren151-w6-phrase002-i02's fr text contains a
    bracketed "/" placeholder ("[places/attractions]"), which must NOT be
    mistaken for a whitespace-bounded alternation -- confirms the specific
    plot that surfaced this during development still has enough variants."""
    module = game_env.module
    plot = next(
        p for p in _all_plots(game_env) if p.plot_id == "fren151-w6-phrase002-i02"
    )
    assert len(module.variants_for(plot)) >= 3


def test_blank_ending_shows_the_stem_and_hides_the_whole_form(game_env):
    """The ending blank is only offered where a topic's forms genuinely share
    a stem (regular conjugation tables), and it must show that stem while
    hiding the complete form."""
    module = game_env.module
    offered = [p for p in _all_plots(game_env) if module.V_BLANK_ENDING in module.variants_for(p)]
    assert offered, "some conjugation tables should support an ending blank"
    for plot in offered:
        question = module.generate_question(plot, _rng(), variant=module.V_BLANK_ENDING)
        prompt = question["prompt"]
        assert module.BLANK_MARKER in prompt
        stem = prompt.split(module.BLANK_MARKER)[0].strip().split()[-1]
        assert stem
        full_form = stem + question["answer"]
        assert full_form not in prompt.split()
        assert any(full_form in module.strip_parentheticals(i["fr"]) for i in plot.items)


# --- re-rolling ------------------------------------------------------------


def test_watering_the_same_plot_twice_rarely_repeats_the_question(game_env):
    module = game_env.module
    plot = next(p for p in _all_plots(game_env) if p.topic_type == "vocab")
    seen = set()
    for seed in range(30):
        question = module.generate_question(plot, _rng(seed))
        seen.add((question["variant"], question["prompt"], tuple(question["choices"])))
    assert len(seen) >= 8


def test_generation_is_deterministic_for_a_given_seed(game_env):
    module = game_env.module
    plot = _all_plots(game_env)[4]
    first = module.generate_question(plot, _rng(99))
    second = module.generate_question(plot, _rng(99))
    assert first == second


def test_exclude_avoids_repeating_the_previous_variant(game_env):
    module = game_env.module
    plot = _all_plots(game_env)[0]
    variants = module.variants_for(plot)
    for seed in range(15):
        question = module.generate_question(plot, _rng(seed), exclude=variants[0])
        assert question["variant"] != variants[0]


def test_exclude_is_ignored_when_it_would_leave_nothing(game_env):
    module = game_env.module
    plot = _all_plots(game_env)[0]
    variants = module.variants_for(plot)
    question = module.generate_question(plot, _rng(), exclude=variants)
    assert question["variant"] in variants


# --- answer checking -------------------------------------------------------


def test_typed_answers_are_checked_leniently(game_env):
    module = game_env.module
    question = {"mode": "typed", "answer": "élève", "choices": []}
    assert module.check_answer(question, "élève") is True
    assert module.check_answer(question, "  ÉLÈVE ") is True
    assert module.check_answer(question, "eleve") is True
    assert module.check_answer(question, "élève.") is True
    assert module.check_answer(question, "professeur") is False
    assert module.check_answer(question, "") is False


def test_typed_answers_accept_either_side_of_a_slash(game_env):
    module = game_env.module
    question = {"mode": "typed", "answer": "a rubber/eraser", "choices": []}
    assert module.check_answer(question, "a rubber") is True
    assert module.check_answer(question, "eraser") is True
    assert module.check_answer(question, "a rubber/eraser") is True


def test_typed_answers_forgive_a_leading_article(game_env):
    module = game_env.module
    question = {"mode": "typed", "answer": "a chair", "choices": []}
    assert module.check_answer(question, "chair") is True


def test_typed_answers_forgive_a_dropped_plus_placeholder(game_env):
    """Template items like "I am + [nationality]" (fren151-w4-phrase002)
    are answers to a translate-the-pattern question -- the placeholder
    itself was never something to type."""
    module = game_env.module
    question = {"mode": "typed", "answer": "I am + [nationality]", "choices": []}
    assert module.check_answer(question, "I am") is True
    assert module.check_answer(question, "i am") is True
    # Typing the whole thing verbatim, placeholder included, still works too.
    assert module.check_answer(question, "I am + [nationality]") is True

    question_fr = {"mode": "typed", "answer": "Je suis + [occupation]", "choices": []}
    assert module.check_answer(question_fr, "je suis") is True


def test_typed_answers_accept_either_direction_of_a_contraction(game_env):
    module = game_env.module
    question = {"mode": "typed", "answer": "it's + [adjective]", "choices": []}
    assert module.check_answer(question, "it's") is True
    assert module.check_answer(question, "it is") is True

    question2 = {"mode": "typed", "answer": "I am not hungry", "choices": []}
    # No contraction present in the catalog answer at all -- unaffected.
    assert module.check_answer(question2, "I am not hungry") is True

    question3 = {"mode": "typed", "answer": "we are happy", "choices": []}
    assert module.check_answer(question3, "we're happy") is True

    question4 = {"mode": "typed", "answer": "he does not know", "choices": []}
    assert module.check_answer(question4, "he doesn't know") is True


def test_typed_answers_accept_belgian_swiss_number_words(game_env):
    """70/80/90 also have Belgian/Swiss French words (septante/huitante/
    nonante) instead of the France-standard compounds -- both are correct
    French, so both are accepted."""
    module = game_env.module

    seventy = {"mode": "typed", "answer": "soixante-dix", "choices": []}
    assert module.check_answer(seventy, "soixante-dix") is True
    assert module.check_answer(seventy, "septante") is True

    eighty = {"mode": "typed", "answer": "quatre-vingts", "choices": []}
    assert module.check_answer(eighty, "quatre-vingts") is True
    assert module.check_answer(eighty, "huitante") is True

    ninety = {"mode": "typed", "answer": "quatre-vingt-dix", "choices": []}
    assert module.check_answer(ninety, "quatre-vingt-dix") is True
    assert module.check_answer(ninety, "nonante") is True
    assert module.check_answer(ninety, "neufante") is True

    # Doesn't leak into unrelated numbers.
    sixty = {"mode": "typed", "answer": "soixante", "choices": []}
    assert module.check_answer(sixty, "septante") is False


def test_multiple_choice_answers_must_match_exactly(game_env):
    module = game_env.module
    question = {"mode": "choice", "answer": "bonjour", "choices": ["bonjour", "salut"]}
    assert module.check_answer(question, "bonjour") is True
    assert module.check_answer(question, "salut") is False


# --- the copyright constraint ---------------------------------------------


def test_every_generated_string_is_recombined_catalog_text(game_env):
    """Hard constraint from §4/§5: the game may only ever recombine the
    catalog's own raw fr/en facts. Nothing a player sees may be anything other
    than catalog text plus this file's own fixed UI scaffolding."""
    module, state = game_env.module, game_env.state
    catalog_text = set()

    def _add(raw):
        # Both the raw text and its parenthetical-stripped form count as
        # catalog-derived -- strip_parentheticals() is an established part
        # of the game's own answer-construction pipeline (blank_target(),
        # answer_alternatives()), not a new way to slip in invented text.
        # This matters for items like "meilleur(e)(s) / pire(s)", where the
        # blanked-word-pair answer ("meilleur / pire") only lines up with
        # the catalog once the inflection parentheses are gone too.
        catalog_text.add(module.normalize_answer(raw))
        catalog_text.add(module.normalize_answer(module.strip_parentheticals(raw)))

    for week in module.CATALOG["weeks"]:
        for topic in week["topics"]:
            _add(topic["title"])
            if topic.get("rule"):
                _add(topic["rule"])
            for item in topic["items"]:
                _add(item["fr"])
                _add(item["en"])

    def is_catalog_derived(text):
        needle = module.normalize_answer(text)
        return any(needle and needle in source for source in catalog_text)

    rng = _rng(13)
    for plot in state.plots:
        for variant in module.variants_for(plot):
            question = module.generate_question(plot, rng, variant=variant)
            assert is_catalog_derived(question["answer"]), question
            for choice in question["choices"]:
                assert is_catalog_derived(choice), question
            if question["note"]:
                assert is_catalog_derived(question["note"]), question


def test_instructions_are_this_games_own_wording_not_the_workbooks(game_env):
    """The only non-catalog text in a question is the fixed instruction line,
    which is written here and enumerable."""
    module = game_env.module
    rng = _rng(17)
    seen = set()
    for plot in game_env.state.plots:
        for variant in module.variants_for(plot):
            seen.add(module.generate_question(plot, rng, variant=variant)["instruction"])
    assert seen <= set(module.INSTRUCTIONS.values())


@pytest.mark.parametrize("topic_type", ["vocab", "phrase", "grammar", "phonetic"])
def test_each_topic_type_is_actually_represented_in_the_farm(game_env, topic_type):
    assert any(p.topic_type == topic_type for p in game_env.state.plots)
