"""L19 -- a personal phrasebook: star items while practising, practise just those."""


def _open(game_env, plot=None, variant=None):
    module = game_env.module
    plot = plot or game_env.state.plots[0]
    module.open_practice(plot.plot_id, variant=variant or module.V_FR_EN_CHOICE)
    return plot


def test_empty_by_default_and_button_hidden_without_a_question(game_env):
    module = game_env.module
    assert module.phrasebook == []
    assert game_env.elements["practice-bookmark-button"].hidden is True
    assert "(0)" in game_env.elements["phrasebook-toggle-button"].innerText


def test_starring_a_practice_question_saves_and_unsaves_it(game_env):
    module = game_env.module
    plot = _open(game_env)
    button = game_env.elements["practice-bookmark-button"]
    assert button.hidden is False and "Save" in button.innerText
    button.dispatch("click", None)
    assert module.phrasebook == [plot.plot_id]
    assert "In your phrasebook" in button.innerText and button.attributes.get("aria-pressed") == "true"
    assert "(1)" in game_env.elements["phrasebook-toggle-button"].innerText
    button.dispatch("click", None)
    assert module.phrasebook == []


def test_a_review_question_can_be_starred_too(game_env):
    module = game_env.module
    plot = game_env.state.plots[3]
    plot.stage = module.STAGE_SPROUT
    module.start_review("word")
    if module.review_question is None:
        module.review_mode = "word"
        module.review_queue = [plot.plot_id]
        module.review_index = 0
        module._advance_review_question()
        module.render()
    game_env.elements["review-bookmark-button"].dispatch("click", None)
    assert module.phrasebook == [module.review_question["plot_id"]]


def test_panel_lists_saved_items_with_meaning_and_removes_them(game_env):
    module = game_env.module
    vocab = next(p for p in game_env.state.plots if p.topic_type == "vocab")
    grammar = next(p for p in game_env.state.plots if p.topic_type == "grammar")
    module.toggle_phrasebook(vocab.plot_id)
    module.toggle_phrasebook(grammar.plot_id)
    game_env.elements["phrasebook-toggle-button"].dispatch("click", None)
    rows = game_env.elements["phrasebook-list"].children
    assert len(rows) == 2
    assert vocab.items[0]["en"] in rows[0].children[0].innerText
    assert grammar.label in rows[1].children[0].innerText
    rows[0].children[1].dispatch("click", None)
    assert module.phrasebook == [grammar.plot_id]
    assert len(game_env.elements["phrasebook-list"].children) == 1


def test_empty_panel_is_gentle_and_practice_is_disabled(game_env):
    game_env.elements["phrasebook-toggle-button"].dispatch("click", None)
    assert game_env.elements["phrasebook-practice-button"].disabled is True
    assert "empty" in game_env.elements["phrasebook-list"].children[0].innerText


def test_practice_runs_a_session_over_only_the_saved_items(game_env):
    module = game_env.module
    ids = [game_env.state.plots[i].plot_id for i in (5, 40, 200)]
    for plot_id in ids:
        module.toggle_phrasebook(plot_id)
    game_env.elements["phrasebook-toggle-button"].dispatch("click", None)
    assert game_env.elements["phrasebook-practice-button"].disabled is False
    game_env.elements["phrasebook-practice-button"].dispatch("click", None)
    assert module.review_mode == module.PHRASEBOOK_MODE
    assert sorted(module.review_queue) == sorted(ids)
    assert module.review_question["plot_id"] in ids


def test_session_size_is_capped(game_env):
    module = game_env.module
    for plot in game_env.state.plots[: module.PHRASEBOOK_SESSION_MAX + 10]:
        module.toggle_phrasebook(plot.plot_id)
    module.start_review(module.PHRASEBOOK_MODE)
    assert len(module.review_queue) == module.PHRASEBOOK_SESSION_MAX


def test_save_round_trip_and_default_save_stays_small(game_env):
    module = game_env.module
    assert "phrasebook" not in module.get_state()
    ids = [game_env.state.plots[i].plot_id for i in (1, 2)]
    for plot_id in ids:
        module.toggle_phrasebook(plot_id)
    saved = module.get_state()
    assert saved["phrasebook"] == ids
    module.phrasebook = []
    module.load_state(saved)
    assert module.phrasebook == ids


def test_a_tampered_save_cannot_smuggle_in_bad_ids(game_env):
    module = game_env.module
    good = game_env.state.plots[0].plot_id
    saved = module.get_state()
    saved["phrasebook"] = [good, good, "not-a-plot", 7, None, ["x"]]
    module.load_state(saved)
    assert module.phrasebook == [good]
    saved["phrasebook"] = "junk"
    module.load_state(saved)
    assert module.phrasebook == []


def test_the_list_is_capped_and_unknown_ids_are_refused(game_env):
    module = game_env.module
    assert module.toggle_phrasebook("nope") is False and module.phrasebook == []
    module.phrasebook = [p.plot_id for p in game_env.state.plots[: module.PHRASEBOOK_LIMIT]]
    extra = game_env.state.plots[module.PHRASEBOOK_LIMIT]
    assert module.toggle_phrasebook(extra.plot_id) is False
    assert len(module.phrasebook) == module.PHRASEBOOK_LIMIT
