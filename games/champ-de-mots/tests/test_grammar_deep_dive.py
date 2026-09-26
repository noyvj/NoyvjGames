"""L15 -- an optional grammar deep-dive panel for grammar plots."""


def _grammar_plot(game_env, with_rule=True):
    return next(p for p in game_env.state.plots if p.topic_type == "grammar" and bool(p.rule) == with_rule)


def _open(game_env, plot, variant=None):
    module = game_env.module
    module.open_practice(plot.plot_id, variant=variant)


def test_button_is_hidden_for_non_grammar_plots_and_shown_for_grammar(game_env):
    module = game_env.module
    vocab = next(p for p in game_env.state.plots if p.topic_type == "vocab")
    _open(game_env, vocab, module.V_FR_EN_CHOICE)
    assert game_env.elements["practice-deepdive-button"].hidden is True
    _open(game_env, _grammar_plot(game_env))
    assert game_env.elements["practice-deepdive-button"].hidden is False
    assert game_env.elements["practice-deepdive"].hidden is True  # collapsed until asked for


def test_data_covers_rule_examples_and_status(game_env):
    module = game_env.module
    plot = _grammar_plot(game_env)
    data = module.grammar_deep_dive(plot)
    assert data["title"] == plot.topic_title and data["rule"] == plot.rule and data["has_rule"]
    assert data["examples"] == [(i["fr"], i["en"]) for i in plot.items]
    assert "Seed" in data["stage"]
    assert module.grammar_deep_dive(next(p for p in game_env.state.plots if p.topic_type == "vocab")) is None
    assert module.grammar_deep_dive(None) is None


def test_a_topic_without_a_rule_says_so_instead_of_showing_nothing(game_env):
    module = game_env.module
    plot = _grammar_plot(game_env, with_rule=False)
    data = module.grammar_deep_dive(plot)
    assert data["rule"] == module.DEEP_DIVE_NO_RULE and data["has_rule"] is False


def test_toggle_renders_the_panel_and_closing_resets_it(game_env):
    module = game_env.module
    plot = _grammar_plot(game_env)
    _open(game_env, plot)
    game_env.elements["practice-deepdive-button"].dispatch("click", None)
    panel = game_env.elements["practice-deepdive"]
    assert panel.hidden is False
    texts = [c.innerText for c in panel.children]
    assert plot.topic_title in texts and plot.rule in texts
    assert any(plot.items[0]["fr"] in t and plot.items[0]["en"] in t for t in texts)
    assert texts[-1].startswith("Where this plot stands")
    game_env.elements["practice-deepdive-button"].dispatch("click", None)
    assert panel.hidden is True
    game_env.elements["practice-deepdive-button"].dispatch("click", None)
    module.close_practice()
    assert panel.hidden is True and game_env.elements["practice-deepdive-button"].hidden is True
    _open(game_env, plot)
    assert panel.hidden is True  # a fresh question starts collapsed


def test_known_mix_ups_are_listed_when_the_topic_has_them(game_env):
    module = game_env.module
    plot = _grammar_plot(game_env)
    plot.items = [{"fr": "ou", "en": "or"}]  # a WEED_CONFUSIONS key
    data = module.grammar_deep_dive(plot)
    assert data["confusions"] == ["où"]
    _open(game_env, plot)
    game_env.elements["practice-deepdive-button"].dispatch("click", None)
    texts = [c.innerText for c in game_env.elements["practice-deepdive"].children]
    assert "Easy to mix up with" in texts and any("où" in t for t in texts)


def test_it_never_changes_srs_state(game_env):
    plot = _grammar_plot(game_env)
    before = (plot.stage, plot.interval_days, plot.last_reviewed, plot.correct_streak)
    _open(game_env, plot)
    game_env.elements["practice-deepdive-button"].dispatch("click", None)
    assert before == (plot.stage, plot.interval_days, plot.last_reviewed, plot.correct_streak)
