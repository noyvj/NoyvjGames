"""J17 -- player-run trade posts: once automation is maxed, establish a
passive income post in a reachable system, one per system."""


def _max_out_automation(game):
    game.total_profit = 100_000
    game.research_points = 1_000_000
    for ship_id in list(game.ships):
        if game.automation_slots_available() and game.ships[ship_id].purchased:
            game.automate_ship(ship_id)
    assert game.automation_is_maxed()


def test_not_available_until_automation_is_maxed(game_env):
    game = game_env.module
    game.total_profit = 100_000
    assert game.automation_is_maxed() is False
    assert game.can_build_trade_post() is False
    assert game.build_trade_post() is False
    game.render_market()
    assert game_env.elements["trade-post-button"].hidden is True


def test_building_a_post_spends_credits_and_adds_passive_income(game_env):
    game = game_env.module
    _max_out_automation(game)
    game.total_profit = 1000
    assert game.build_trade_post()
    assert game.trade_posts == ["Home system"]
    assert game.total_profit == 1000 - game.TRADE_POST_COST
    before = game.total_profit
    game.tick()
    assert game.total_profit >= before + game.TRADE_POST_INCOME_PER_TICK - 1  # sales may add more


def test_one_post_per_system_and_only_reachable_systems(game_env):
    game = game_env.module
    _max_out_automation(game)
    game.total_profit = 10_000
    assert game.build_trade_post()
    assert game.next_trade_post_system() is None  # Kepler not reachable yet
    assert game.can_build_trade_post() is False
    game.unlocked_research.add("galaxy_expansion")
    assert game.next_trade_post_system() == "Kepler Cluster"
    assert game.build_trade_post()
    assert game.trade_posts == ["Home system", "Kepler Cluster"]
    assert game.trade_post_income_per_tick() == 2 * game.TRADE_POST_INCOME_PER_TICK


def test_cannot_build_without_enough_credits(game_env):
    game = game_env.module
    _max_out_automation(game)
    game.total_profit = game.TRADE_POST_COST - 1
    assert game.can_build_trade_post() is False


def test_passive_income_is_not_counted_as_a_sale(game_env):
    game = game_env.module
    _max_out_automation(game)
    game.total_profit = 1000
    game.build_trade_post()
    sales = game.total_sales_count
    game.ships["1"].location = "aurum"  # idle docked ships make no sale
    game.tick()
    assert game.total_sales_count == sales


def test_button_builds_and_status_lists_posts(game_env):
    game = game_env.module
    _max_out_automation(game)
    game.total_profit = 1000
    game.render_market()
    button = game_env.elements["trade-post-button"]
    assert button.hidden is False and button.disabled is False
    button.dispatch("click", None)
    assert game.trade_posts == ["Home system"]
    status = game_env.elements["trade-post-status"].innerText
    assert "Home system" in status and f"+{game.TRADE_POST_INCOME_PER_TICK} credits per tick" in status
    assert game_env.elements["trade-post-button"].disabled is True


def test_state_round_trip_and_bad_saved_values(game_env):
    game = game_env.module
    game.trade_posts[:] = ["Home system", "Rift Colonies"]
    saved = game.get_state()
    assert saved["trade_posts"] == ["Home system", "Rift Colonies"]
    game.trade_posts[:] = []
    game.load_state(saved)
    assert game.trade_posts == ["Home system", "Rift Colonies"]
    for bad, expected in (
        (["Home system", "Home system", "Nowhere", 7, None], ["Home system"]),
        ("junk", []), (None, []), (5, []), ({"a": 1}, []),
    ):
        saved["trade_posts"] = bad
        game.load_state(saved)
        assert game.trade_posts == expected
    del saved["trade_posts"]
    game.trade_posts[:] = ["Home system"]
    game.load_state(saved)
    assert game.trade_posts == []
