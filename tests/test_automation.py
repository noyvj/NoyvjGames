"""Tests for the Milestone 2 auto-generator (passive Iron production)."""

import math


def test_setup_configures_buy_button(game_env):
    button = game_env.elements["buy-generator-button"]
    assert button.disabled is False
    assert "10 Iron" in button.innerText


def test_setup_registers_buy_listener(game_env):
    button = game_env.elements["buy-generator-button"]
    assert "click" in button._listeners
    assert len(button._listeners["click"]) == 1


def test_initial_generator_state(game_env):
    assert game_env.module.generator_count == 0
    assert game_env.elements["generator-count"].innerText == "0"
    assert game_env.elements["generator-rate"].innerText == "0"


def test_setup_registers_a_continuous_tick_no_manual_countdown(game_env):
    # Milestone constraint: automation must be a continuous passive rate,
    # not a timer/countdown gate — so production is driven by setInterval,
    # not a one-shot setTimeout.
    assert len(game_env.timers.intervals) == 1
    _callback, delay = game_env.timers.intervals[0]
    assert delay == game_env.module.TICK_INTERVAL_MS


def test_cannot_afford_generator_does_nothing(game_env):
    game_env.buy_generator()
    assert game_env.module.generator_count == 0
    assert game_env.module.resource_count == 0


def test_buying_generator_deducts_cost_and_increments_count(game_env):
    game_env.module.resource_count = 10
    game_env.buy_generator()
    assert game_env.module.generator_count == 1
    assert game_env.module.resource_count == 0


def test_buying_generator_updates_rate_display(game_env):
    game_env.module.resource_count = 10
    game_env.buy_generator()
    assert game_env.elements["generator-count"].innerText == "1"
    assert game_env.elements["generator-rate"].innerText == "1"


def test_generator_cost_increases_after_purchase(game_env):
    first_cost = game_env.module.generator_cost()
    game_env.module.resource_count = first_cost
    game_env.buy_generator()
    second_cost = game_env.module.generator_cost()
    assert second_cost > first_cost


def test_buy_button_label_reflects_next_cost(game_env):
    game_env.module.resource_count = 10
    game_env.buy_generator()
    button = game_env.elements["buy-generator-button"]
    expected_cost = game_env.module.generator_cost()
    assert str(expected_cost) in button.innerText


def test_buy_button_gives_press_feedback_even_when_unaffordable(game_env):
    # "Button press gives visible feedback" applies to any press, not just
    # successful purchases.
    button = game_env.elements["buy-generator-button"]
    game_env.buy_generator()
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


def test_buy_button_press_feedback_on_successful_purchase(game_env):
    button = game_env.elements["buy-generator-button"]
    game_env.module.resource_count = 10
    game_env.buy_generator()
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


def test_no_generators_means_no_passive_income_on_tick(game_env):
    game_env.timers.tick_intervals(5)
    assert game_env.module.resource_count == 0


def test_owning_a_generator_produces_resources_over_ticks(game_env):
    game_env.module.resource_count = 10
    game_env.buy_generator()  # 1 generator, rate 1/s, ticking every 100ms
    game_env.timers.tick_intervals(10)  # 10 * 100ms = 1 second
    assert math.isclose(game_env.module.resource_count, 1.0, abs_tol=1e-9)


def test_passive_income_updates_the_displayed_count(game_env):
    game_env.module.resource_count = 10
    game_env.buy_generator()
    game_env.timers.tick_intervals(10)
    assert game_env.elements["resource-count"].innerText == "1"


def test_display_floors_fractional_resource_progress(game_env):
    game_env.module.resource_count = 10
    game_env.buy_generator()
    game_env.timers.tick_intervals(3)  # 0.3 iron produced, still "shows" as 0
    assert game_env.elements["resource-count"].innerText == "0"
    assert game_env.module.resource_count > 0


def test_multiple_generators_scale_the_rate_linearly(game_env):
    game_env.module.resource_count = 1000
    game_env.buy_generator()
    game_env.buy_generator()
    game_env.buy_generator()
    assert game_env.module.generator_count == 3
    assert game_env.elements["generator-rate"].innerText == "3"

    game_env.module.resource_count = 0
    game_env.timers.tick_intervals(10)  # 1 second at 3/s
    assert math.isclose(game_env.module.resource_count, 3.0, abs_tol=1e-9)


def test_manual_clicking_still_works_alongside_automation(game_env):
    game_env.module.resource_count = 10
    game_env.buy_generator()  # spends the 10 Iron, resource_count -> 0
    game_env.click()
    assert game_env.module.resource_count == 1
    game_env.timers.tick_intervals(10)  # +1 generator * 1/s * 1s
    assert math.isclose(game_env.module.resource_count, 2.0, abs_tol=1e-9)


def test_display_not_off_by_one_from_float_accumulation(game_env):
    # Ten 0.1 additions land on 0.9999999999999999 in IEEE754, not 1.0.
    # A naive math.floor() would display "0" a full second after the
    # generator should have produced its first whole Iron.
    game_env.module.resource_count = 0
    game_env.module.generator_count = 1
    for _ in range(10):
        game_env.module.tick()
    assert game_env.elements["resource-count"].innerText == "1"


def test_cannot_afford_generator_leaves_button_label_unchanged(game_env):
    button = game_env.elements["buy-generator-button"]
    before = button.innerText
    game_env.buy_generator()
    assert button.innerText == before
