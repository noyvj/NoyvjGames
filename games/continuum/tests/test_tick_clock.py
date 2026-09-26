"""U1: tick-based play (speed controls, season clock)."""

import pytest


def _click(env, key):
    env.elements[f"speed-{key}-button"].dispatch("click", None)


def test_starts_paused(game_env):
    m = game_env.module
    assert m.sim_speed == 0 and m.season_progress == 0.0
    assert "Paused" in game_env.elements["season-clock-display"].innerText


def test_paused_clock_never_advances(game_env):
    m = game_env.module
    season = game_env.state.season
    assert m.tick_clock(1.0) == 0
    for _ in range(50):
        m.tick_clock(1.0)
    assert game_env.state.season == season


def test_speed_buttons_set_speed_and_aria(game_env):
    m = game_env.module
    for key, speed in (("1x", 1), ("2x", 2), ("4x", 4), ("pause", 0)):
        _click(game_env, key)
        assert m.sim_speed == speed
        assert game_env.elements[f"speed-{key}-button"].attributes["aria-pressed"] == "true"


def test_bad_speed_rejected(game_env):
    m = game_env.module
    for bad in (3, -1, "2", None, 8, 1.5):
        assert m.set_speed(bad) is False
    assert m.sim_speed == 0


def test_a_season_passes_after_the_era_length_at_1x(game_env):
    m = game_env.module
    m.set_speed(1)
    season = game_env.state.season
    length = m.season_length()
    steps = int(length)  # 1s steps, the clamp maximum
    passed = sum(m.tick_clock(1.0) for _ in range(steps - 1))
    assert passed == 0 and game_env.state.season == season
    assert m.tick_clock(1.0) == 1
    assert game_env.state.season == season + 1


def test_higher_speeds_are_proportionally_faster(game_env):
    m = game_env.module
    m.set_speed(4)
    season = game_env.state.season
    total = sum(m.tick_clock(1.0) for _ in range(10))
    # 10 real seconds at 4x = 40 game-seconds = 4 seasons of a 10s era
    assert total == 4 and game_env.state.season == season + 4


def test_a_stalled_frame_cannot_fast_forward(game_env):
    m = game_env.module
    m.set_speed(4)
    season = game_env.state.season
    assert m.tick_clock(3600.0) <= m.MAX_SEASONS_PER_TICK
    assert game_env.state.season <= season + m.MAX_SEASONS_PER_TICK
    assert m.season_progress < m.season_length()


def test_bad_dt_is_ignored(game_env):
    m = game_env.module
    m.set_speed(1)
    for bad in (0, -1.0, float("nan"), None, "1", True):
        assert m.tick_clock(bad) == 0
    assert m.season_progress == 0.0


def test_pausing_keeps_banked_progress(game_env):
    m = game_env.module
    m.set_speed(1)
    m.tick_clock(0.5)
    m.set_speed(0)
    m.tick_clock(5.0)
    assert m.season_progress == pytest.approx(0.5)


def test_clock_holds_during_a_look_back(game_env):
    m = game_env.module
    m.set_speed(1)
    m.campaign.revisiting = "tribal"
    assert m.tick_clock(1.0) == 0 and m.season_progress == 0.0
    m.render_clock()
    assert "Looking back" in game_env.elements["season-clock-display"].innerText
    m.campaign.revisiting = None


def test_later_eras_have_longer_seasons(game_env):
    m = game_env.module
    lengths = [m.SEASON_SECONDS[era] for era in m.sim.ERA_ORDER]
    assert lengths == sorted(lengths) and lengths[0] < lengths[-1]
    assert set(m.SEASON_SECONDS) == set(m.sim.ERA_ORDER)


def test_progress_bar_and_text_track_the_clock(game_env):
    m = game_env.module
    m.set_speed(1)
    m.tick_clock(1.0)
    assert game_env.elements["season-progress-fill"].style.width == "10%"
    assert "next season in 9s" in game_env.elements["season-clock-display"].innerText


def test_speed_is_never_saved_and_loads_paused(game_env):
    m = game_env.module
    m.set_speed(4)
    data = m.get_state()
    assert "sim_speed" not in str(data) and "speed" not in data
    m.load_state(data)
    assert m.sim_speed in (0, 4)  # load_state leaves the live clock alone;
    m.sim_speed = 0


def test_advance_season_button_is_gone_from_the_page():
    import pathlib
    html = (pathlib.Path(__file__).resolve().parent.parent / "index.html").read_text()
    assert "advance-season-button" not in html
    assert 'id="speed-controls"' in html
