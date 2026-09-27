"""GB-30: a Perfect Season streak (no clear, no trust collapse) gives a small
growth multiplier, shown as a flame counter on the season indicator."""

from .gb_helpers import advance_to, log_kinds, toast_text

SEASON = 40


def _idle_season(env, n=1):
    advance_to(env, (env.module.forest_tick // SEASON + n) * SEASON)


def test_idle_season_earns_a_flame(game_env):
    m = game_env.module
    advance_to(game_env, SEASON)
    assert m.perfect_streak == 1
    assert "season" in log_kinds(m)
    assert "Perfect Season x1" in toast_text(game_env)
    assert "streak: 1" in game_env.elements["perfect-streak-text"].innerText


def test_multiplier_grows_two_percent_per_flame_up_to_ten(game_env):
    m = game_env.module
    seen = []
    for _ in range(7):
        _idle_season(game_env)
        seen.append(round(m.current_perfect_streak_multiplier(), 4))
    assert seen == [1.02, 1.04, 1.06, 1.08, 1.10, 1.10, 1.10]
    assert m.perfect_streak == 7


def test_multiplier_applies_to_accrual(game_env):
    m = game_env.module
    plot = m.Plot(0)
    plot.ticks_intact = 5
    base = plot.accrue_tick()
    m.perfect_streak = 3
    plot2 = m.Plot(0)
    plot2.ticks_intact = 5
    assert abs(plot2.accrue_tick() / base - 1.06) < 1e-9


def test_a_clear_breaks_the_season(game_env):
    m = game_env.module
    advance_to(game_env, SEASON)
    game_env.tick(5)
    game_env.select(0)
    game_env.clear()
    for _ in range(6):
        game_env.tick()  # let the undo window lapse
    assert m.perfect_season_status() == (False, "a plot was cleared this season")
    advance_to(game_env, 2 * SEASON)
    assert m.perfect_streak == 0
    assert any("broke a 1-season" in e["text"] for e in m.forest_log)


def test_the_next_clean_season_starts_a_new_streak(game_env):
    m = game_env.module
    game_env.tick(3)
    game_env.select(0)
    game_env.clear()
    advance_to(game_env, SEASON)
    assert m.perfect_streak == 0
    advance_to(game_env, 2 * SEASON)
    assert m.perfect_streak == 1


def test_granting_a_clear_request_breaks_it_too(game_env):
    m = game_env.module
    game_env.tick(m.STAKEHOLDER_EVENT_INTERVAL_TICKS + 1)
    game_env.grant_stakeholder()
    assert m.season_cleared is True


def test_undoing_the_clear_keeps_the_season_perfect(game_env):
    m = game_env.module
    game_env.tick(3)
    game_env.select(0)
    game_env.clear()
    m.undo_last_clear()
    advance_to(game_env, SEASON)
    assert m.perfect_streak == 1


def test_trust_collapse_breaks_it(game_env):
    m = game_env.module
    game_env.tick(3)
    m.community_relations = m.PERFECT_SEASON_MIN_RELATIONS - 5
    game_env.tick()
    m.community_relations = 80  # recovered later, but the dip counted
    assert m.perfect_season_status()[0] is False
    advance_to(game_env, SEASON)
    assert m.perfect_streak == 0


def test_declines_alone_are_fine_while_trust_holds(game_env):
    m = game_env.module
    game_env.tick(3)
    m.pending_stakeholder_request = {"plot_index": 5, "reason": "housing", "kind": "clear"}
    game_env.decline_stakeholder()
    assert m.community_relations > m.PERFECT_SEASON_MIN_RELATIONS
    assert m.perfect_season_status()[0] is True


def test_indicator_states_the_rule_and_this_seasons_status(game_env):
    m = game_env.module
    m.render()
    element = game_env.elements["perfect-streak-text"]
    assert "on track" in element.title and "without clearing" in element.title
    assert "Perfect Season streak" in element.getAttribute("aria-label")
    game_env.select(0)
    game_env.clear()
    assert "broken this season" in element.title


def test_streak_flashes_the_counter(game_env):
    advance_to(game_env, SEASON)
    assert game_env.elements["perfect-streak-text"].classList.contains("just-improved")
    game_env.timers.flush()
    assert not game_env.elements["perfect-streak-text"].classList.contains("just-improved")


def test_highland_and_wetland_share_the_multiplier(game_env):
    m = game_env.module
    m.perfect_streak = 5
    assert m.Plot(0, region="wetland").accrue_tick() > 0


def test_state_round_trip_and_defaults(game_env):
    m = game_env.module
    assert "perfect_season" not in m.get_state()
    advance_to(game_env, 2 * SEASON)
    state = m.get_state()
    assert state["perfect_season"]["streak"] == 2
    m.perfect_streak = 0
    m.load_state(state)
    assert m.perfect_streak == 2


def test_dirty_season_flag_is_saved(game_env):
    m = game_env.module
    game_env.tick(3)
    game_env.select(0)
    game_env.clear()
    state = m.get_state()
    assert state["perfect_season"]["cleared"] is True
    game_env.reset_session()
    m.load_state(state)
    assert m.season_cleared is True


def test_load_rejects_bad_streak_data(game_env):
    m = game_env.module
    base = m.get_state()
    for bad in ({"streak": True, "cleared": "yes", "min_relations": "low"}, {"streak": -4}, {"streak": 10**12},
                {"streak": float("nan")}, [1], "x", 5, {"cleared": 1, "min_relations": 1e9}):
        m.load_state(dict(base, perfect_season=bad))
        assert 0 <= m.perfect_streak <= 9999
        assert m.season_cleared is False
        assert m.season_min_relations is None or 0 <= m.season_min_relations <= 100


def test_reset_clears_the_streak(game_env):
    m = game_env.module
    advance_to(game_env, SEASON)
    game_env.reset_session()
    assert m.perfect_streak == 0 and m.season_cleared is False
