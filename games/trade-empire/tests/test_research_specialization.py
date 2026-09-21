"""J15 -- the research specialization fork: after Automation Expansion II,
choose an Automation path or a Market path; the first tier of one closes
the other for good."""


def _ready(game):
    game.research_points = 1_000_000
    game.unlock_research("automation_slot")
    assert game.unlock_research("automation_slot_2")


def test_both_paths_are_gated_behind_automation_expansion_ii(game_env):
    game = game_env.module
    game.research_points = 1_000_000
    for node in ("auto_efficiency", "market_insight"):
        assert game.can_unlock_research(node) is False
    _ready(game)
    for node in ("auto_efficiency", "market_insight"):
        assert game.can_unlock_research(node) is True


def test_choosing_one_path_permanently_closes_the_other(game_env):
    game = game_env.module
    _ready(game)
    assert game.unlock_research("auto_efficiency")
    assert game.research_node_blocked_by("market_insight") == "auto_efficiency"
    assert game.can_unlock_research("market_insight") is False
    assert game.unlock_research("market_insight") is False
    assert game.unlock_research("market_insight_2") is False
    assert "market_insight" not in game.unlocked_research


def test_tier_two_needs_tier_one_and_stays_on_its_own_path(game_env):
    game = game_env.module
    _ready(game)
    assert game.can_unlock_research("auto_efficiency_2") is False
    game.unlock_research("market_insight")
    assert game.can_unlock_research("auto_efficiency_2") is False
    assert game.can_unlock_research("market_insight_2") is True


def test_automation_path_boosts_automated_ships_only_and_adds_a_slot(game_env):
    game = game_env.module
    _ready(game)
    ship = game.ships["1"]

    def proceeds(automated):
        ship.location = None
        ship.origin, ship.destination = "aurum", "ferrum"
        ship.cargo_good, ship.cargo_qty = game.ORE, 10
        ship.transit_ticks_remaining = 1
        ship.automated = automated
        return ship.advance_transit()[2]

    baseline_manual, baseline_auto = proceeds(False), proceeds(True)
    assert baseline_manual == baseline_auto
    slots_before = game.max_automated_ships()
    game.unlock_research("auto_efficiency")
    manual, auto = proceeds(False), proceeds(True)
    assert manual == baseline_manual
    assert auto == int(round(baseline_auto * (1 + game.AUTO_EFFICIENCY_BONUS)))
    game.unlock_research("auto_efficiency_2")
    assert game.max_automated_ships() == slots_before + game.AUTO_EFFICIENCY_2_SLOT_BONUS


def test_market_path_speeds_recovery_and_softens_price_drops(game_env):
    game = game_env.module
    _ready(game)
    game.market_multiplier[game.ORE] = 0.5
    game.recover_market()
    normal_gain = game.market_multiplier[game.ORE] - 0.5
    game.unlock_research("market_insight")
    game.market_multiplier[game.ORE] = 0.5
    game.recover_market()
    assert abs((game.market_multiplier[game.ORE] - 0.5) - normal_gain * game.MARKET_INSIGHT_RECOVERY_MULTIPLIER) < 1e-9

    game.market_multiplier[game.ORE] = 1.0
    game.apply_market_sale(game.ORE, 10)
    normal_drop = 1.0 - game.market_multiplier[game.ORE]
    game.unlock_research("market_insight_2")
    game.market_multiplier[game.ORE] = 1.0
    game.apply_market_sale(game.ORE, 10)
    assert abs((1.0 - game.market_multiplier[game.ORE]) - normal_drop * game.MARKET_INSIGHT_2_DECAY_MULTIPLIER) < 1e-9


def test_the_closed_path_says_so_in_the_ui(game_env):
    game = game_env.module
    _ready(game)
    game.unlock_research("auto_efficiency")
    game.render_research()
    text = game_env.elements["research-market_insight-status"].innerText
    assert "closed" in text and "Autopilot Optimisation" in text
    # the label and description must survive the appended note
    assert text.startswith("Market Insight (Market path) — Sold-down prices recover 50% faster")
    assert game_env.elements["research-market_insight-unlock-button"].title.startswith("Closed by your choice")
    assert game_env.elements["research-market_insight-unlock-button"].disabled is True


def test_save_round_trip_keeps_the_choice_and_the_exclusion(game_env):
    game = game_env.module
    _ready(game)
    game.unlock_research("market_insight")
    saved = game.get_state()
    game.unlocked_research.clear()
    game.load_state(saved)
    assert "market_insight" in game.unlocked_research
    assert game.research_node_blocked_by("auto_efficiency") == "market_insight"


def test_fully_studied_needs_one_completed_path_not_both(game_env):
    game = game_env.module
    game.research_points = 1_000_000
    for node in ("fast_ships", "hauler", "automation_slot", "automation_slot_2", "galaxy_expansion", "outer_reaches"):
        game.unlock_research(node)
    assert "all_research_unlocked" not in game.achievement_ids_earned()
    game.unlock_research("auto_efficiency")
    game.unlock_research("auto_efficiency_2")
    assert "all_research_unlocked" in game.achievement_ids_earned()
