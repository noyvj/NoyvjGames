"""C8: a one-time callout the first time cumulative renewable capacity
crosses 50% of the grid's total. Fires from the action handlers
(build/retire/advance round), never from render() itself, so a loaded
save that already crossed this threshold doesn't flash the callout
purely from being rendered."""


def test_callout_hidden_on_a_fresh_game(game_env):
    assert game_env.elements["renewable-milestone-callout"].hidden is True


def test_callout_appears_once_renewable_share_crosses_half(game_env):
    game_env.state.funds = 10_000
    game_env.build("coal")  # 20 cap
    game_env.build("gas")  # +15 cap -- 35 fossil, 0 renewable
    assert game_env.elements["renewable-milestone-callout"].hidden is True
    game_env.build("solar")  # +10 cap -- 10/45 ~= 22%, still under 50%
    game_env.build("wind")  # +12 cap -- 22/57 ~= 39%, still under 50%
    assert game_env.elements["renewable-milestone-callout"].hidden is True
    game_env.build("hydro")  # +40 cap -- 62/97 ~= 64%, crosses 50%
    assert game_env.elements["renewable-milestone-callout"].hidden is False
    assert game_env.state.renewable_50_reached is True


def test_callout_is_dismissible(game_env):
    game_env.build("solar")  # 100% renewable immediately
    assert game_env.elements["renewable-milestone-callout"].hidden is False
    game_env.elements["renewable-milestone-dismiss-button"].dispatch("click", None)
    assert game_env.elements["renewable-milestone-callout"].hidden is True


def test_callout_does_not_reappear_after_being_reached(game_env):
    game_env.build("solar")
    game_env.elements["renewable-milestone-dismiss-button"].dispatch("click", None)
    game_env.build("wind")  # still >=50% renewable -- must not re-trigger
    assert game_env.elements["renewable-milestone-callout"].hidden is True


def test_reached_flag_round_trips_through_save_load(game_env):
    module = game_env.module
    game_env.build("solar")
    snapshot = module.get_state()
    assert snapshot["renewable_50_reached"] is True

    module.load_state(snapshot)
    assert module.state.renewable_50_reached is True


def test_loading_a_save_that_already_reached_it_does_not_flash_the_callout(game_env):
    module = game_env.module
    game_env.build("solar")
    game_env.elements["renewable-milestone-dismiss-button"].dispatch("click", None)
    snapshot = module.get_state()

    module.load_state(snapshot)

    assert game_env.elements["renewable-milestone-callout"].hidden is True


def test_retiring_fossil_down_to_a_renewable_majority_can_trigger_it(game_env):
    game_env.build("coal")
    game_env.build("solar")  # 20 coal vs 10 solar -- fossil majority
    assert game_env.elements["renewable-milestone-callout"].hidden is True
    game_env.retire("coal")  # now 100% renewable
    assert game_env.elements["renewable-milestone-callout"].hidden is False
