"""B7: "forest ranger" harder difficulty (steeper soil degradation)."""


def test_default_difficulty_is_normal(game_env):
    m = game_env.module
    assert m.current_difficulty == "normal"
    m.plots[0].clear_count = 2
    assert abs(m.plots[0].productivity_multiplier() - 0.8) < 1e-9


def test_ranger_doubles_degradation_per_clear(game_env):
    m = game_env.module
    game_env.change_difficulty("ranger")
    m.plots[0].clear_count = 2
    assert abs(m.plots[0].productivity_multiplier() - 0.6) < 1e-9


def test_ranger_still_floors_at_minimum(game_env):
    m = game_env.module
    game_env.change_difficulty("ranger")
    m.plots[0].clear_count = 50
    assert m.plots[0].productivity_multiplier() == m.MIN_PRODUCTIVITY_MULTIPLIER


def test_changing_difficulty_resets_the_session(game_env):
    m = game_env.module
    game_env.tick(5)
    assert m.standing_forest_value() > 0
    game_env.change_difficulty("ranger")
    assert m.standing_forest_value() == 0


def test_invalid_difficulty_is_rejected(game_env):
    m = game_env.module
    assert m.reset_session(difficulty="nightmare") is False
    assert m.current_difficulty == "normal"


def test_difficulty_round_trips_through_save(game_env):
    m = game_env.module
    game_env.change_difficulty("ranger")
    state = m.get_state()
    m.reset_session(difficulty="normal")
    m.load_state(state)
    assert m.current_difficulty == "ranger"


def test_old_save_without_difficulty_loads_as_normal(game_env):
    m = game_env.module
    game_env.change_difficulty("ranger")
    state = m.get_state()
    del state["current_difficulty"]
    m.load_state(state)
    assert m.current_difficulty == "normal"


def test_soil_hint_reflects_ranger_step(game_env):
    game_env.change_difficulty("ranger")
    game_env.select(0)
    assert "20 points" in game_env.elements["soil-hint"].title


def test_select_mirrors_difficulty(game_env):
    game_env.change_difficulty("ranger")
    assert game_env.elements["difficulty-select"].value == "ranger"
