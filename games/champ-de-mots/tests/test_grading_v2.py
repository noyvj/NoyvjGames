"""Milestone 8: grading engine v2 (design doc §14.2).

Formalizes Milestone 3's leniency into explicit STRICT/LENIENT tiers decided
from an item's own shape, adds an accent-sensitivity toggle (default ON) and
a per-item `accepted` array (auto-generated, extensible by hand). None of
this replaces `check_answer`'s original two-argument signature -- every test
in `test_question_generator.py` still calls it that way, so this file pins
that the new `tier`/`accent_sensitive` machinery is purely additive.
"""

import re

import pytest


# --- grading_tier ------------------------------------------------------


def test_single_word_answers_are_strict(game_env):
    module = game_env.module
    assert module.grading_tier("bonjour") == module.TIER_STRICT
    assert module.grading_tier("chien") == module.TIER_STRICT


def test_multi_word_answers_are_lenient(game_env):
    module = game_env.module
    assert module.grading_tier("Il y a un théâtre.") == module.TIER_LENIENT
    assert module.grading_tier("There is a theatre.") == module.TIER_LENIENT


def test_numbers_and_hyphenated_compounds_stay_strict(game_env):
    """A hyphenated number like "quatre-vingt-dix" is one token, so it counts
    as a single-word answer even though it's several French words -- §14.2
    explicitly calls out numbers as a STRICT category."""
    module = game_env.module
    assert module.grading_tier("quatre-vingt-dix") == module.TIER_STRICT
    assert module.grading_tier("soixante-dix") == module.TIER_STRICT


def test_tier_is_judged_after_stripping_template_and_parenthetical_noise(game_env):
    module = game_env.module
    # "I am + [nationality]" is judged on "I am" (two words) -> LENIENT.
    assert module.grading_tier("I am + [nationality]") == module.TIER_LENIENT
    # "assez + adjective" is judged on "assez" (one word) -> STRICT.
    assert module.grading_tier("assez + adjective") == module.TIER_STRICT
    # A parenthetical inflection marker doesn't count as a second word.
    assert module.grading_tier("professeur(e)") == module.TIER_STRICT


def test_isolated_conjugated_forms_are_strict(game_env):
    module = game_env.module
    plot = next(p for p in game_env.state.plots if module.is_conjugation_plot(p))
    pronoun, form = module.conjugation_forms(plot)[0]
    assert module.grading_tier(form) == module.TIER_STRICT


# --- normalize_answer's accent-fold opt-out -----------------------------


def test_normalize_answer_still_folds_accents_by_default(game_env):
    """Unchanged from Milestone 3: every existing caller that doesn't pass
    the new `fold_accents` argument keeps seeing accent-insensitive text."""
    module = game_env.module
    assert module.normalize_answer("élève") == module.normalize_answer("eleve")


def test_normalize_answer_can_keep_accents_when_asked(game_env):
    module = game_env.module
    assert module.normalize_answer("élève", fold_accents=False) == "élève"
    assert module.normalize_answer("élève", fold_accents=False) != module.normalize_answer(
        "eleve", fold_accents=False
    )
    assert module.normalize_answer("ÉLÈVE", fold_accents=False) == module.normalize_answer(
        "élève", fold_accents=False
    )


# --- STRICT tier behaviour -----------------------------------------------


def test_strict_tier_is_exact_after_normalization(game_env):
    module = game_env.module
    question = {"mode": "typed", "answer": "bonjour", "choices": []}
    assert module.check_answer(question, "bonjour", tier=module.TIER_STRICT) is True
    assert module.check_answer(question, "  BONJOUR  ", tier=module.TIER_STRICT) is True
    assert module.check_answer(question, "bonjour.", tier=module.TIER_STRICT) is True
    assert module.check_answer(question, "salut", tier=module.TIER_STRICT) is False


def test_strict_tier_strips_parenthetical_suffix_like_lenient_already_did(game_env):
    """Report-queue review (2026-09-05) found several STRICT items --
    "gentil(le)", "culturel(le)", "intelligent(e)", "regarder (-er)",
    "cousin (m/f)" -- all rejecting the correct bare/base form, because
    strict_alternatives() never stripped the catalog's "(...)" suffix
    notation, unlike answer_alternatives()'s LENIENT path (which has done
    this since Milestone 3). grading_tier() already strips parentheticals
    *before counting words*, so these items were always routed to STRICT
    -- they just never got the same stripping applied once they got there."""
    module = game_env.module
    question = {"mode": "typed", "answer": "gentil(le)", "choices": []}
    assert module.grading_tier("gentil(le)") == module.TIER_STRICT
    assert module.check_answer(question, "gentil", tier=module.TIER_STRICT) is True
    assert module.check_answer(question, "gentil(le)", tier=module.TIER_STRICT) is True
    assert module.check_answer(question, "gentille", tier=module.TIER_STRICT) is False

    infinitive = {"mode": "typed", "answer": "regarder (-er)", "choices": []}
    assert module.check_answer(infinitive, "regarder", tier=module.TIER_STRICT) is True

    dual_gender = {"mode": "typed", "answer": "cousin (m/f)", "choices": []}
    assert module.check_answer(dual_gender, "cousin", tier=module.TIER_STRICT) is True


