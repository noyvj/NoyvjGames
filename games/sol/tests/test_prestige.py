"""Tests for A1: Prestige / New Game+. TODO.md's own note leaned toward
starting simple -- a permanent flat resource-yield bonus on restart --
over a full skill-tree layer, since the latter is genuinely its own
milestone-sized feature; game.py went with that (see its own "Prestige /
New Game+ (A1)" comment block). Only available once every world is fully
terraformed (the existing soft win-state), gated behind confirm(), and
resets every world/research/governor/travel state while keeping
prestige_level, lifetime stats, and every already-earned achievement."""


def _win_the_game(game_env):
    module = game_env.module
    for planet in module.PLANETS:
        module.planet_state[planet]["terraform_progress"] = module.TERRAFORM_MAX
    module.update_win_display()


# --- availability --------------------------------------------------------

def test_prestige_unavailable_before_the_win_state(game_env):
    assert game_env.module._prestige_available() is False
    game_env.prestige()
    assert game_env.module.prestige_level == 0


def test_prestige_available_once_every_world_is_terraformed(game_env):
    _win_the_game(game_env)
    assert game_env.module._prestige_available() is True


def test_prestige_button_lives_inside_the_win_banner(game_env):
    # Same hidden-toggle as the banner itself -- no separate gating needed.
    assert game_env.elements["win-banner"].hidden is True
    _win_the_game(game_env)
    assert game_env.elements["win-banner"].hidden is False


# --- the reset itself ------------------------------------------------

def test_prestige_increments_the_level(game_env):
    _win_the_game(game_env)
    game_env.prestige()
    assert game_env.module.prestige_level == 1


def test_prestige_does_nothing_without_confirmation(game_env):
    _win_the_game(game_env)
    game_env.set_confirm_response(False)
    game_env.prestige()
    assert game_env.module.prestige_level == 0
    assert game_env.earth["terraform_progress"] == game_env.module.TERRAFORM_MAX


def test_prestige_resets_every_planets_economy(game_env):
    module = game_env.module
    game_env.earth["resource_count"] = 999
    game_env.earth["generator_count"] = 5
    _win_the_game(game_env)

    game_env.prestige()

    for planet in module.PLANETS:
        state = module.planet_state[planet]
        assert state["resource_count"] == 0.0
        assert state["generator_count"] == 0
        assert state["terraform_progress"] == 0.0
        assert state["ecology_health"] == 100.0


def test_prestige_resets_research_and_unlocks(game_env):
    module = game_env.module
    module.unlocked_bodies.add("Mars")
    module.completed_tiers = 1
    module.research_progress = 500.0
    _win_the_game(game_env)

    game_env.prestige()

    assert module.unlocked_bodies == set()
    assert module.completed_tiers == 0
    assert module.research_progress == 0.0


def test_prestige_resets_visited_bodies_and_current_planet(game_env):
    module = game_env.module
    module.unlocked_bodies.add("Mars")
    game_env.travel_to("Mars")
    _win_the_game(game_env)

    game_env.prestige()

    assert module.visited_bodies == {"Earth"}
    assert module.current_planet == "Earth"


def test_prestige_resets_governor_settings(game_env):
    module = game_env.module
    game_env.set_priority("growth")
    game_env.increase_budget()
    _win_the_game(game_env)

    game_env.prestige()

    assert module.governor_priority == "balance"
    assert module.governor_budget_pct == 50.0
    assert module.governor_tick_count == 0
    assert module.governor_purchase_count == 0


def test_prestige_keeps_lifetime_stats(game_env):
    module = game_env.module
    game_env.click("Earth")
    clicks_before = module.total_manual_clicks
    mined_before = module.lifetime_resources_mined_by_click
    _win_the_game(game_env)

    game_env.prestige()

    assert module.total_manual_clicks == clicks_before
    assert module.lifetime_resources_mined_by_click == mined_before


def test_prestige_keeps_one_shot_historical_achievement_flags(game_env):
    """quick_start/swift_expansion/manual_labor/off_the_grid are historical
    flags that, once True, never reset (see their own module comment) --
    unlike the live-derived achievements below (first_ore etc.), which are
    pure functions of planet_state and so DO reset when prestige resets
    planet_state, exactly as they would from any other event that drops
    the same underlying state back down (this isn't prestige-specific:
    the base game already accepts a live-derived achievement can un-earn
    itself if the state that justified it changes)."""
    module = game_env.module
    module.manual_labor_hit = True
    module.quick_start_hit = True
    _win_the_game(game_env)

    game_env.prestige()

    assert module.manual_labor_hit is True
    assert module.quick_start_hit is True


def test_prestige_resets_live_derived_achievements_tied_to_planet_state(game_env):
    """Documented consequence of "derive, don't track": first_ore is a
    pure function of Earth's resource_count, which prestige resets to 0
    along with the rest of that world's economy -- so it un-earns until
    re-earned in the new run, the same as it would if the player simply
    spent every last Iron down to 0 without ever prestiging."""
    module = game_env.module
    game_env.click("Earth")
    assert "first_ore" in module.achievement_ids_earned()
    _win_the_game(game_env)

    game_env.prestige()

    assert "first_ore" not in module.achievement_ids_earned()


# --- the production bonus ------------------------------------------------

def test_prestige_multiplier_is_one_at_level_zero(game_env):
    assert game_env.module.prestige_multiplier() == 1.0


def test_prestige_multiplier_increases_per_level(game_env):
    module = game_env.module
    _win_the_game(game_env)
    game_env.prestige()
    assert module.prestige_multiplier() == 1.0 + module.PRESTIGE_BONUS_PER_LEVEL


def test_prestige_bonus_applies_to_manual_clicks(game_env):
    module = game_env.module
    _win_the_game(game_env)
    game_env.prestige()
    game_env.click("Earth")
    assert game_env.earth["resource_count"] == 1.0 + module.PRESTIGE_BONUS_PER_LEVEL


def test_prestige_bonus_applies_to_automated_production(game_env):
    module = game_env.module
    _win_the_game(game_env)
    game_env.prestige()

    game_env.earth["resource_count"] = 10
    game_env.buy_generator("Earth")
    baseline = game_env.earth["resource_count"]
    game_env.timers.tick_intervals(10)  # 1 second
    produced = game_env.earth["resource_count"] - baseline
    assert produced > 1.0 * module.PLANETS["Earth"]["generator_rate"]  # boosted above the un-prestiged rate


def test_win_banner_shows_prestige_level_readout(game_env):
    module = game_env.module
    _win_the_game(game_env)
    assert "Prestige into a New Game+" in game_env.elements["prestige-level-readout"].innerText

    game_env.prestige()
    _win_the_game(game_env)
    assert "Prestige Level 1" in game_env.elements["prestige-level-readout"].innerText


def test_prestige_button_wired_up_by_setup(game_env):
    button = game_env.elements["prestige-button"]
    assert "click" in button._listeners
    assert len(button._listeners["click"]) == 1


def test_prestige_survives_a_save_round_trip(game_env):
    module = game_env.module
    _win_the_game(game_env)
    game_env.prestige()
    saved = module.get_state()
    assert saved["prestige_level"] == 1

    module.deserialize_state({})  # simulate loading a save missing the field entirely
    assert module.prestige_level == 1  # falls back to whatever's already running
