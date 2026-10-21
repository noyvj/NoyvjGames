import copy

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


def test_fresh_state_has_no_season_frames(game_env):
    m = game_env.module
    data = m.get_state()
    assert "season_frames" not in data


def test_tick_80_gives_two_frames(game_env):
    m = game_env.module
    game_env.tick(80)
    data = m.get_state()
    assert len(data["season_frames"]) == 2


def test_load_state_twice_preserves_frames(game_env):
    m = game_env.module
    game_env.tick(80)
    data = copy.deepcopy(m.get_state())
    game_env.reset_session()
    m.load_state(data)
    m.load_state(data)
    assert m.season_frames == data["season_frames"]


def test_load_state_filters_bad_frames(game_env):
    m = game_env.module
    good_frame = {"n": 1, "cols": 3, "cells": "PPP", "label": "Spring"}
    bad_data = {
        "season_frames": [
            "x",
            {"n": 1, "cols": 3, "cells": "PPPQ"},
            {"n": 2, "cols": 4, "cells": "PPPPP"},
            good_frame,
        ]
    }
    game_env.reset_session()
    m.load_state(bad_data)
    assert len(m.season_frames) == 1
    assert m.season_frames[0] == good_frame


def test_load_state_missing_key_clears_frames(game_env):
    m = game_env.module
    bad_data = {"season_frames": [{"n": 1, "cols": 3, "cells": "PPP", "label": "Spring"}]}
    del bad_data["season_frames"]
    game_env.reset_session()
    m.load_state(bad_data)
    assert m.season_frames == []
