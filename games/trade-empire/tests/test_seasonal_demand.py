"""J29 -- opt-in seasonal demand: a rotating, predictable pair of goods sells
for a bonus; nothing is ever marked down; off by default."""


def _tick(game_env, n=1):
    for _ in range(n):
        game_env.module.tick()


def test_off_by_default_and_prices_are_untouched(game_env):
    game = game_env.module
    assert game.seasonal_demand_enabled is False
    assert game.seasonal_multiplier(game.ORE) == 1.0
    before = game.current_sell_price(game.ORE)
    _tick(game_env, 5)
    assert game.season_ticks == 0
    assert game.current_sell_price(game.ORE) == before


def test_the_toggle_button_switches_the_mode_and_status_text(game_env):
    game = game_env.module
    game_env.elements["seasonal-demand-toggle-button"].dispatch("click", None)
    assert game.seasonal_demand_enabled is True
    assert "on" in game_env.elements["seasonal-demand-toggle-button"].innerText
    assert "Season 1" in game_env.elements["seasonal-demand-status"].innerText


def test_a_good_in_demand_sells_for_the_bonus(game_env):
    game = game_env.module
    hot = game.seasonal_hot_goods(0)
    cold = next(g for g in game.seasonal_reachable_goods() if g not in hot)
    game.seasonal_demand_enabled = True
    expected = max(1, round(game.SELL_PRICE[hot[0]] * game.market_multiplier[hot[0]] * (1 + game.SEASONAL_DEMAND_BONUS)))
    assert game.current_sell_price(hot[0]) == expected
    assert game.current_sell_price(hot[0]) > round(game.SELL_PRICE[hot[0]] * game.market_multiplier[hot[0]])
    assert game.seasonal_multiplier(cold) == 1.0


def test_seasons_rotate_predictably_and_cover_every_reachable_good(game_env):
    game = game_env.module
    seen = set()
    for season in range(6):
        hot = game.seasonal_hot_goods(season)
        assert len(hot) == game.SEASONAL_HOT_GOOD_COUNT
        seen.update(hot)
    assert seen == set(game.seasonal_reachable_goods())
    assert game.seasonal_hot_goods(2) == game.seasonal_hot_goods(2)


def test_ticks_only_advance_while_enabled_and_the_status_counts_down(game_env):
    game = game_env.module
    game.seasonal_demand_enabled = True
    _tick(game_env, 5)
    assert game.season_ticks == 5
    number, left, hot, upcoming = game.seasonal_status()
    assert number == 1 and left == game.SEASON_LENGTH_TICKS - 5
    _tick(game_env, game.SEASON_LENGTH_TICKS - 5)
    assert game.seasonal_status()[0] == 2
    assert game.seasonal_status()[2] == upcoming


def test_state_round_trips_and_tolerates_bad_saved_values(game_env):
    game = game_env.module
    game.seasonal_demand_enabled = True
    game.season_ticks = 42
    saved = game.get_state()
    assert saved["seasonal_demand"] == {"enabled": True, "ticks": 42}
    game.seasonal_demand_enabled, game.season_ticks = False, 0
    game.load_state(saved)
    assert game.seasonal_demand_enabled is True and game.season_ticks == 42
    for bad in ({"enabled": "yes", "ticks": -5}, {"enabled": True, "ticks": 1e308}, {"enabled": True, "ticks": True}, "junk", None):
        saved["seasonal_demand"] = bad
        game.load_state(saved)
        assert game.season_ticks == 0
        assert game.seasonal_demand_enabled is (isinstance(bad, dict) and bad.get("enabled") is True)


def test_an_old_save_without_the_field_loads_with_the_mode_off(game_env):
    game = game_env.module
    saved = game.get_state()
    del saved["seasonal_demand"]
    game.seasonal_demand_enabled, game.season_ticks = True, 9
    game.load_state(saved)
    assert game.seasonal_demand_enabled is False and game.season_ticks == 0


def test_the_market_line_flags_goods_that_are_in_demand(game_env):
    game = game_env.module
    game.seasonal_demand_enabled = True
    game.render_market()
    hot = game.seasonal_hot_goods(0)
    assert "in demand" in game_env.elements[f"market-{hot[0]}-display"].innerText
    cold = next(g for g in game.seasonal_reachable_goods() if g not in hot and f"market-{g}-display" in game_env.elements)
    assert "in demand" not in game_env.elements[f"market-{cold}-display"].innerText
