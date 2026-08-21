"""Iteration Pass 3 — fun/teaching balance: the ticker now narrates the
sea-level/damage side of recovery too (not just fish stock), and
adaptation tier unlocks get an immediate, trackable ticker payoff instead
of only a passive label change. See `climate-games-fun-teaching-balance.md`
and the "Iteration Notes — Pass 3" section in CLAUDE.md.
"""


def test_tier_unlock_logs_ticker_message(game_env):
    for _ in range(3):
        game_env.invest("adaptation")
    assert any("Sandbag berms" in msg for msg in game_env.state.ticker_log)
    assert any("dampened 30%" in msg for msg in game_env.state.ticker_log)


def test_no_tier_unlock_message_below_threshold(game_env):
    game_env.invest("adaptation")
    game_env.invest("adaptation")  # 2 < threshold of 3
    assert game_env.state.ticker_log == []


def test_tier_unlock_message_fires_again_at_next_threshold(game_env):
    for _ in range(6):
        game_env.invest("adaptation")
    assert any("Sandbag berms" in msg for msg in game_env.state.ticker_log)
    assert any("Seawalls" in msg and "dampened 60%" in msg for msg in game_env.state.ticker_log)


def test_tier_unlock_message_does_not_fire_on_output_investment(game_env):
    game_env.invest("output")
    assert game_env.state.ticker_log == []


def test_render_shows_tier_unlock_message(game_env):
    for _ in range(3):
        game_env.invest("adaptation")
    game_env.module.render()
    assert "Adaptation upgraded to Sandbag berms" in game_env.elements["ticker-log"].innerHTML


def test_trend_message_absent_before_enough_seasons(game_env):
    for _ in range(3):
        game_env.invest("adaptation")
    game_env.advance_season()
    game_env.advance_season()
    assert not any("flattening" in msg for msg in game_env.state.ticker_log)


def test_trend_flattening_message_logged_when_curve_flattens(game_env):
    # Two seasons at tier 0 (full damage), then unlock tier 1 mid-run,
    # then two more seasons at the dampened rate -> a visibly flattening
    # curve, matching the same first-half/second-half comparison already
    # used for the static damage-trend display.
    game_env.advance_season()
    game_env.advance_season()
    for _ in range(3):
        game_env.invest("adaptation")
    game_env.advance_season()
    game_env.advance_season()
    assert any("flattening" in msg for msg in game_env.state.ticker_log)
    assert game_env.state.trend_flattening_announced is True


def test_trend_flattening_message_fires_only_once(game_env):
    game_env.advance_season()
    game_env.advance_season()
    for _ in range(3):
        game_env.invest("adaptation")
    for _ in range(5):
        game_env.advance_season()
    flattening_messages = [msg for msg in game_env.state.ticker_log if "flattening" in msg]
    assert len(flattening_messages) <= 1


def test_no_trend_message_with_no_investment(game_env):
    for _ in range(4):
        game_env.advance_season()
    assert game_env.state.ticker_log == []
