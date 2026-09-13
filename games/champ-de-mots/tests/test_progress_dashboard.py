"""Improvement Ideas addendum (2026-09-13), §5: a progress dashboard --
per-week mastery %, weakest touched topics, and days since anything was
watered. A separate, purely informational screen: nothing here mutates
SRS state or row-unlock caching.
"""


def test_dashboard_is_hidden_until_toggled(game_env):
    module = game_env.module
    assert module.dashboard_open is False
    assert game_env.elements["dashboard-panel"].hidden is True


def test_toggling_opens_and_closes_the_dashboard(game_env):
    module = game_env.module
    module.on_toggle_dashboard()
    assert module.dashboard_open is True
    assert game_env.elements["dashboard-panel"].hidden is False
    assert "Hide" in game_env.elements["dashboard-toggle-button"].innerText

    module.on_toggle_dashboard()
    assert module.dashboard_open is False
    assert game_env.elements["dashboard-panel"].hidden is True


def test_row_mastery_is_zero_for_an_untouched_row(game_env):
    module = game_env.module
    assert module.dashboard_row_mastery(1) == 0.0


def test_row_mastery_rises_as_plots_grow(game_env):
    module, state = game_env.module, game_env.state
    row_plots = state.row_plots(1)
    for plot in row_plots:
        state.review(plot.plot_id, True)
    assert module.dashboard_row_mastery(1) > 0.0
    assert module.dashboard_row_mastery(1) <= 100.0


def test_a_fully_automated_row_reports_100_percent_mastery(game_env):
    module, state = game_env.module, game_env.state
    row_plots = state.row_plots(1)
    for plot in row_plots:
        for _ in range(6):
            state.review(plot.plot_id, True)
            state.advance_day(plot.interval_days)
    assert all(p.stage == module.STAGE_AUTOMATED for p in row_plots)
    assert module.dashboard_row_mastery(1) == 100.0


def test_days_since_last_touch_is_none_for_a_fresh_farm(game_env):
    module = game_env.module
    assert module.dashboard_days_since_last_touch() is None


def test_days_since_last_touch_tracks_the_most_recent_review(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    state.review(plot.plot_id, True)
    state.advance_day(5)
    assert module.dashboard_days_since_last_touch() == 5


def test_weakest_topics_excludes_untouched_ones(game_env):
    module = game_env.module
    assert module.dashboard_weakest_topics() == []


def test_weakest_topics_ranks_the_least_grown_first(game_env):
    module, state = game_env.module, game_env.state
    weak_topic_plots = [p for p in state.plots if p.topic_id == state.plots[0].topic_id]
    strong_topic_id = next(
        p.topic_id for p in state.plots if p.topic_id != state.plots[0].topic_id
    )
    strong_topic_plots = [p for p in state.plots if p.topic_id == strong_topic_id]

    # Barely touch the "weak" topic once each (still Sprout), fully mature
    # the "strong" one.
    for plot in weak_topic_plots:
        state.review(plot.plot_id, True)
    for plot in strong_topic_plots:
        for _ in range(6):
            state.review(plot.plot_id, True)
            state.advance_day(plot.interval_days)

    weakest = module.dashboard_weakest_topics(limit=10)
    weakest_ids = [entry["topic_id"] for entry in weakest]
    weak_topic_id = weak_topic_plots[0].topic_id
    assert weak_topic_id in weakest_ids
    assert strong_topic_id in weakest_ids  # both touched, so both listed
    # The barely-touched (Sprout) topic must rank as weaker than the fully
    # Automated one -- lower average stage rank sorts first.
    assert weakest_ids.index(weak_topic_id) < weakest_ids.index(strong_topic_id)

    # With a limit small enough to force a cut, only the genuinely weaker
    # topic survives.
    top_one = module.dashboard_weakest_topics(limit=1)
    assert top_one[0]["topic_id"] == weak_topic_id


def test_weakest_topics_never_includes_a_locked_row(game_env):
    module, state = game_env.module, game_env.state
    locked_plot = next(p for p in state.plots if not state.is_row_unlocked(p.sequence))
    # Force some SRS state directly (bypassing the row-unlock check that
    # open_practice() would normally enforce) to prove the dashboard itself
    # still won't surface a locked row even if a plot somehow got touched.
    locked_plot.last_reviewed = 0
    weakest = module.dashboard_weakest_topics(limit=50)
    assert all(entry["sequence"] != locked_plot.sequence for entry in weakest)


def test_the_dashboard_never_mutates_srs_state(game_env):
    module, state = game_env.module, game_env.state
    stages_before = [p.stage for p in state.plots]
    intervals_before = [p.interval_days for p in state.plots]
    module.on_toggle_dashboard()
    assert [p.stage for p in state.plots] == stages_before
    assert [p.interval_days for p in state.plots] == intervals_before
