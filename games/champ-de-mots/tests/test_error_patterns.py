"""Improvement Ideas addendum, "personal error-pattern digest": a wrong
typed answer is classified by *why* it likely missed (accent slip, known
mix-up, close typo, or a genuine miss), and the running counts are surfaced
on the Progress Dashboard. Purely diagnostic -- classification never
changes grading or SRS scheduling, only a persistent tally.
"""


def _plot_for_fr(state, fr_text):
    return next(p for p in state.plots if p.items[0].get("fr") == fr_text)


def _all_texts(element):
    """The fake DOM's innerText doesn't aggregate appendChild-ed children
    (unlike a real browser), so gathering rendered text means walking the
    tree explicitly -- same workaround test_cultural_notes.py uses."""
    texts = [element.innerText]
    for child in element.children:
        texts.extend(_all_texts(child))
    return texts


def test_classify_detects_a_known_mixup(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "travailler")
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)
    question = module.current_question
    assert question["answer"] == "to work"
    pattern = module.classify_wrong_typed_answer(question, "travel", module.grading_tier(question["answer"]))
    assert pattern == module.ERROR_PATTERN_KNOWN_MIXUP


def test_classify_detects_an_accent_slip(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "enchanté")
    module.open_practice(plot.plot_id, variant=module.V_EN_FR_TYPED)
    question = module.current_question
    assert question["answer"] == "enchanté"
    pattern = module.classify_wrong_typed_answer(question, "enchante", module.grading_tier(question["answer"]))
    assert pattern == module.ERROR_PATTERN_ACCENT


def test_classify_detects_a_close_typo(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "bonjour")
    module.open_practice(plot.plot_id, variant=module.V_EN_FR_TYPED)
    question = module.current_question
    assert question["answer"] == "bonjour"
    pattern = module.classify_wrong_typed_answer(question, "bonjor", module.grading_tier(question["answer"]))
    assert pattern == module.ERROR_PATTERN_CLOSE_TYPO


def test_classify_falls_back_to_other_for_an_arbitrary_miss(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "bonjour")
    module.open_practice(plot.plot_id, variant=module.V_EN_FR_TYPED)
    question = module.current_question
    pattern = module.classify_wrong_typed_answer(
        question, "quelque chose de completement different", module.grading_tier(question["answer"])
    )
    assert pattern == module.ERROR_PATTERN_OTHER


def test_a_wrong_typed_answer_increments_the_matching_pattern_count(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "enchanté")
    module.open_practice(plot.plot_id, variant=module.V_EN_FR_TYPED)
    module.submit_answer("enchante")
    assert module.error_pattern_counts == {module.ERROR_PATTERN_ACCENT: 1}


def test_repeated_misses_of_the_same_kind_accumulate(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "bonjour")
    module.open_practice(plot.plot_id, variant=module.V_EN_FR_TYPED)
    module.submit_answer("bonjor")
    module.open_practice(plot.plot_id, variant=module.V_EN_FR_TYPED)
    module.submit_answer("bonjor")
    assert module.error_pattern_counts[module.ERROR_PATTERN_CLOSE_TYPO] == 2


def test_a_correct_typed_answer_records_nothing(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "bonjour")
    module.open_practice(plot.plot_id, variant=module.V_EN_FR_TYPED)
    module.submit_answer("bonjour")
    assert module.error_pattern_counts == {}


def test_a_wrong_multiple_choice_answer_records_nothing(game_env):
    """Multiple choice carries none of the typed-answer nuance -- a
    wrong pick is just "picked the wrong one," not a spelling pattern."""
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_CHOICE)
    question = module.current_question
    wrong_choice = next(c for c in question["choices"] if c != question["answer"])
    module.submit_answer(wrong_choice)
    assert module.error_pattern_counts == {}


def test_error_pattern_counts_persist_through_a_save_round_trip(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "enchanté")
    module.open_practice(plot.plot_id, variant=module.V_EN_FR_TYPED)
    module.submit_answer("enchante")

    saved = module.get_state()
    assert saved["error_patterns"] == {module.ERROR_PATTERN_ACCENT: 1}

    module.load_state(saved)
    assert module.error_pattern_counts == {module.ERROR_PATTERN_ACCENT: 1}


def test_a_save_missing_error_patterns_defaults_to_empty(game_env):
    """Forward-compat: an older save written before this field existed must
    not crash load_state() -- same defensive posture as every other field."""
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "enchanté")
    module.open_practice(plot.plot_id, variant=module.V_EN_FR_TYPED)
    module.submit_answer("enchante")
    assert module.error_pattern_counts

    module.load_state({"version": module.SAVE_VERSION, "current_day": 0, "plots": {}})
    assert module.error_pattern_counts == {}


def test_dashboard_common_patterns_starts_empty(game_env):
    module = game_env.module
    module.on_toggle_dashboard()
    panel = game_env.elements["dashboard-panel"]
    texts = _all_texts(panel)
    assert any("no wrong typed answers" in text.lower() for text in texts)


def test_dashboard_lists_a_recorded_pattern_with_its_count(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "enchanté")
    module.open_practice(plot.plot_id, variant=module.V_EN_FR_TYPED)
    module.submit_answer("enchante")

    module.on_toggle_dashboard()
    panel = game_env.elements["dashboard-panel"]
    texts = _all_texts(panel)
    assert any(module.ERROR_PATTERN_LABELS[module.ERROR_PATTERN_ACCENT] in text for text in texts)
    assert any("1 time" in text for text in texts)


def test_the_dashboard_never_mutates_error_pattern_counts(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "enchanté")
    module.open_practice(plot.plot_id, variant=module.V_EN_FR_TYPED)
    module.submit_answer("enchante")
    before = dict(module.error_pattern_counts)

    module.on_toggle_dashboard()
    module.on_toggle_dashboard()

    assert module.error_pattern_counts == before
