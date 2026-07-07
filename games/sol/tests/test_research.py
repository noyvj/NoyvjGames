"""Tests for the research system: funding progress toward sequential
distance tiers (Milestone 4: Near Bodies v1; Milestone 9a: generalized to
a tier sequence, adding a Far Bodies tier). Tiers are researched in order —
completing one seamlessly advances to funding the next, with the button
only truly disabling once every tier is exhausted."""


def _tier(game_env, index):
    return game_env.module.RESEARCH_TIERS[index]


def _complete_tier(game_env, index):
    """Funds and completes tiers 0..index in sequence (in order, since
    tiers must be researched sequentially)."""
    for i in range(index + 1):
        target = _tier(game_env, i)["target"]
        game_env.earth["resource_count"] = target
        clicks = target // game_env.module.RESEARCH_FUND_COST
        for _ in range(clicks):
            game_env.fund_research()


# --- initial state -----------------------------------------------------

def test_research_starts_at_zero_progress(game_env):
    assert game_env.module.research_progress == 0.0
    assert game_env.elements["research-progress"].innerText == "0 / 1000"


def test_nothing_unlocked_initially(game_env):
    assert game_env.module.unlocked_bodies == set()


def test_first_tier_is_near_bodies(game_env):
    tier = _tier(game_env, 0)
    assert tier["name"] == "Near Bodies"
    assert tier["target"] == 1000
    assert set(tier["unlocks"]) == {"Moon", "Mars"}


def test_second_tier_is_far_bodies(game_env):
    tier = _tier(game_env, 1)
    assert tier["name"] == "Far Bodies"
    assert set(tier["unlocks"]) == {"Venus", "AsteroidBelt", "Pluto", "JupiterMoons", "SaturnMoons"}


def test_research_bar_starts_empty(game_env):
    assert game_env.elements["research-bar"].style.width == "0.0%"


def test_research_status_empty_initially(game_env):
    assert game_env.elements["research-status"].innerText == ""


def test_research_label_shows_current_tier_name(game_env):
    assert "Near Bodies" in game_env.elements["research-label"].innerText


def test_setup_configures_fund_button(game_env):
    button = game_env.elements["fund-research-button"]
    assert button.disabled is False
    assert "50 Iron" in button.innerText


def test_setup_registers_fund_listener(game_env):
    button = game_env.elements["fund-research-button"]
    assert "click" in button._listeners
    assert len(button._listeners["click"]) == 1


# --- funding: affordability -----------------------------------------------

def test_cannot_afford_funding_does_nothing(game_env):
    game_env.fund_research()
    assert game_env.module.research_progress == 0.0
    assert game_env.earth["resource_count"] == 0


def test_funding_deducts_flat_iron_cost(game_env):
    game_env.earth["resource_count"] = 50
    game_env.fund_research()
    assert game_env.earth["resource_count"] == 0


def test_funding_adds_flat_progress(game_env):
    game_env.earth["resource_count"] = 50
    game_env.fund_research()
    assert game_env.module.research_progress == 50


def test_funding_cost_does_not_scale_between_purchases(game_env):
    # Unlike buildings, research funding is a flat repeatable investment,
    # not an escalating-cost purchase, and stays flat across every tier.
    game_env.earth["resource_count"] = 200
    game_env.fund_research()
    game_env.fund_research()
    game_env.fund_research()
    button = game_env.elements["fund-research-button"]
    assert "50 Iron" in button.innerText
    assert game_env.earth["resource_count"] == 50


def test_repeated_funding_accumulates_progress(game_env):
    game_env.earth["resource_count"] = 500
    for _ in range(9):
        game_env.fund_research()
    assert game_env.module.research_progress == 450
    assert game_env.earth["resource_count"] == 50


def test_funding_updates_progress_display(game_env):
    game_env.earth["resource_count"] = 50
    game_env.fund_research()
    assert game_env.elements["research-progress"].innerText == "50 / 1000"


def test_funding_updates_bar_width(game_env):
    game_env.earth["resource_count"] = 50
    game_env.fund_research()
    assert game_env.elements["research-bar"].style.width == "5.0%"


def test_funding_button_gives_press_feedback_even_when_unaffordable(game_env):
    button = game_env.elements["fund-research-button"]
    game_env.fund_research()
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


