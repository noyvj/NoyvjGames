"""Improvement Ideas addendum: achievements, scoped to a game-local slice
only -- the doc's own cross-game architecture ("this game would be the
first contributor to") is out of scope here. Since a plot's stage never
regresses (Milestone 2), "currently Automated" and "ever reached
Automated" are the same count, so this needs no new save state at all.
"""


def _all_texts(element):
    texts = [element.innerText]
    for child in element.children:
        texts.extend(_all_texts(child))
    return texts


def _fully_automate(state, plot):
    for _ in range(6):
        state.review(plot.plot_id, True)
        state.advance_day(plot.interval_days)


def test_automated_plot_count_is_zero_on_a_fresh_farm(game_env):
    module = game_env.module
    assert module.automated_plot_count() == 0


def test_automated_plot_count_tracks_real_automated_plots(game_env):
    module, state = game_env.module, game_env.state
    _fully_automate(state, state.plots[0])
    assert state.plots[0].stage == module.STAGE_AUTOMATED
    assert module.automated_plot_count() == 1


def test_fully_automated_row_count_is_zero_on_a_fresh_farm(game_env):
    module = game_env.module
    assert module.fully_automated_row_count() == 0


def test_fully_automated_row_count_counts_a_row_only_once_every_plot_is_done(game_env):
    module, state = game_env.module, game_env.state
    row_plots = state.row_plots(1)
    for plot in row_plots[:-1]:
        _fully_automate(state, plot)
    assert module.fully_automated_row_count() == 0

    _fully_automate(state, row_plots[-1])
    assert module.fully_automated_row_count() == 1


def test_no_thresholds_are_earned_on_a_fresh_farm(game_env):
    module = game_env.module
    summary = module.achievements_summary()
    assert summary["automated"]["earned"] == []
    assert summary["rows"]["earned"] == []


def test_the_next_automated_threshold_shows_progress(game_env):
    module, state = game_env.module, game_env.state
    _fully_automate(state, state.plots[0])
    summary = module.achievements_summary()
    next_up = summary["automated"]["next"]
    assert next_up["id"] == 25
    assert next_up["current"] == 1


def test_crossing_a_threshold_earns_it_and_advances_next(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.plots[:25]:
        _fully_automate(state, plot)
    summary = module.achievements_summary()
    earned_ids = [entry["id"] for entry in summary["automated"]["earned"]]
    assert 25 in earned_ids
    assert summary["automated"]["next"]["id"] == 50


def test_earned_thresholds_list_most_recent_first(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.plots[:50]:
        _fully_automate(state, plot)
    summary = module.achievements_summary()
    earned_ids = [entry["id"] for entry in summary["automated"]["earned"]]
    assert earned_ids == [50, 25]


def test_a_full_week_achievement_is_earned_once_a_row_is_entirely_automated(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.row_plots(1):
        _fully_automate(state, plot)
    summary = module.achievements_summary()
    earned_labels = [entry["label"] for entry in summary["rows"]["earned"]]
    assert module.ACHIEVEMENT_ROW_LABELS[1] in earned_labels
    assert summary["rows"]["next"]["id"] == 5


def test_achievements_never_mutate_srs_state(game_env):
    module, state = game_env.module, game_env.state
    stages_before = [p.stage for p in state.plots]
    module.on_toggle_achievements()
    module.achievements_summary()
    assert [p.stage for p in state.plots] == stages_before


def test_the_panel_is_hidden_until_toggled(game_env):
    module = game_env.module
    assert module.achievements_open is False
    assert game_env.elements["achievements-panel"].hidden is True


def test_toggling_opens_and_closes_the_panel(game_env):
    module = game_env.module
    module.on_toggle_achievements()
    assert module.achievements_open is True
    assert game_env.elements["achievements-panel"].hidden is False
    assert "Hide" in game_env.elements["achievements-toggle-button"].innerText

    module.on_toggle_achievements()
    assert module.achievements_open is False
    assert game_env.elements["achievements-panel"].hidden is True


def test_the_panel_shows_the_next_target_before_anything_is_earned(game_env):
    module = game_env.module
    module.on_toggle_achievements()
    texts = _all_texts(game_env.elements["achievements-panel"])
    assert any("25 plots automated" in text and "0 of 25" in text for text in texts)


def test_the_panel_shows_an_earned_badge(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.plots[:25]:
        _fully_automate(state, plot)
    module.on_toggle_achievements()
    texts = _all_texts(game_env.elements["achievements-panel"])
    assert any("25 plots automated" in text for text in texts)