def test_strict_tier_has_no_synonym_list_lenient_tier_does(game_env):
    """The same item, judged both ways: LENIENT drops a leading article from
    the catalog answer as one of its curated phrasings; STRICT is exact
    match after normalization only, so it doesn't."""
    module = game_env.module
    question = {"mode": "typed", "answer": "a chair", "choices": []}
    assert module.check_answer(question, "chair", tier=module.TIER_LENIENT) is True
    assert module.check_answer(question, "chair", tier=module.TIER_STRICT) is False
    assert module.check_answer(question, "a chair", tier=module.TIER_STRICT) is True


def test_strict_tier_still_folds_contractions_and_number_regionalisms(game_env):
    """§14.2: contraction equivalence and (by extension) the number-
    regionalism table are shared normalization, not a synonym list, so they
    still apply even at STRICT."""
    module = game_env.module
    question = {"mode": "typed", "answer": "it's", "choices": []}
    assert module.check_answer(question, "it is", tier=module.TIER_STRICT) is True

    ninety = {"mode": "typed", "answer": "quatre-vingt-dix", "choices": []}
    assert module.check_answer(ninety, "nonante", tier=module.TIER_STRICT) is True


def test_strict_tier_default_accent_sensitive_toggle_matters(game_env):
    module = game_env.module
    question = {"mode": "typed", "answer": "élève", "choices": []}
    # accent_sensitive=True (the live default): a dropped accent is wrong.
    assert module.check_answer(question, "eleve", tier=module.TIER_STRICT, accent_sensitive=True) is False
    assert module.check_answer(question, "élève", tier=module.TIER_STRICT, accent_sensitive=True) is True
    # accent_sensitive=False (toggled off): back to the old lenient fold.
    assert module.check_answer(question, "eleve", tier=module.TIER_STRICT, accent_sensitive=False) is True
    # Omitted entirely: same as accent_sensitive=False, matching normalize_answer's own default.
    assert module.check_answer(question, "eleve", tier=module.TIER_STRICT) is True


# --- LENIENT tier / accepted-array integration ----------------------------


def test_lenient_tier_matches_legacy_behaviour_when_no_catalog_item_is_found(game_env):
    """A hand-built question dict with no real plot_id (as every pre-M8 test
    uses) still gets full leniency at the LENIENT tier -- `_lookup_accepted`
    degrades to "no extra variants" rather than raising."""
    module = game_env.module
    question = {"mode": "typed", "answer": "a rubber/eraser", "choices": []}
    assert module.check_answer(question, "a rubber", tier=module.TIER_LENIENT) is True
    assert module.check_answer(question, "eraser", tier=module.TIER_LENIENT) is True


def test_generate_accepted_variants_includes_canonical_and_punctuation_stripped(game_env):
    module = game_env.module
    variants = module.generate_accepted_variants("Il y a un théâtre.")
    assert "Il y a un théâtre." in variants
    assert "Il y a un théâtre" in variants


def test_generate_accepted_variants_includes_both_contraction_directions(game_env):
    module = game_env.module
    variants = module.generate_accepted_variants("It's a theatre.")
    assert any("it's" in v.casefold() for v in variants)
    assert any("it is" in v.casefold() for v in variants)


def test_generate_accepted_variants_reorders_a_slash_pair(game_env):
    module = game_env.module
    variants = module.generate_accepted_variants("a rubber / eraser")
    assert "a rubber / eraser" in variants
    assert "eraser / a rubber" in variants


def test_generate_accepted_variants_is_purely_mechanical_recombination(game_env):
    """No invented text -- every variant is built only from words already in
    the input, same copyright-safety rule as the runtime question generator."""
    module = game_env.module
    text = "Comment vas-tu?"
    for variant in module.generate_accepted_variants(text):
        for word in re.findall(r"\w+", variant, flags=0):
            assert word.casefold() in text.casefold()


def test_catalog_item_accepted_prefers_a_manually_added_array(game_env):
    module = game_env.module
    item = {"en": "there is a theatre.", "accepted_en": ["there's a theatre"]}
    assert module._catalog_item_accepted(item, "en") == ["there's a theatre"]


def test_catalog_item_accepted_falls_back_to_generated_variants(game_env):
    module = game_env.module
    item = {"fr": "Il y a un théâtre."}
    result = module._catalog_item_accepted(item, "fr")
    assert result == module.generate_accepted_variants("Il y a un théâtre.")


def test_lookup_accepted_finds_the_real_catalog_item_behind_a_question(game_env):
    module, state = game_env.module, game_env.state
    plot = next(
        p for p in state.plots if module.grading_tier(p.items[0]["fr"]) == module.TIER_LENIENT
    )
    item = plot.items[0]
    question = {"plot_id": plot.plot_id, "answer": item["fr"]}
    assert module._lookup_accepted(question) == module.generate_accepted_variants(item["fr"])


