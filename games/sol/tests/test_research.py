"""Tests for the Milestone 4 research system v1: funding progress toward
the first distance tier (Near Bodies: Moon + Mars), unlocked with Iron."""


# --- initial state -----------------------------------------------------

def test_research_starts_at_zero_progress(game_env):
    assert game_env.module.research_progress == 0.0
    assert game_env.elements["research-progress"].innerText == "0 / 1000"


def test_near_bodies_starts_locked(game_env):
    assert game_env.module.near_bodies_unlocked is False


def test_research_bar_starts_empty(game_env):
    assert game_env.elements["research-bar"].style.width == "0.0%"


def test_research_status_empty_initially(game_env):
    assert game_env.elements["research-status"].innerText == ""


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
    assert game_env.module.resource_count == 0


def test_funding_deducts_flat_iron_cost(game_env):
    game_env.module.resource_count = 50
    game_env.fund_research()
    assert game_env.module.resource_count == 0


def test_funding_adds_flat_progress(game_env):
    game_env.module.resource_count = 50
    game_env.fund_research()
    assert game_env.module.research_progress == 50


def test_funding_cost_does_not_scale_between_purchases(game_env):
    # Unlike buildings, research funding is a flat repeatable investment,
    # not an escalating-cost purchase.
    game_env.module.resource_count = 200
    game_env.fund_research()
    game_env.fund_research()
    game_env.fund_research()
    button = game_env.elements["fund-research-button"]
    assert "50 Iron" in button.innerText
    assert game_env.module.resource_count == 50


def test_repeated_funding_accumulates_progress(game_env):
    game_env.module.resource_count = 500
    for _ in range(9):
        game_env.fund_research()
    assert game_env.module.research_progress == 450
    assert game_env.module.resource_count == 50


def test_funding_updates_progress_display(game_env):
    game_env.module.resource_count = 50
    game_env.fund_research()
    assert game_env.elements["research-progress"].innerText == "50 / 1000"


def test_funding_updates_bar_width(game_env):
    game_env.module.resource_count = 50
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
    game_env.module.resource_count = 50
    game_env.fund_research()
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


# --- unlocking the tier -----------------------------------------------

def test_reaching_target_unlocks_near_bodies(game_env):
    game_env.module.resource_count = 1000
    for _ in range(20):
        game_env.fund_research()
    assert game_env.module.near_bodies_unlocked is True


def test_progress_clamps_at_target_not_overshooting(game_env):
    game_env.module.research_progress = 980
    game_env.module.resource_count = 50
    game_env.fund_research()
    assert game_env.module.research_progress == 1000


def test_unlock_can_happen_with_progress_already_close_to_target(game_env):
    game_env.module.research_progress = 970
    game_env.module.resource_count = 50
    game_env.fund_research()
    assert game_env.module.near_bodies_unlocked is True


def test_unlock_updates_progress_display_to_unlocked_text(game_env):
    game_env.module.research_progress = 950
    game_env.module.resource_count = 50
    game_env.fund_research()
    assert game_env.elements["research-progress"].innerText == "Unlocked"


def test_unlock_shows_both_moon_and_mars_in_status(game_env):
    game_env.module.research_progress = 950
    game_env.module.resource_count = 50
    game_env.fund_research()
    status = game_env.elements["research-status"].innerText
    assert "Moon" in status
    assert "Mars" in status


def test_unlock_disables_fund_button(game_env):
    game_env.module.research_progress = 950
    game_env.module.resource_count = 50
    game_env.fund_research()
    button = game_env.elements["fund-research-button"]
    assert button.disabled is True
    assert button.innerText == "Near Bodies Unlocked"


def test_bar_shows_full_width_once_unlocked(game_env):
    game_env.module.research_progress = 950
    game_env.module.resource_count = 50
    game_env.fund_research()
    assert game_env.elements["research-bar"].style.width == "100.0%"


# --- funding is a no-op once already unlocked ------------------------

def test_funding_after_unlock_does_not_spend_iron(game_env):
    game_env.module.near_bodies_unlocked = True
    game_env.module.research_progress = 1000
    game_env.module.resource_count = 500
    game_env.fund_research()
    assert game_env.module.resource_count == 500


def test_funding_after_unlock_still_gives_press_feedback(game_env):
    game_env.module.near_bodies_unlocked = True
    game_env.module.research_progress = 1000
    game_env.module.resource_count = 500
    button = game_env.elements["fund-research-button"]
    game_env.fund_research()
    assert button.classList.contains("pressed")


# --- decoupled from ecology/automation --------------------------------

def test_research_progress_unaffected_by_passive_ticks(game_env):
    game_env.module.resource_count = 1000
    game_env.buy_generator()
    game_env.timers.tick_intervals(50)
    assert game_env.module.research_progress == 0.0


def test_research_funding_does_not_touch_ecology(game_env):
    game_env.module.resource_count = 50
    ecology_before = game_env.module.ecology_health
    game_env.fund_research()
    assert game_env.module.ecology_health == ecology_before


def test_research_available_even_during_ecological_collapse(game_env):
    # Funding spends banked Iron directly; it isn't automated production,
    # so it shouldn't be gated by the ecology penalty/halt.
    game_env.module.ecology_health = 0.0
    game_env.module.resource_count = 50
    game_env.fund_research()
    assert game_env.module.research_progress == 50
