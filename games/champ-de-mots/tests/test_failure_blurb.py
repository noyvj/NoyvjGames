"""Milestone 10: the failure feedback blurb (§14.3), Phase 1 only.

A short card shown once an answer is marked wrong: what it is, a memory
tip, and why it matters. Phase 1 is explicitly template-filled from catalog
fields plus a generic per-topic_type "why it matters" template -- there is
no Claude API call here (that's Phase 2, explicitly out of scope).
"""

import pytest


def _first_plot(game_env, topic_type, needs_rule=False):
    plots = [p for p in game_env.state.plots if p.topic_type == topic_type]
    if needs_rule:
        plots = [p for p in plots if p.rule]
    return plots[0]


# --- build_failure_blurb() shape -------------------------------------------


def test_blurb_has_the_documented_three_fields(game_env):
    module = game_env.module
    plot = _first_plot(game_env, "vocab")
    question = module.generate_question(plot, module.random.Random(1))
    blurb = module.build_failure_blurb(question)
    assert set(blurb) == {"what_it_is", "memory_tip", "why_it_matters"}
    assert blurb["what_it_is"]
    assert blurb["memory_tip"]
    assert blurb["why_it_matters"]


def test_blurb_is_none_for_an_unrecognised_question(game_env):
    module = game_env.module
    assert module.build_failure_blurb({"plot_id": "not-a-real-plot"}) is None


# --- "what it is" ------------------------------------------------------


def test_grammar_what_it_is_uses_the_rule_field(game_env):
    module = game_env.module
    plot = _first_plot(game_env, "grammar", needs_rule=True)
    question = module.generate_question(plot, module.random.Random(2))
    blurb = module.build_failure_blurb(question)
    assert blurb["what_it_is"] == plot.rule


def test_vocab_what_it_is_restates_the_catalog_pair(game_env):
    module = game_env.module
    plot = _first_plot(game_env, "vocab")
    item = plot.items[0]
    question = module.generate_question(plot, module.random.Random(3))
    blurb = module.build_failure_blurb(question)
    assert item["fr"] in blurb["what_it_is"]
    assert item["en"] in blurb["what_it_is"]
    assert plot.topic_title in blurb["what_it_is"]


# --- "why it matters": a generic per-topic_type template -------------------


def test_why_it_matters_is_the_same_generic_template_per_topic_type(game_env):
    module = game_env.module
    for topic_type in ("vocab", "phrase", "grammar", "phonetic"):
        plots = [p for p in game_env.state.plots if p.topic_type == topic_type][:3]
        texts = set()
        for plot in plots:
            question = module.generate_question(plot, module.random.Random(4))
            texts.add(module.build_failure_blurb(question)["why_it_matters"])
        assert len(texts) == 1, f"{topic_type} why_it_matters should be one fixed template"
        assert texts == {module.FAILURE_BLURB_WHY_IT_MATTERS[topic_type]}


def test_why_it_matters_differs_by_topic_type(game_env):
    module = game_env.module
    values = set(module.FAILURE_BLURB_WHY_IT_MATTERS.values())
    assert len(values) == len(module.FAILURE_BLURB_WHY_IT_MATTERS)


# --- Phase 1 only: no API call, no per-item authored content ---------------


def test_no_network_or_api_call_anywhere_in_the_blurb_path(game_env):
    """Phase 2 (a one-off Claude API call per item, cached) is explicitly a
    stretch goal, not part of this build."""
    module = game_env.module
    source_names = {"anthropic", "claude", "api_key", "requests.", "urllib", "httpx"}
    import inspect

    source = inspect.getsource(module.build_failure_blurb)
    source += inspect.getsource(module._blurb_what_it_is)
    source += inspect.getsource(module._blurb_memory_tip)
    lowered = source.lower()
    for banned in source_names:
        assert banned not in lowered


# --- rendering: shown only once an answer is marked wrong -------------------


def test_blurb_panel_is_hidden_before_any_answer(game_env):
    module = game_env.module
    plot = _first_plot(game_env, "vocab")
    module.open_practice(plot.plot_id)
    assert game_env.elements["practice-blurb"].hidden is True


def test_blurb_panel_is_hidden_when_the_answer_is_correct(game_env):
    module = game_env.module
    plot = _first_plot(game_env, "vocab")
    question = module.open_practice(plot.plot_id, variant=module.V_FR_EN_CHOICE)
    module.submit_answer(question["answer"])
    assert module.current_result is True
    assert game_env.elements["practice-blurb"].hidden is True


def test_blurb_panel_appears_on_a_wrong_choice_answer(game_env):
    """Unlike the report button, the blurb is not written-answer-only --
    §14.3 says "when an answer is marked wrong", full stop."""
    module = game_env.module
    plot = _first_plot(game_env, "vocab")
    question = module.open_practice(plot.plot_id, variant=module.V_FR_EN_CHOICE)
    wrong = next(c for c in question["choices"] if c != question["answer"])
    module.submit_answer(wrong)
    assert module.current_result is False
    assert game_env.elements["practice-blurb"].hidden is False
    assert game_env.elements["practice-blurb-what"].innerText
    assert game_env.elements["practice-blurb-tip"].innerText
    assert game_env.elements["practice-blurb-why"].innerText


def test_blurb_panel_appears_on_a_wrong_typed_answer(game_env):
    module = game_env.module
    plot = next(
        p for p in game_env.state.plots if module.V_FR_EN_TYPED in module.variants_for(p)
    )
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)
    module.submit_answer("definitely wrong")
    assert module.current_result is False
    assert game_env.elements["practice-blurb"].hidden is False


def test_blurb_panel_hides_again_once_the_panel_closes(game_env):
    module = game_env.module
    plot = _first_plot(game_env, "vocab")
    question = module.open_practice(plot.plot_id, variant=module.V_FR_EN_CHOICE)
    wrong = next(c for c in question["choices"] if c != question["answer"])
    module.submit_answer(wrong)
    assert game_env.elements["practice-blurb"].hidden is False
    game_env.close_practice()
    assert game_env.elements["practice-blurb"].hidden is True


def test_blurb_text_matches_build_failure_blurb(game_env):
    module = game_env.module
    plot = _first_plot(game_env, "grammar", needs_rule=True)
    question = module.open_practice(plot.plot_id, variant=module.V_EXAMPLE_FR_EN)
    wrong = next(c for c in question["choices"] if c != question["answer"])
    module.submit_answer(wrong)
    blurb = module.build_failure_blurb(question)
    assert game_env.elements["practice-blurb-what"].innerText == blurb["what_it_is"]
    assert game_env.elements["practice-blurb-tip"].innerText == blurb["memory_tip"]
    assert game_env.elements["practice-blurb-why"].innerText == blurb["why_it_matters"]