def test_check_answer_lenient_tier_accepts_a_manually_curated_report_addition(game_env):
    """The scenario §14.2.4 describes: a human triages a report and hand-adds
    a phrasing to the catalog item's accepted array; the next player who
    types that phrasing is now marked correct."""
    module, state = game_env.module, game_env.state
    plot = next(
        p for p in state.plots if module.grading_tier(p.items[0]["en"]) == module.TIER_LENIENT
    )
    item = plot.items[0]
    item["accepted_en"] = ["a hand-triaged alternate phrasing"]
    question = {"mode": "typed", "plot_id": plot.plot_id, "answer": item["en"], "choices": []}
    assert (
        module.check_answer(
            question, "a hand-triaged alternate phrasing", tier=module.TIER_LENIENT
        )
        is True
    )
    # The legacy (tier=None) path is completely unaffected by the addition --
    # proof that the old signature really is frozen.
    assert (
        module.check_answer(question, "a hand-triaged alternate phrasing") is False
    )
    del item["accepted_en"]


# --- live gameplay wiring --------------------------------------------------


def test_submit_answer_is_accent_sensitive_by_default(game_env):
    module, state = game_env.module, game_env.state
    assert module.ACCENT_SENSITIVE is True
    plot = state.plots_by_id["fren151-w1-vocab002-i00"]  # "zéro"
    assert plot.items[0]["fr"] == "zéro"

    module.open_practice(plot.plot_id, variant=module.V_EN_FR_TYPED)
    assert module.current_question["variant"] == module.V_EN_FR_TYPED
    result = module.submit_answer("zero")  # missing the accent
    assert result is False


def test_toggling_accent_sensitivity_off_relaxes_the_next_answer(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots_by_id["fren151-w1-vocab002-i00"]

    game_env.elements["accent-toggle-checkbox"].dispatch("click", None)
    assert module.ACCENT_SENSITIVE is False
    assert game_env.elements["accent-toggle-checkbox"].checked is False

    module.open_practice(plot.plot_id, variant=module.V_EN_FR_TYPED)
    result = module.submit_answer("zero")
    assert result is True

    # Toggle back on leaves it accent-sensitive again.
    game_env.elements["accent-toggle-checkbox"].dispatch("click", None)
    assert module.ACCENT_SENSITIVE is True


def test_submit_answer_uses_strict_tier_for_a_single_word_typed_answer(game_env):
    module, state = game_env.module, game_env.state
    plot = next(
        p
        for p in state.plots
        if module.V_FR_EN_TYPED in module.variants_for(p)
        and module.grading_tier(p.items[0]["en"]) == module.TIER_STRICT
    )
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)
    answer = module.current_question["answer"]
    result = module.submit_answer(f"a {answer}")  # an article STRICT should reject
    assert result is False


def test_submit_answer_uses_lenient_tier_for_a_multi_word_typed_answer(game_env):
    module, state = game_env.module, game_env.state
    plot = next(
        p
        for p in state.plots
        if module.V_FR_EN_TYPED in module.variants_for(p)
        and module.grading_tier(p.items[0]["en"]) == module.TIER_LENIENT
        and str(p.items[0]["en"]).split()[0].casefold() in ("a", "an", "the", "to", "some")
    )
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)
    answer = module.current_question["answer"]
    words = answer.split()
    dropped = " ".join(words[1:])  # drop the leading article -- LENIENT forgives this
    result = module.submit_answer(dropped)
    assert result is True


def test_accent_toggle_is_not_part_of_the_save_payload(game_env):
    """A session preference, not SRS state -- same call as `last_variant`."""
    module = game_env.module
    assert "accent_sensitive" not in module.get_state()


# --- backward compatibility (the hard constraint on this milestone) --------


def test_check_answer_two_argument_signature_is_completely_unchanged(game_env):
    module = game_env.module
    question = {"mode": "typed", "answer": "élève", "choices": []}
    assert module.check_answer(question, "élève") is True
    assert module.check_answer(question, "eleve") is True
    assert module.check_answer(question, "professeur") is False


def test_answer_alternatives_one_argument_signature_is_completely_unchanged(game_env):
    module = game_env.module
    alternatives = module.answer_alternatives("a rubber/eraser")
    assert {"a rubber", "rubber", "eraser", "a rubber/eraser"} <= alternatives
    # An unrelated extra phrasing passed via the new `accepted` kwarg must
    # never leak into a call that omits it.
    with_extra = module.answer_alternatives("a rubber/eraser", accepted=["a gum"])
    assert "gum" not in alternatives
    assert "gum" in with_extra


def test_every_plot_and_variant_still_generates_a_checkable_question(game_env):
    """Smoke test that Milestone 8 didn't disturb Milestone 3's generation
    path at all -- every variant still produces a question whose own answer
    checks out true under the unchanged legacy check_answer."""
    module = game_env.module
    rng = module.random.Random(23)
    for plot in game_env.state.plots[:150]:
        for variant in module.variants_for(plot):
            question = module.generate_question(plot, rng, variant=variant)
            assert module.check_answer(question, question["answer"]) is True
