"""J19 -- colony loyalty: a chronically under-served colony makes a one-time
concession demand. Granting it costs credits and restores satisfaction;
ignoring it costs nothing and it lapses."""


def _neglect(game, colony_id="aurum", ticks=None):
    colony = game.colony_states[colony_id]
    colony.need_satisfaction = 0.0
    for _ in range(ticks if ticks is not None else game.NEGLECT_DEMAND_TICKS):
        colony.need_satisfaction = 0.0
        colony.update_loyalty()
    return colony


def test_a_well_supplied_colony_never_demands_anything(game_env):
    game = game_env.module
    colony = game.colony_states["aurum"]
    colony.need_satisfaction = 0.9
    for _ in range(game.NEGLECT_DEMAND_TICKS * 3):
        colony.update_loyalty()
    assert colony.neglect_ticks == 0 and not colony.has_demand()


def test_chronic_neglect_triggers_a_demand_only_after_the_full_stretch(game_env):
    game = game_env.module
    colony = _neglect(game, ticks=game.NEGLECT_DEMAND_TICKS - 1)
    assert not colony.has_demand()
    colony.update_loyalty()
    assert colony.has_demand() and colony.demand_ticks_left == game.DEMAND_WINDOW_TICKS


def test_recovering_above_the_threshold_resets_the_neglect_count(game_env):
    game = game_env.module
    colony = _neglect(game, ticks=game.NEGLECT_DEMAND_TICKS - 5)
    colony.need_satisfaction = game.NEGLECT_THRESHOLD + 0.1
    colony.update_loyalty()
    assert colony.neglect_ticks == 0


def test_granting_costs_credits_restores_satisfaction_and_starts_a_cooldown(game_env):
    game = game_env.module
    colony = _neglect(game)
    game.total_profit = 500
    assert game.grant_concession("aurum")
    assert game.total_profit == 500 - game.CONCESSION_COST
    assert colony.need_satisfaction == game.CONCESSION_SATISFACTION_BOOST
    assert not colony.has_demand() and colony.demand_cooldown == game.DEMAND_COOLDOWN_TICKS


def test_cannot_grant_without_a_demand_or_without_credits(game_env):
    game = game_env.module
    game.total_profit = 500
    assert game.can_grant_concession("aurum") is False
    _neglect(game)
    game.total_profit = game.CONCESSION_COST - 1
    assert game.can_grant_concession("aurum") is False
    assert game.grant_concession("aurum") is False
    assert game.total_profit == game.CONCESSION_COST - 1


def test_ignoring_a_demand_costs_nothing_and_it_lapses_then_cools_down(game_env):
    game = game_env.module
    colony = _neglect(game)
    game.total_profit = 500
    for _ in range(game.DEMAND_WINDOW_TICKS):
        colony.need_satisfaction = 0.0
        colony.update_loyalty()
    assert not colony.has_demand()
    assert game.total_profit == 500 and colony.demand_cooldown > 0
    for _ in range(game.NEGLECT_DEMAND_TICKS + 5):
        colony.need_satisfaction = 0.0
        colony.update_loyalty()
        if colony.demand_cooldown > 0:
            assert not colony.has_demand()  # no new demand during the cooldown


def test_tick_runs_the_loyalty_update_for_every_colony(game_env):
    game = game_env.module
    for state in game.colony_states.values():
        state.need_satisfaction = 0.0
    game.tick()
    assert all(state.neglect_ticks == 1 for state in game.colony_states.values())


def test_the_ui_shows_the_demand_and_the_button_grants_it(game_env):
    game = game_env.module
    game.total_profit = 500
    _neglect(game)
    game.render()
    demand = game_env.elements["colony-aurum-demand-display"]
    button = game_env.elements["colony-aurum-concede-button"]
    assert demand.hidden is False and "concession" in demand.innerText and "costs nothing" in demand.innerText
    assert button.hidden is False and button.disabled is False
    button.dispatch("click", None)
    assert game.total_profit == 500 - game.CONCESSION_COST
    assert game_env.elements["colony-aurum-demand-display"].hidden is True
    assert game_env.elements["colony-verdant-demand-display"].hidden is True


def test_state_round_trip_and_bad_saved_values(game_env):
    game = game_env.module
    colony = game.colony_states["aurum"]
    colony.neglect_ticks, colony.demand_ticks_left, colony.demand_cooldown = 12, 7, 33
    saved = game.get_state()
    entry = saved["colony_states"]["aurum"]
    assert (entry["neglect_ticks"], entry["demand_ticks_left"], entry["demand_cooldown"]) == (12, 7, 33)
    colony.neglect_ticks = colony.demand_ticks_left = colony.demand_cooldown = 0
    game.load_state(saved)
    assert (colony.neglect_ticks, colony.demand_ticks_left, colony.demand_cooldown) == (12, 7, 33)
    for bad in (-1, 10**9, True, "5", None, 2.5):
        for key in ("neglect_ticks", "demand_ticks_left", "demand_cooldown"):
            saved["colony_states"]["aurum"][key] = bad
        game.load_state(saved)
        assert (colony.neglect_ticks, colony.demand_ticks_left, colony.demand_cooldown) == (0, 0, 0)
    for key in ("neglect_ticks", "demand_ticks_left", "demand_cooldown"):
        del saved["colony_states"]["aurum"][key]
    colony.neglect_ticks = 5
    game.load_state(saved)
    assert colony.neglect_ticks == 0
