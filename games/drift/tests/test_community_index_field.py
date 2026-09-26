"""I17: the save carries a write-only wellbeing number for the community capacity index."""


def test_state_carries_the_current_wellbeing_score(game_env):
    m = game_env.module
    state = m.get_state()
    assert state["wellbeing_score"] == m.region.wellbeing_score()
    m.region.funds = 900.0
    assert m.get_state()["wellbeing_score"] == m.region.wellbeing_score()


def test_the_extra_key_is_ignored_on_load(game_env):
    m = game_env.module
    state = m.get_state()
    state["wellbeing_score"] = 12345
    assert m.load_state(state) is True
    assert m.region.wellbeing_score() != 12345
