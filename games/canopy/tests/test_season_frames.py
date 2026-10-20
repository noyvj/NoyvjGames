from canopy_worldvars import SEASON_FRAMES_MAX


def test_season_frames_empty_at_start(game_env):
    m = game_env.module
    assert m.season_frames == []


def test_one_frame_after_first_season(game_env):
    m = game_env.module
    game_env.tick(40)
    assert len(m.season_frames) == 1
    frame = m.season_frames[0]
    assert frame["n"] == 1
    assert frame["label"] == "Spring"
    assert frame["cols"] == m.runstate.GRID_COLS
    assert len(frame["cells"]) == len(m.plots)
    assert set(frame["cells"]) == {"P"}


def test_frame_updates_on_clear(game_env):
    game_env.tick(40)
    game_env.tick(3)
    game_env.select(0)
    game_env.clear()
    game_env.tick(37)
    newest = game_env.module.season_frames[-1]
    assert newest["cells"][0] == "B"


def test_max_frames_kept(game_env):
    m = game_env.module
    for _ in range(22):
        game_env.tick(40)
    assert len(m.season_frames) == SEASON_FRAMES_MAX
    assert m.season_frames[-1]["n"] == 22
    assert m.season_frames[0]["n"] == 3


def test_reset_clears_frames(game_env):
    game_env.tick(40)
    game_env.reset_session()
    assert game_env.module.season_frames == []