def test_funding_button_press_feedback_on_success(game_env):
    button = game_env.elements["fund-research-button"]
    game_env.earth["resource_count"] = 50
    game_env.fund_research()
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


# --- completing tier 1 (Near Bodies) ------------------------------------

def test_reaching_target_unlocks_near_bodies(game_env):
    _complete_tier(game_env, 0)
    assert "Moon" in game_env.module.unlocked_bodies
    assert "Mars" in game_env.module.unlocked_bodies


def test_progress_clamps_at_target_not_overshooting(game_env):
    game_env.module.research_progress = 980
    game_env.earth["resource_count"] = 50
    game_env.fund_research()
    # Progress resets to 0 immediately upon completion (moving on to the
    # next tier), so it never sits "overshot" at the old target either.
    assert game_env.module.research_progress == 0.0


def test_completing_tier_advances_completed_tiers_counter(game_env):
    assert game_env.module.completed_tiers == 0
    _complete_tier(game_env, 0)
    assert game_env.module.completed_tiers == 1


def test_completing_tier_1_immediately_shows_tier_2(game_env):
    _complete_tier(game_env, 0)
    assert "Far Bodies" in game_env.elements["research-label"].innerText
    assert game_env.elements["research-progress"].innerText == "0 / 5000"


def test_fund_button_stays_active_after_completing_tier_1(game_env):
    # Unlike the old single-tier design, finishing a tier seamlessly moves
    # on to the next one — the button should NOT disable until every tier
    # is exhausted.
    _complete_tier(game_env, 0)
    button = game_env.elements["fund-research-button"]
    assert button.disabled is False
    assert "50 Iron" in button.innerText


def test_bar_resets_for_the_next_tier(game_env):
    _complete_tier(game_env, 0)
    assert game_env.elements["research-bar"].style.width == "0.0%"


# --- completing tier 2 (Far Bodies) / all tiers done -----------------------

def test_completing_both_tiers_unlocks_all_far_bodies(game_env):
    _complete_tier(game_env, 1)
    for body in ("Venus", "AsteroidBelt", "Pluto", "JupiterMoons", "SaturnMoons"):
        assert body in game_env.module.unlocked_bodies


def test_completing_all_tiers_shows_terminal_state(game_env):
    _complete_tier(game_env, 1)
    assert game_env.elements["research-progress"].innerText == "All Tiers Unlocked"
    assert game_env.elements["research-bar"].style.width == "100%"
    button = game_env.elements["fund-research-button"]
    assert button.disabled is True
    assert button.innerText == "All Tiers Unlocked"


def test_completing_all_tiers_shows_terminal_status_message(game_env):
    _complete_tier(game_env, 1)
    assert "Every distance tier" in game_env.elements["research-status"].innerText


# --- funding is a no-op once every tier is exhausted -----------------------

def test_funding_after_all_tiers_done_does_not_spend_iron(game_env):
    _complete_tier(game_env, 1)
    game_env.earth["resource_count"] = 500
    game_env.fund_research()
    assert game_env.earth["resource_count"] == 500


def test_funding_after_all_tiers_done_still_gives_press_feedback(game_env):
    _complete_tier(game_env, 1)
    game_env.earth["resource_count"] = 500
    button = game_env.elements["fund-research-button"]
    game_env.fund_research()
    assert button.classList.contains("pressed")


# --- decoupled from ecology/automation --------------------------------

def test_research_progress_unaffected_by_passive_ticks(game_env):
    game_env.earth["resource_count"] = 1000
    game_env.buy_generator()
    game_env.timers.tick_intervals(50)
    assert game_env.module.research_progress == 0.0


def test_research_funding_does_not_touch_ecology(game_env):
    game_env.earth["resource_count"] = 50
    ecology_before = game_env.earth["ecology_health"]
    game_env.fund_research()
    assert game_env.earth["ecology_health"] == ecology_before


def test_research_available_even_during_ecological_collapse(game_env):
    # Funding spends banked Iron directly; it isn't automated production,
    # so it shouldn't be gated by the ecology penalty/halt.
    game_env.earth["ecology_health"] = 0.0
    game_env.earth["resource_count"] = 50
    game_env.fund_research()
    assert game_env.module.research_progress == 50
