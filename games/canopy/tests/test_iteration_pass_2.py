"""Iteration Pass 2: a biodiversity sub-meter (separate from economic
standing value, surfaced via a wildlife icon rather than a number) and
periodic stakeholder-tension requests (grant clears the community's
requested plot and nudges relations up, decline keeps it standing and
nudges relations down — neither choice is free or catastrophic)."""


def test_biodiversity_starts_at_zero(game_env):
    assert game_env.plot(0).biodiversity == 0.0


def test_biodiversity_accrues_while_preserved(game_env):
    game_env.timers.tick_intervals(5)
    assert game_env.plot(0).biodiversity == 5 * game_env.module.BIODIVERSITY_ACCRUAL_PER_TICK


def test_biodiversity_does_not_accrue_while_bare(game_env):
    game_env.select_tile_click(0)
    game_env.clear()
    game_env.timers.tick_intervals(5)
    assert game_env.plot(0).biodiversity == 0.0


def test_biodiversity_resets_on_clear(game_env):
    game_env.timers.tick_intervals(60)
    assert game_env.plot(0).biodiversity > 0.0
    game_env.select_tile_click(0)
    game_env.clear()
    assert game_env.plot(0).biodiversity == 0.0


def test_has_wildlife_false_below_threshold(game_env):
    game_env.timers.tick_intervals(5)
    assert game_env.plot(0).has_wildlife() is False


def test_has_wildlife_true_above_threshold(game_env):
    ticks_needed = int(game_env.module.BIODIVERSITY_WILDLIFE_THRESHOLD / game_env.module.BIODIVERSITY_ACCRUAL_PER_TICK) + 1
    game_env.timers.tick_intervals(ticks_needed)
    assert game_env.plot(0).has_wildlife() is True


def test_render_marks_wildlife_tile_with_css_class(game_env):
    ticks_needed = int(game_env.module.BIODIVERSITY_WILDLIFE_THRESHOLD / game_env.module.BIODIVERSITY_ACCRUAL_PER_TICK) + 1
    game_env.timers.tick_intervals(ticks_needed)
    assert "plot-has-wildlife" in game_env.elements["plot-0"].className


def test_community_relations_starts_neutral(game_env):
    assert game_env.module.community_relations == game_env.module.STARTING_COMMUNITY_RELATIONS


def test_no_stakeholder_request_before_interval_elapses(game_env):
    game_env.timers.tick_intervals(game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS - 1)
    assert game_env.module.pending_stakeholder_request is None


def test_no_stakeholder_request_when_no_plot_has_accrued_value(game_env):
    for plot in game_env.module.plots:
        plot.state = game_env.module.BARE
    game_env.timers.tick_intervals(game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS)
    assert game_env.module.pending_stakeholder_request is None


def test_stakeholder_request_triggers_once_a_plot_is_established(game_env):
    game_env.timers.tick_intervals(game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS + 1)
    assert game_env.module.pending_stakeholder_request is not None
    assert game_env.module.pending_stakeholder_request["plot_index"] == 0


def test_stakeholder_request_targets_most_established_plot(game_env):
    # Plot 0 accrues the longest, so it should be the target.
    game_env.timers.tick_intervals(game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS + 1)
    assert game_env.module.pending_stakeholder_request["plot_index"] == 0


def test_grant_stakeholder_request_clears_plot_and_adds_income(game_env):
    game_env.timers.tick_intervals(game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS + 1)
    target = game_env.module.pending_stakeholder_request["plot_index"]
    value_before = game_env.plot(target).value
    game_env.grant_stakeholder()
    assert game_env.plot(target).state == game_env.module.BARE
    assert game_env.total_income == value_before
    assert game_env.module.pending_stakeholder_request is None


def test_grant_stakeholder_request_raises_community_relations(game_env):
    game_env.timers.tick_intervals(game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS + 1)
    before = game_env.module.community_relations
    game_env.grant_stakeholder()
    assert game_env.module.community_relations == before + game_env.module.STAKEHOLDER_GRANT_RELATIONS_DELTA


def test_decline_stakeholder_request_keeps_plot_standing(game_env):
    game_env.timers.tick_intervals(game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS + 1)
    target = game_env.module.pending_stakeholder_request["plot_index"]
    game_env.decline_stakeholder()
    assert game_env.plot(target).state == game_env.module.PRESERVED
    assert game_env.module.pending_stakeholder_request is None


def test_decline_stakeholder_request_lowers_community_relations(game_env):
    game_env.timers.tick_intervals(game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS + 1)
    before = game_env.module.community_relations
    game_env.decline_stakeholder()
    assert game_env.module.community_relations == before + game_env.module.STAKEHOLDER_DECLINE_RELATIONS_DELTA


def test_community_relations_clamped_to_100(game_env):
    game_env.module.community_relations = 95
    game_env.timers.tick_intervals(game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS + 1)
    game_env.grant_stakeholder()
    assert game_env.module.community_relations == 100


def test_community_relations_clamped_to_0(game_env):
    game_env.module.community_relations = 2
    game_env.timers.tick_intervals(game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS + 1)
    game_env.decline_stakeholder()
    assert game_env.module.community_relations == 0


def test_grant_with_no_pending_request_is_a_noop(game_env):
    result = game_env.module.grant_stakeholder_request()
    assert result is False


def test_decline_with_no_pending_request_is_a_noop(game_env):
    result = game_env.module.decline_stakeholder_request()
    assert result is False


def test_stakeholder_panel_hidden_without_pending_request(game_env):
    game_env.module.render()
    assert game_env.elements["stakeholder-panel"].hidden is True


def test_stakeholder_panel_visible_with_pending_request(game_env):
    game_env.timers.tick_intervals(game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS + 1)
    assert game_env.elements["stakeholder-panel"].hidden is False
    assert len(game_env.elements["stakeholder-message"].innerText) > 0


def test_stakeholder_reason_cycles_deterministically(game_env):
    seen_reasons = []
    for _ in range(3):
        game_env.timers.tick_intervals(game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS)
        seen_reasons.append(game_env.module.pending_stakeholder_request["reason"])
        game_env.decline_stakeholder()
    assert seen_reasons == game_env.module.STAKEHOLDER_REASONS


def test_community_relations_display_updates(game_env):
    game_env.module.render()
    assert "50" in game_env.elements["community-relations-display"].innerText
