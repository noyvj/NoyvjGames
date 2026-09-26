"""D9: the save carries the season each seawall tier was first reached, for the community seawall pace line."""


def test_no_field_before_any_tier(game_env):
    m = game_env.module
    assert "tier_first_season" not in m.get_state()


def test_first_season_per_tier_from_the_tier_log(game_env):
    m = game_env.module
    m.state.tier_log = [0, 0, 1, 1, 2, 2, 2]
    assert m.get_state()["tier_first_season"] == {"t1": 3, "t2": 5}
    m.state.tier_log = [0, 3, 3]
    assert m.get_state()["tier_first_season"] == {"t1": 2, "t2": 2, "t3": 2}


def test_extra_key_is_ignored_on_load(game_env):
    m = game_env.module
    m.state.tier_log = [0, 1]
    state = m.get_state()
    assert m.load_state(state) is not False
